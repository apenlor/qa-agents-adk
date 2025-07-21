# analysis-agent/runner.py
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from google.adk.events import Event
from mcp.types import CallToolResult

from config import logger
from agent import analysis_agent

APP_NAME = "analysis-agent-app"
USER_ID = "user_1"


def _log_agent_event(event: Event) -> None:
    """
    Logs a structured, human-readable summary of an agent event.

    This function inspects the event's content and logs key information, such as
    function calls, function responses (including errors), and agent thoughts.
    The full event object is logged at the DEBUG level for detailed inspection.
    """
    logger.debug(f"--- AGENT EVENT ---\n{event}\n--------------------")

    function_calls = event.get_function_calls()
    function_responses = event.get_function_responses()

    if function_calls:
        calls_str = ", ".join([f"{fc.name}(...)" for fc in function_calls])
        logger.info(f"🛠️  Agent -> Tool: Calling {calls_str}")
    elif function_responses:
        for fr in function_responses:
            response_payload = fr.response

            # The MCPToolset returns a CallToolResult object, not a dict.
            # We must handle this specific object type to access its attributes.
            if isinstance(response_payload, CallToolResult):
                if response_payload.isError:
                    # The error message is in the 'content' attribute.
                    error_msg = "Unknown error"
                    if response_payload.content and response_payload.content[0].text:
                        error_msg = response_payload.content[0].text
                    logger.warning(f"❌ Tool Error in '{fr.name}': {error_msg}")
                else:
                    logger.info(f"✅ Tool Success: {fr.name}")
            else:
                # Fallback for other potential tool types.
                logger.info(f"✅ Tool Result '{fr.name}': {response_payload}")

    elif event.author == analysis_agent.name and not (event.is_final_response() or event.actions.escalate):
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
            break  # The turn has concluded with an escalation.

    logger.info(f"🤖 Agent Final Response: {final_response_text}")