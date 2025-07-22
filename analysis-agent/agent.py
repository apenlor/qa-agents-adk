from google.adk.agents import Agent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StreamableHTTPConnectionParams
from google.adk.agents import LlmAgent
from google.genai.types import ToolConfig, GenerateContentConfig, FunctionCallingConfig

# --- POC Design Comment ---
# In this POC, we are giving the agent full control over the workflow to test
# its reasoning and tool-use capabilities, triggered by an API call.
# The agent will discover and orchestrate the necessary tools from the MCP server.
#
# In a production scenario, we might add more safety rails (like direct calls to
# the API for downloading attachments or performing the work package update), but for a
# POC, this approach demonstrates the full potential of an autonomous agent.


# Initializes ToolSet
toolset = MCPToolset(
    connection_params=StreamableHTTPConnectionParams(
        url="http://openproject-mcp:8000/mcp",
    )
)

# Create the tool configuration to disable the model's automatic loop
# tool_config = ToolConfig(
#     function_calling_config=FunctionCallingConfig(
#         # ANY mode ensures the model calls a tool and then returns control to our Runner.
#         mode=ToolConfig.FunctionCallingConfig.Mode.ANY
#     )
# )

analysis_agent = LlmAgent(
    name="analysis_agent_v1",
    model="gemini-2.5-pro",
    description="An autonomous agent that analyzes, updates, and transitions OpenProject work packages.",
    instruction="""
    You are an autonomous Senior Business Analyst. You have a set of specific tools to process an OpenProject work package.
    
    **Your Mission:**
    You will be given a work package ID. You must fully specify it based on its attachments and then move it to the "Specified" state.
    
    **High-Level Workflow & Tool Guide:**
    1.  **Get Details:** Use `get_work_package_details` to get current information like the `lockVersion`.
    2.  **Find Attachments:** Use `get_work_package_attachments` to list all file attachments.
    3.  **Read Content:** For each attachment, use `get_attachment_content`.
        -- IMPORTANT: This tool returns a JSON object: `{"mime_type": "...", "data": "..."}` where 'data' is the Base64 encoded file content.
        -- You can pass this object directly to the model for multi-modal analysis (e.g., to understand an image).
    4.  **Analyze & Prepare:** Based on the content of all attachments, formulate a new `description` and a list of `acceptance_criteria`.
    5.  **Update Description & Status:** Use `update_work_package_description` and `update_work_package_status` to apply your changes. Remember to use the latest `lockVersion` for each update. Use `list_statuses` to find the ID for the "Specified" status.
    6.  **Report Completion:** Your final output must be a single, brief, human-readable sentence summarizing your work.
    """,
    tools=[toolset]
    # generate_content_config=GenerateContentConfig(tool_config=tool_config)
)

print(f"Agent '{analysis_agent.name}' created with full MCP toolset.")
