# analysis-agent/runner.py
import logging

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
    Logs a human-readable summary of an agent event, following the event
    identification logic from the official ADK documentation.
    """
    logger.debug(f"--- AGENT EVENT ---\n{event!r}\n--------------------")

    # --- Event Identification Logic ---
    if event.author != analysis_agent.name:
        # Ignore events not from our agent (e.g., initial user query)
        return

    if event.content and event.content.parts:

        function_calls = event.get_function_calls()
        if function_calls:
            for fc in function_calls:
                # Si se llama a exit_loop, lo tratamos como la respuesta final.
                if fc.name == 'exit_loop':
                    summary = fc.args.get('summary', 'Workflow completed without a summary.')
                    logger.info(f"🤖 Agent -> Final Summary: {summary}")
                else:
                    logger.info(f"🛠️  Agent -> Action: Calling {fc.name}(...)")
            return

        function_responses = event.get_function_responses()
        if function_responses:
            for fr in function_responses:
                response_payload = fr.response.get("result")
                if isinstance(response_payload, CallToolResult):
                    if response_payload.isError:
                        error_msg = response_payload.content[0].text if response_payload.content else "Unknown error"
                        logger.warning(f"❌ Tool Error in '{fr.name}': {error_msg}")
                    else:
                        log_summary = f"✅ Tool Success: {fr.name}"
                        data = response_payload.structuredContent
                        if fr.name == 'get_work_package_details' and isinstance(data, dict):
                            log_summary += f" -> [ID: {data.get('id')}, Subject: '{data.get('subject')}', lockVersion: {data.get('lockVersion')}]"
                        elif fr.name == 'get_work_package_attachments' and isinstance(data, list):
                            filenames = [att.get('fileName', 'N/A') for att in data]
                            log_summary += f" -> Found {len(data)} attachment(s): {filenames}"
                        elif fr.name == 'get_attachment_content' and isinstance(data, dict):
                            mime_type = data.get('mime_type', 'N/A')
                            data_size_kb = len(data.get('data', '')) * 3 / 4 / 1024
                            log_summary += f" -> [Content received: {mime_type}, ~{data_size_kb:.1f} KB]"
                        logger.info(log_summary)
                else:
                    logger.info(f"✅ Tool '{fr.name}' returned a non-standard response.")

        # Keeping it for failure texts situations
        elif event.is_final_response() and event.author == analysis_agent.name:
            if event.content and event.content.parts and event.content.parts[0].text:
                logger.info(f"🤖 Agent -> Final Response: {event.content.parts[0].text.strip()}")


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
