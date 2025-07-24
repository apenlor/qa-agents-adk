# analysis-agent/logger_utils.py
from typing import Any, Dict, List

from google.adk.events import Event
from google.genai import types
from mcp.types import CallToolResult, ImageContent, TextContent

from agent import analysis_agent
from config import logger


# --- Log Formatting Helpers ---

def _format_wp_details(data: Dict[str, Any]) -> str:
    """Formats a log summary for get_work_package_details."""
    return (
        f" -> [ID: {data.get('id')}, Status: '{data.get('status')}', "
        f"Subject: '{data.get('subject')}']"
    )


def _format_wp_attachments(data: List[Dict[str, Any]]) -> str:
    """Formats a log summary for get_work_package_attachments."""
    return f" -> Found {len(data)} attachment(s)"


def _format_attachment_content(content_block: Any) -> str:
    """Formats a log summary for get_attachment_content."""
    if isinstance(content_block, ImageContent):
        mime_type = content_block.mimeType or 'N/A'
        data_size_kb = len(content_block.data) * 3 / 4 / 1024
        return f" -> [Content received: {mime_type}, ~{data_size_kb:.1f} KB]"
    elif isinstance(content_block, TextContent):
        data_size_kb = len(content_block.text.encode('utf-8')) / 1024
        return f" -> [Content received: text/plain, ~{data_size_kb:.1f} KB]"
    return " -> [Content received but format is unrecognized]"


# --- Event Logging Helpers ---

def _log_function_calls(function_calls: List[types.FunctionCall]) -> None:
    """Logs agent actions (tool calls)."""
    for fc in function_calls:
        if fc.name == "exit_loop":
            summary = fc.args.get("summary", "Workflow completed without a summary.")
            logger.info(f"🤖 Agent -> Final Summary: {summary}")
        else:
            logger.info(f"🛠️  Agent -> Action: Calling {fc.name}(...)")


def _format_tool_success_log(tool_name: str, result: CallToolResult) -> str:
    """Creates a detailed log summary for a successful tool call."""
    base_log = f"✅ Tool Success: {tool_name}"

    if result.structuredContent is not None:
        data = result.structuredContent
        if tool_name in ['get_work_package_details', 'get_work_package_attachments']:
            formatter = {
                "get_work_package_details": _format_wp_details,
                "get_work_package_attachments": _format_wp_attachments,
            }.get(tool_name)
            return base_log + formatter(data) if formatter else base_log

    elif result.content:
        data = result.content[0]
        if tool_name == 'get_attachment_content':
            return base_log + _format_attachment_content(data)

    return base_log


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
    if event.author != analysis_agent.name:
        return  # Ignore events not from our agent (e.g., initial user query)

    logger.debug(f"--- AGENT EVENT ---\n{event!r}\n--------------------")

    if function_calls := event.get_function_calls():
        _log_function_calls(function_calls)
    elif function_responses := event.get_function_responses():
        _log_function_responses(function_responses)
    elif event.is_final_response() and event.content and event.content.parts:
        logger.info(f"🤖 Agent -> Final Response: {event.content.parts[0].text.strip()}")
