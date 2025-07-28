# analysis-agent/agent.py
import os
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StreamableHTTPConnectionParams
from google.genai.types import ToolConfig, GenerateContentConfig, FunctionCallingConfig, FunctionCallingConfigMode
from google.adk.tools.tool_context import ToolContext
from google.adk.agents.readonly_context import ReadonlyContext


# --- POC Design Comment ---
# In this POC, we are giving the agent full control over the workflow to test
# its reasoning and tool-use capabilities, triggered by an API call.
# The agent will discover and orchestrate the necessary tools from the MCP server.
#
# In a production scenario, we might add more safety rails (like direct calls to
# the API for downloading attachments or performing the work package update), but for a
# POC, this approach demonstrates the full potential of an autonomous agent.


def _load_examples_as_text() -> str:
    """
    Reads markdown example files from the 'examples' directory and formats
    them into a single string to be injected into the main instruction prompt.
    """
    example_files = [
        "examples/technical_requirements_example.md",
        "examples/user_feature_example.md"
    ]
    all_examples_text = ""
    for file_path in example_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                all_examples_text += f"--- Example: {os.path.basename(file_path)} ---\n"
                all_examples_text += content
                all_examples_text += "\n\n"
        except FileNotFoundError:
            print(f"Warning: Example file not found at {file_path}. It will be omitted from the prompt.")
    return all_examples_text


INSTRUCTION_TEMPLATE = """
You are an expert Senior Business Analyst. Your goal is to process an OpenProject work package by analyzing its attachments and generating a high-quality, formatted markdown description.

**Your Mission:**
You will be given a work package ID. You must fully specify the work package based on its attachments and then move it to the "Specified" state.

---
**REFERENCE EXAMPLES**
Here are golden-standard examples of how to transform raw requirements into a well-structured markdown block. Use them to guide the quality and format of your output.

{analysis_examples}
---

**High-Level Workflow & Tool Guide:**
1.  **Find and Read Attachments:** Use `get_work_package_attachments` and `get_attachment_content` to read the content 
of all attachments. If there are no attachments, call `exit_loop` and report this.
2.  **Analyze & Generate Markdown:** The `get_attachment_content` tool is multi-modal. For PDFs, it will return a list 
containing both the extracted text and any embedded images. You must analyze **all** of this content together to 
understand the full context and formulate your `description` and `acceptance_criteria`. Combine them into a single 
block of markdown.
3.  **Update Description:** Call `update_work_package_description` with the complete markdown block you just generated.
4.  **Find Status ID:** Call `list_statuses` to find the numerical ID for the "Specified" status.
5.  **Update Status:** Call `update_work_package_status` with the work package ID and the status ID you found.
6.  **Final Step:** Call `exit_loop` with a summary of your work.
"""

"""
Factory function to build the analysis agent, loading examples from disk
and injecting them into a context-rich instruction prompt.
"""
required_tools = [
    "get_work_package_details",
    "get_work_package_attachments",
    "get_attachment_content",
    "update_work_package_description",
    "update_work_package_status",
    "list_statuses"
]
toolset = MCPToolset(
    connection_params=StreamableHTTPConnectionParams(url="http://openproject-mcp:8000/mcp/"),
    tool_filter=required_tools
)


def exit_loop(summary: str, tool_context: ToolContext):
    """Call this as the absolute final step to complete the mission."""
    tool_context.actions.escalate = True
    return {"status": "complete", "summary": summary}


tool_config = ToolConfig(function_calling_config=FunctionCallingConfig(mode=FunctionCallingConfigMode.ANY))
generate_content_config = GenerateContentConfig(tool_config=tool_config)


def instruction_provider(ctx: ReadonlyContext) -> str:
    """Assembles the final instruction prompt at runtime to bypass template substitution."""
    analysis_examples = _load_examples_as_text()
    return INSTRUCTION_TEMPLATE.format(analysis_examples=analysis_examples)


analysis_agent = LlmAgent(
    name="analysis_agent_v1",
    model="gemini-2.5-pro",
    description="An autonomous agent that analyzes, updates, and transitions OpenProject work packages.",
    instruction=instruction_provider,
    tools=[toolset, exit_loop],
    generate_content_config=generate_content_config
)

print(f"Agent '{analysis_agent.name}' created with file-based examples.")
