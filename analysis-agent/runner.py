# analysis-agent/runner.py
from typing import Any, Dict, List

from google.adk.events import Event
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from mcp.types import CallToolResult

from agent import analysis_agent
from config import logger

APP_NAME = "analysis-agent-app"
USER_ID = "user_1"


# --- Log Formatting Helpers ---

def _format_wp_details(data: Dict[str, Any]) -> str:
    """Formats a log summary for get_work_package_details."""
    return (
        f" -> [ID: {data.get('id')}, Subject: '{data.get('subject')}', "
        f"lockVersion: {data.get('lockVersion')}]"
    )


def _format_wp_attachments(data: List[Dict[str, Any]]) -> str:
    """Formats a log summary for get_work_package_attachments."""
    filenames = [att.get("fileName", "N/A") for att in data if isinstance(att, dict)]
    return f" -> Found {len(data)} attachment(s): {filenames}"


def _format_attachment_content(data: Dict[str, Any]) -> str:
    """Formats a log summary for get_attachment_content."""
    mime_type = data.get("mime_type", "N/A")
    # The original calculation was incorrect for base64. A simple byte length is more accurate.
    data_size_kb = len(data.get("data", b"")) / 1024
    return f" -> [Content received: {mime_type}, ~{data_size_kb:.1f} KB]"


def _format_tool_success_log(tool_name: str, data: Any) -> str:
    """Creates a detailed log summary for a successful tool call using a formatter."""
    base_log = f"✅ Tool Success: {tool_name}"
    formatters = {
        "get_work_package_details": _format_wp_details,
        "get_work_package_attachments": _format_wp_attachments,
        "get_attachment_content": _format_attachment_content,
    }
    # Only format if the data type is correct for the formatter
    if formatter := formatters.get(tool_name):
        if (isinstance(data, dict) and tool_name != "get_work_package_attachments") or \
                (isinstance(data, list) and tool_name == "get_work_package_attachments"):
            return base_log + formatter(data)
    return base_log


# --- Event Logging Helpers ---

def _log_function_calls(function_calls: List[types.FunctionCall]) -> None:
    """Logs agent actions (tool calls)."""
    for fc in function_calls:
        if fc.name == "exit_loop":
            summary = fc.args.get("summary", "Workflow completed without a summary.")
            logger.info(f"🤖 Agent -> Final Summary: {summary}")
        else:
            logger.info(f"🛠️  Agent -> Action: Calling {fc.name}(...)")


def _log_function_responses(function_responses: List[types.FunctionResponse]) -> None:
    """Logs the results from tool executions."""
    for fr in function_responses:
        response_payload = fr.response.get("result")
        if isinstance(response_payload, CallToolResult):
            if response_payload.isError:
                error_msg = response_payload.content[0].text if response_payload.content else "Unknown error"
                logger.warning(f"❌ Tool Error in '{fr.name}': {error_msg}")
            else:
                log_summary = _format_tool_success_log(fr.name, response_payload.structuredContent)
                logger.info(log_summary)
        else:
            logger.info(f"✅ Tool '{fr.name}' returned a non-standard response.")


def _log_agent_event(event: Event) -> None:
    """
    Logs a human-readable summary of an agent event by dispatching to specialized handlers.
    """
    if event.author != analysis_agent.name:
        return  # Ignore events not from our agent (e.g., initial user query)

    logger.debug(f"--- AGENT EVENT ---\n{event!r}\n--------------------")

    if function_calls := event.get_function_calls():
        _log_function_calls(function_calls)
    elif function_responses := event.get_function_responses():
        _log_function_responses(function_responses)
    elif event.is_final_response() and event.content and event.content.parts:
        # This handles cases where the agent outputs text instead of calling a tool.
        logger.info(f"🤖 Agent -> Final Response: {event.content.parts[0].text.strip()}")


# --- Agent Execution Helpers ---

async def _setup_runner_and_session(work_package_id: int) -> (str, Runner):
    """Initializes and returns the session and the agent runner."""
    session_service = InMemorySessionService()
    session_id = f"wp_analysis_{work_package_id}"
    await session_service.create_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=session_id
    )
    logger.info(f"Session created: App='{APP_NAME}', User='{USER_ID}', Session='{session_id}'")
    runner = Runner(
        agent=analysis_agent,
        app_name=APP_NAME,
        session_service=session_service,
    )
    return session_id, runner


def _get_final_text_from_event(event: Event) -> str:
    """Extracts the final text from a concluding agent event."""
    text = "Agent did not produce a readable final response."
    if event.content and event.content.parts:
        text = event.content.parts[0].text

    if event.actions.escalate:
        # The `exit_loop` tool sets escalate=True, but we log its summary separately.
        # This handles other potential escalations.
        return f"Agent escalated: {text}"
    return text


def _handle_execution_error(e: Exception) -> str:
    """Formats a final message from a runtime exception."""
    if "429" in str(e) and "resource_exhausted" in str(e).lower():
        msg = "Agent stopped due to Google AI API quota limits."
        logger.error(msg)
        return msg

    msg = f"An unexpected error stopped the agent: {e}"
    logger.error(msg, exc_info=True)
    return msg


async def _process_agent_events(
        runner: Runner, user_id: str, session_id: str, query: types.Content
) -> str:
    """Runs the agent, logs events, and returns the final response text."""
    try:
        async for event in runner.run_async(
                user_id=user_id, session_id=session_id, new_message=query
        ):
            _log_agent_event(event)
            if event.is_final_response() or event.actions.escalate:
                return _get_final_text_from_event(event)
        return "Agent finished without a final response or escalation."
    except Exception as e:
        return _handle_execution_error(e)


# --- Main Orchestration Function ---

async def execute_analysis(work_package_id: int):
    """
    Orchestrates the agent execution workflow by delegating to helper functions.
    """
    session_id, runner = await _setup_runner_and_session(work_package_id)

    query_text = (
        f"Process work package {work_package_id}. Fully analyze its attachments, "
        "update its description and acceptance criteria, and then move it to the 'Specified' status."
    )
    logger.info(f"Initial query for the agent: '{query_text}'")
    query_content = types.Content(role="user", parts=[types.Part(text=query_text)])

    final_response_text = await _process_agent_events(
        runner, USER_ID, session_id, query_content
    )

    logger.info(f"🤖 Agent Final Response: {final_response_text}")
