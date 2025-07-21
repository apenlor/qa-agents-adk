from google.adk.agents import Agent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StreamableHTTPConnectionParams
from google.adk.agents import LlmAgent

# --- POC Design Comment ---
# In this POC, we are giving the agent full control over the workflow to test
# its reasoning and tool-use capabilities, triggered by an API call.
# The agent will discover and orchestrate the necessary tools from the MCP server.
#
# In a production scenario, we might add more safety rails (like direct calls to
# the API for downloading attachments or performing the work package update), but for a
# POC, this approach demonstrates the full potential of an autonomous agent.

REQUIRED_TOOLS_FOR_POC = [
    "view_work_package",
    "list_statuses",
    "list_work_package_attachments",
    "view_attachment",
    "create_work_package_attachment",
    "update_work_package",
]

toolset = MCPToolset(
    connection_params=StreamableHTTPConnectionParams(
        url="http://openproject-mcp:8000/mcp",
    ),
    tool_filter=REQUIRED_TOOLS_FOR_POC
)

analysis_agent = LlmAgent(
    name="analysis_agent_v1",
    model="gemini-2.5-pro",
    description="An autonomous agent that analyzes, updates, and transitions OpenProject work packages.",
    instruction="""
You are an autonomous Senior Business Analyst. Your goal is to process an OpenProject work package by following a precise workflow. You have been provided with a comprehensive set of tools to interact with the OpenProject API.

**Your Mission:**
You will be given a work package ID. You must fully specify the work package based on its attachments and then move it to the "Specified" state.

**High-Level Workflow:**
1.  **Investigate the Work Package:** Use your tools to find all file attachments associated with the given work package ID.
2.  **Gather Information:** Read the content of all attachments. If there are no attachments or they are empty, you must stop and report that you cannot proceed.
3.  **Synthesize and Analyze:** Based on the gathered content, formulate a concise work package 'description' and a detailed list of 'acceptance_criteria'.
4.  **Prepare for Update:** Before updating, you must find the correct ID for the "Specified" status by using your tools to list all available statuses.
5.  **Execute the Update:** Update the work package with the new description, acceptance criteria, and status. The acceptance criteria should be formatted as a markdown list and placed in the 'customField1' field. The status must be updated using the ID you found. You may need to fetch the work package's `lockVersion` to perform the update.
6.  **Report Completion:** Your final output must be a single, brief, human-readable sentence summarizing the result of your work (e.g., "Successfully analyzed 2 attachments, updated the description, and moved the work package to the 'Specified' state.").
""",
    tools=[toolset],
)

print(f"Agent '{analysis_agent.name}' created with full MCP toolset.")
