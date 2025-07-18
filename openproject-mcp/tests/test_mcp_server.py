# openproject-mcp/tests/test_mcp_server.py
import asyncio
import httpx
import sys
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

# --- Test Configuration ---
SERVER_URL = "http://localhost:8000/mcp"
# This Work Package ID must exist in your OpenProject instance for the test to pass.
TEST_WORK_PACKAGE_ID = 3
# The specific tool we want to validate.
TOOL_TO_TEST = "view_work_package"


async def main():
    """
    Connects to the running MCP server, lists available tools, and executes
    a specific tool to validate the end-to-end integration.
    """
    print(f"--- Starting end-to-end test against MCP server at {SERVER_URL} ---")

    # `streamablehttp_client` handles the underlying HTTP connection.
    async with streamablehttp_client(SERVER_URL) as (read_stream, write_stream, _):
        print("\n ✅ HTTP connection established successfully.")

        # `ClientSession` manages the MCP session lifecycle.
        async with ClientSession(read_stream, write_stream) as session:
            print(" ⏳ Initializing MCP session...")
            await session.initialize()
            print(" ✅ MCP session initialized successfully.")

            # --- STEP 1: List Tools ---
            print("\n--- [1/2] Testing 'list_tools' ---")
            list_response = await session.list_tools()
            tools = list_response.tools

            assert tools, "Server should return at least one tool."
            print(f" ✅ PASSED: Server returned {len(tools)} tools.")

            tool_names = [t.name for t in tools]
            assert TOOL_TO_TEST in tool_names, \
                f"The required tool '{TOOL_TO_TEST}' was not found on the server."
            print(f" ✅ Required tool '{TOOL_TO_TEST}' is available.")

            # --- STEP 2: Call a Tool ---
            print(f"\n--- [2/2] Testing 'call_tool' (Work Package ID: {TEST_WORK_PACKAGE_ID}) ---")
            tool_arguments = {"id": TEST_WORK_PACKAGE_ID}

            print(f"Attempting to execute '{TOOL_TO_TEST}' with arguments: {tool_arguments}")
            exec_response = await session.call_tool(
                name=TOOL_TO_TEST,
                arguments=tool_arguments
            )

            assert not exec_response.isError, f"Tool returned an error: {exec_response.error}"

            result_data = exec_response.structuredContent

            assert isinstance(result_data, dict), "Tool response should be a dictionary."
            assert result_data.get("id") == TEST_WORK_PACKAGE_ID, \
                f"Expected work package ID {TEST_WORK_PACKAGE_ID}, but got {result_data.get('id')}."

            print(" ✅ PASSED: Tool executed successfully.")
            print(f"   Response: {{'id': {result_data.get('id')}, 'subject': '{result_data.get('subject')}'}}")

            print("\n🎉 ALL TESTS PASSED! 🎉")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except httpx.ConnectError as e:
        print("\n❌ CONNECTION ERROR: Could not connect to the MCP server.")
        print(f"    Error: {e}")
        print("    Please ensure the server is running before executing this test.")
        sys.exit(1)
    except AssertionError as e:
        print(f"\n--- TEST FAILED: {e} ---")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ AN UNEXPECTED ERROR OCCURRED: {e}")
        # This block helps debug complex asyncio errors by unpacking them.
        if isinstance(e, BaseExceptionGroup):
            print("\n--- Breakdown of Internal Errors ---")
            for i, inner_exc in enumerate(e.exceptions):
                print(f"  Sub-exception [{i + 1}]: {type(inner_exc).__name__}: {inner_exc}")
        sys.exit(1)