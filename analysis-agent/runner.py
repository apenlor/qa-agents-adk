# analysis-agent/runner.py
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from config import logger
from agent import analysis_agent

APP_NAME = "analysis-agent-app"
USER_ID = "user_1"
SESSION_ID = "session_001"  # Using a fixed ID for simplicity


async def execute_analysis(work_package_id: int):
    """
    This function implements the agent execution logic, following ADK best practices.
    It creates a Runner, invokes it with a query, and processes the event stream.
    """
    # --- Session Management ---
    session_service = InMemorySessionService()
    # Create the specific session where the conversation will happen
    await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID
    )
    print(f"Session created: App='{APP_NAME}', User='{USER_ID}', Session='{SESSION_ID}'")

    # --- Runner ---
    logger.info(f"Starting autonomous workflow for work package ID: {work_package_id}")
    runner = Runner(
        agent=analysis_agent,
        app_name=APP_NAME,
        session_service=session_service
    )

    # --- Query ---
    query = (
        f"Process work package {work_package_id}. Fully analyze its attachments, "
        "update its description and acceptance criteria, and then move it to the 'Specified' status."
    )
    logger.info(f"Initial query for the agent: '{query}'")
    content = types.Content(role='user', parts=[types.Part(text=query)])

    # --- Execution ---
    final_response_text = "Agent did not produce a final response."  # Default
    # Key Concept: run_async executes the agent logic and yields Events.
    async for event in runner.run_async(user_id=USER_ID, session_id=SESSION_ID, new_message=content):
        logger.debug(f"--- AGENT EVENT ---\n{event}\n--------------------")
        # Key Concept: is_final_response() marks the concluding message for the turn.
        if event.is_final_response():
            if event.content and event.content.parts:
                # Assuming text response in the first part
                final_response_text = event.content.parts[0].text
            elif event.actions and event.actions.escalate:  # Handle potential errors/escalations
                final_response_text = f"Agent escalated: {event.error_message or 'No specific message.'}"
            break
    logger.info(f"🤖 Agent Final Response: {final_response_text}")
