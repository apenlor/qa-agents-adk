# packages/app.py
"""
Central application module.

This module creates and configures the single MCP Server instance.
"""
from mcp.server.lowlevel import Server

app = Server("ADK OpenProject MCP Server")