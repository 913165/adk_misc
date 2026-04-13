# agent.py
import os
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters

# Path to your MCP server script
MCP_SERVER_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "custom_mcp_agent.py"
)

root_agent = LlmAgent(
    model="gemini-flash-latest",
    name="inventory_agent",
    description="An agent that manages inventory for Ambokts company.",
    instruction="""You are an inventory management assistant for Ambokts.
You can search products, check stock levels, and place orders.
Always confirm order details with the user before placing an order.
When searching, try partial matches if the exact term doesn't work.""",
    tools=[
        MCPToolset(
            connection_params=StdioServerParameters(
                command="python",
                args=[MCP_SERVER_PATH],
            ),
        )
    ],
)