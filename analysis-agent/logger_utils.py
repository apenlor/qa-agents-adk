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


def _format_attachment_content(content_blocks: List[Any]) -> str:
    """
    Formats a log summary for get_attachment_content by analyzing the list
    of received content blocks (text, images, etc.).
    """
    if not isinstance(content_blocks, list):
        return " -> [Received content but in an unexpected format]"

    text_blocks = [block for block in content_blocks if isinstance(block, TextContent)]
    image_blocks = [block for block in content_blocks if isinstance(block, ImageContent)]

    summary_parts = []
    total_kb = 0

    if text_blocks:
        text_size_kb = sum(len(block.text.encode('utf-8')) for block in text_blocks) / 1024
        total_kb += text_size_kb
        summary_parts.append(f"{len(text_blocks)} text block(s)")

    if image_blocks:
        image_size_kb = sum(len(block.data) * 3 / 4 for block in image_blocks) / 1024
        total_kb += image_size_kb
        summary_parts.append(f"{len(image_blocks)} image(s)")

    if not summary_parts:
        return " -> [Received empty content]"

    return f" -> [Received {', '.join(summary_parts)} (~{total_kb:.1f} KB total)]"


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

    # Handle tools that return JSON in structuredContent
    if result.structuredContent is not None:
        data = result.structuredContent
        if tool_name == 'get_work_package_details':
            return base_log + _format_wp_details(data)
        if tool_name == 'get_work_package_attachments':
            return base_log + _format_wp_attachments(data)

    # Handle tools that return a list of ContentBlocks
    elif result.content:
        # The data is the entire list of content blocks
        data = result.content
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
