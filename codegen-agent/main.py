# codegen-agent/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from config import logger
from runner import execute_codegen
from agent import codegen_agent

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages the application's lifecycle to ensure clean resource handling.
    The MCPToolset maintains a persistent network connection, which must be
    closed gracefully on shutdown to prevent resource leaks.
    """
    yield
    logger.info("Application is shutting down. Closing MCP toolset connection...")
    if codegen_agent.tools:
        await codegen_agent.tools[0].close()
    logger.info("MCP toolset connection closed.")

# --- FastAPI App Initialization ---
app = FastAPI(
    title="Codegen Agent Service",
    description="An API to trigger an autonomous codegen agent.",
)


# --- API Data Models ---
class WebhookRequest(BaseModel):
    work_package_id: int


# --- API Endpoint ---
@app.post("/generate-code")
async def generate_code(request: WebhookRequest, background_tasks: BackgroundTasks):
    """
    Webhook endpoint to trigger the autonomous generation of code.
    It delegates the execution to the runner function as a background task.
    """
    wp_id = request.work_package_id
    logger.info(f"Webhook received for work package ID: {wp_id}. Starting codegen agent in background.")

    background_tasks.add_task(execute_codegen, wp_id)

    return {"status": "accepted", "message": f"Codegen workflow started for work package {wp_id}."}
