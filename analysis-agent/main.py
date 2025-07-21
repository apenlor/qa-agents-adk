# analysis-agent/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from config import logger
from runner import execute_analysis
from agent import analysis_agent

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages the application's lifecycle to ensure clean resource handling.
    The MCPToolset maintains a persistent network connection, which must be
    closed gracefully on shutdown to prevent resource leaks.
    """
    # El código aquí se ejecuta al arrancar la aplicación (si es necesario)
    yield
    # El código aquí se ejecuta al apagar la aplicación
    logger.info("Application is shutting down. Closing MCP toolset connection...")
    if analysis_agent.tools:
        await analysis_agent.tools[0].close()
    logger.info("MCP toolset connection closed.")

# --- FastAPI App Initialization ---
app = FastAPI(
    title="Analysis Agent Service",
    description="An API to trigger an autonomous analysis agent on OpenProject work packages.",
)


# --- API Data Models ---
class WebhookRequest(BaseModel):
    work_package_id: int


# --- API Endpoint ---
@app.post("/analyse-work-package")
async def analyse_work_package(request: WebhookRequest, background_tasks: BackgroundTasks):
    """
    Webhook endpoint to trigger the autonomous analysis of a work package.
    It delegates the execution to the runner function as a background task.
    """
    wp_id = request.work_package_id
    logger.info(f"Webhook received for work package ID: {wp_id}. Starting agent in background.")

    background_tasks.add_task(execute_analysis, wp_id)

    return {"status": "accepted", "message": f"Analysis workflow started for work package {wp_id}."}
