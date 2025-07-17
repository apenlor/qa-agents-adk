# handlers.py

import json
from ..config import logger
from ..tools.openproject_tools import find_tool, get_all_tools
from ..app import app
# MCP Server Imports
from mcp import types as mcp_types
from mcp.server.lowlevel import Server
# ADK <-> MCP Conversion Utility
from google.adk.tools.mcp_tool.conversion_utils import adk_to_mcp_tool_type

# Implement the MCP server's handler to list available tools
@app.list_tools()
async def list_mcp_tools() -> list[mcp_types.Tool]:
    """MCP handler to list tools this server exposes."""
    logger.info("Received list_tools request.")
    mcp_tools = []
    # Get all registered tools from our tool module
    for adk_tool in await get_all_tools():
        # Convert each ADK tool's definition to the MCP Tool schema format
        mcp_tool_schema = adk_to_mcp_tool_type(adk_tool)
        logger.info(f"Advertising tool: {mcp_tool_schema.name}")
        mcp_tools.append(mcp_tool_schema)
    return mcp_tools

# Implement the MCP server's handler to execute a tool call
@app.call_tool()
async def call_mcp_tool(
    name: str, arguments: dict
) -> list[mcp_types.Content]:
    """MCP handler to execute a tool call requested by an MCP client."""
    logger.info(f"Received call_tool request for '{name}' with args: {arguments}")

    # Find the requested tool in our registry
    adk_tool_to_run = find_tool(name)

    if adk_tool_to_run:
        try:
            # Execute the found ADK tool's run_async method.
            adk_tool_response = await adk_tool_to_run.run_async(
                args=arguments,
                tool_context=None,
            )
            logger.info(f"ADK tool '{name}' executed. Response: {adk_tool_response}")

            # Format the ADK tool's response (often a dict) into an MCP-compliant format.
            response_text = json.dumps(adk_tool_response, indent=2)
            # MCP expects a list of mcp_types.Content parts
            return [mcp_types.TextContent(type="text", text=response_text)]

        except Exception as e:
            logger.error(f"Error executing ADK tool '{name}': {e}", exc_info=True)
            # Return an error message in MCP format
            error_text = json.dumps(
                {"error": f"Failed to execute tool '{name}': {str(e)}"}
            )
            return [mcp_types.TextContent(type="text", text=error_text)]
    else:
        # Handle calls to unknown tools
        logger.warning(f"Tool '{name}' not found/exposed by this server.")
        error_text = json.dumps({"error": f"Tool '{name}' not implemented by this server."})
        return [mcp_types.TextContent(type="text", text=error_text)]