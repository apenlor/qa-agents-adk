# codegen-agent/logger_utils.py
from typing import Any, Dict, List

from google.adk.events import Event
from google.genai import types
from mcp.types import CallToolResult

from agent import codegen_agent
from config import logger


# --- Log Formatting Helpers ---

def _format_wp_details(data: Dict[str, Any]) -> str:
    """Formats a log summary for get_work_package_details."""
    return (
        f" -> [ID: {data.get('id')}, Status: '{data.get('status')}', "
        f"Subject: '{data.get('subject')}']"
    )


def _format_tool_success_log(tool_name: str, result: CallToolResult) -> str:
    """Creates a detailed log summary for a successful tool call."""
    base_log = f"✅ Tool Success: {tool_name}"

    if result.structuredContent is not None:
        data = result.structuredContent
        if tool_name == 'get_work_package_details':
            return base_log + _format_wp_details(data)
        # Other tools used by this agent have simple responses
        # and don't need special formatting for their success log.

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
                log_summary = _format_tool_success_log(fr.name, response_payload)
                logger.info(log_summary)
        else:
            logger.info(f"✅ Tool '{fr.name}' returned a non-standard response.")


def log_agent_event(event: Event) -> None:
    """
    Logs a human-readable summary of an agent event by dispatching to specialized handlers.
    """
    if event.author != codegen_agent.name:
        return

    logger.debug(f"--- AGENT EVENT ---\n{event!r}\n--------------------")

    # This logic correctly handles events that contain both a thought and a tool call.
    if event.content and event.content.parts:
        for part in event.content.parts:
            if part.text and not part.function_call and not part.function_response:
                logger.info(f"🤔 Agent -> Thought: {part.text.strip()}")

    if function_calls := event.get_function_calls():
        _log_function_calls(function_calls)

    if function_responses := event.get_function_responses():
        _log_function_responses(function_responses)