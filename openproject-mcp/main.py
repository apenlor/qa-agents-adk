# main.py
import asyncio

# MCP Server Imports
from mcp.server.lowlevel import NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.server.streamable_http

from packages.app import app
from packages.config import logger

async def run_mcp_server():
    """Runs the MCP server, listening for connections over a gRPC network port."""
    # Use the stdio_server context manager from the mcp.server.stdio library
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        logger.info("MCP Stdio Server: Starting handshake with client...")
        await app.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name=app.name,  # Use the server name defined in main.py
                server_version="0.1.0",
                capabilities=app.get_capabilities(
                    # Define server capabilities - consult MCP docs for options
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )
        logger.info("MCP Stdio Server: Run loop finished or client disconnected.")


if __name__ == "__main__":
    logger.info("Launching MCP Server to expose ADK tools via stdio...")
    try:
        asyncio.run(run_mcp_server())
    except KeyboardInterrupt:
        logger.info("MCP Server (stdio) stopped by user.")
    except Exception as e:
        logger.error(f"MCP Server (stdio) encountered an error: {e}", exc_info=True)
    finally:
        logger.info("MCP Server (stdio) process exiting.")