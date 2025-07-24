# codegen-agent/runner.py
from google.adk.events import Event
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from agent import codegen_agent
from config import logger
from logger_utils import log_agent_event

APP_NAME = "codegen-agent-app"
USER_ID = "user_1"


# --- Agent Execution Helpers ---

async def _setup_runner_and_session(work_package_id: int) -> (str, Runner):
    """Initializes and returns the session and the agent runner."""
    session_service = InMemorySessionService()
    session_id = f"wp_codegen_{work_package_id}"
    await session_service.create_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=session_id
    )
    logger.info(f"Session created: App='{APP_NAME}', User='{USER_ID}', Session='{session_id}'")
    runner = Runner(
        agent=codegen_agent,
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
            log_agent_event(event)
            if event.is_final_response() or event.actions.escalate:
                return _get_final_text_from_event(event)
        return "Agent finished without a final response or escalation."
    except Exception as e:
        return _handle_execution_error(e)


# --- Main Orchestration Function ---

async def execute_codegen(work_package_id: int):
    """
    Orchestrates the agent execution workflow by delegating to helper functions.
    """
    session_id, runner = await _setup_runner_and_session(work_package_id)

    query_text = (
        f"Your mission is to process work package {work_package_id}. "
        "Follow your workflow to analyze its requirements, generate the Robot Framework tests, "
        "and attach the resulting test file."
    )
    logger.info(f"Initial query for the agent: '{query_text}'")
    query_content = types.Content(role="user", parts=[types.Part(text=query_text)])

    final_response_text = await _process_agent_events(
        runner, USER_ID, session_id, query_content
    )

    logger.info(f"🤖 Agent Final Response: {final_response_text}")