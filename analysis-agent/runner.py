# analysis-agent/runner.py
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from google.adk.events import Event
from mcp.types import CallToolResult
import json

from config import logger
from agent import analysis_agent

APP_NAME = "analysis-agent-app"
USER_ID = "user_1"


def _log_agent_event(event: Event) -> None:
    """
    Logs a structured, human-readable summary of an agent event for INFO level.
    The full event object is always logged at the DEBUG level for detailed inspection.
    """
    # The full, verbose event is only ever logged at DEBUG level.
    logger.debug(f"--- AGENT EVENT ---\n{event}\n--------------------")

    # --- INFO Level Logging: Human-Readable Summaries ---
    function_calls = event.get_function_calls()
    if function_calls:
        calls_str = ", ".join([f"{fc.name}(...)" for fc in function_calls])
        logger.info(f"🛠️  Agent -> Decided to call tool(s): {calls_str}")
        return

    function_responses = event.get_function_responses()
    if function_responses:
        for fr in function_responses:
            response_payload = fr.response.get("result")

            if isinstance(response_payload, CallToolResult):
                if response_payload.isError:
                    error_msg = response_payload.content[0].text if response_payload.content else "Unknown error"
                    logger.warning(f"❌ Tool '{fr.name}' failed with error: {error_msg}")
                else:
                    # Logic for creating a concise summary for successful tool calls.
                    log_summary = f"✅ Tool '{fr.name}' executed successfully"
                    data = response_payload.structuredContent

                    if fr.name == 'get_work_package_details' and isinstance(data, dict):
                        log_summary += f" -> [ID: {data.get('id')}, Subject: '{data.get('subject')}']"
                    elif fr.name == 'get_work_package_attachments' and isinstance(data, list):
                        filenames = [att.get('fileName', 'N/A') for att in data]
                        log_summary += f" -> Found {len(data)} attachment(s): {filenames}"
                    elif fr.name == 'get_attachment_content' and isinstance(data, dict):
                        mime_type = data.get('mime_type', 'N/A')
                        data_size_kb = len(data.get('data', '')) * 3 / 4 / 1024
                        log_summary += f" -> [Content received: {mime_type}, ~{data_size_kb:.1f} KB]"

                    logger.info(log_summary)
            else:
                # Fallback for non-MCP tools, keeping it concise.
                logger.info(f"✅ Tool '{fr.name}' returned a non-standard response.")
        return

    # Log agent's thoughts only if it's not a final response.
    if event.author == analysis_agent.name and not (event.is_final_response() or event.actions.escalate):
        if event.content and event.content.parts:
            logger.info(f"🤔 Agent -> Thought: {event.content.parts[0].text}")

async def execute_analysis(work_package_id: int):
    """
    Implements the agent execution logic by creating and invoking a Runner.

    This function sets up the session, defines the initial query, and processes
    the event stream from the agent, delegating logging to a helper function.
    """
    session_service = InMemorySessionService()
    # Using a unique session ID for each run is a best practice for isolation.
    session_id = f"wp_analysis_{work_package_id}"
    await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=session_id
    )
    logger.info(f"Session created: App='{APP_NAME}', User='{USER_ID}', Session='{session_id}'")

    runner = Runner(
        agent=analysis_agent,
        app_name=APP_NAME,
        session_service=session_service
    )

    query = (
        f"Process work package {work_package_id}. Fully analyze its attachments, "
        "update its description and acceptance criteria, and then move it to the 'Specified' status."
    )
    logger.info(f"Initial query for the agent: '{query}'")
    content = types.Content(role='user', parts=[types.Part(text=query)])

    final_response_text = "Agent did not produce a final response."
    try:
        async for event in runner.run_async(user_id=USER_ID, session_id=session_id, new_message=content):
            _log_agent_event(event)

            # A turn is considered over if the agent provides a final response or escalates.
            if event.is_final_response():
                if event.content and event.content.parts:
                    final_response_text = event.content.parts[0].text
                break  # The turn has successfully concluded.

            if event.actions.escalate:
                escalation_message = "No specific message."
                if event.content and event.content.parts:
                    escalation_message = event.content.parts[0].text
                final_response_text = f"Agent escalated: {escalation_message}"
                break
    except Exception as e:
        if "429" in str(e) and "resource_exhausted" in str(e).lower():
            final_response_text = "Agent stopped due to Google AI API quota limits."
            logger.error(final_response_text)
        else:
            final_response_text = f"An unexpected error stopped the agent: {e}"
            logger.error(final_response_text, exc_info=True)

    logger.info(f"🤖 Agent Final Response: {final_response_text}")
