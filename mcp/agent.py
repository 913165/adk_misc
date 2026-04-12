from google.adk.agents import Agent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters
from dotenv import load_dotenv
load_dotenv()


root_agent = Agent(
    model="gemini-2.5-flash",
    name="root_agent",
    description="Queries a MySQL database using natural language.",
    instruction=(
        "You are a helpful database assistant connected to a MySQL database called demo_company. "
        "It has these tables: department, employee, project, employee_project. "
        "Use the available tools to run SQL queries and answer the user's questions. "
        "Always show results in a clean readable format."
    ),
    tools=[
        MCPToolset(
            connection_params=StdioServerParameters(
                command="npx.cmd",   # use "npx" on Mac/Linux
                args=["-y", "@benborla29/mcp-server-mysql"],
                env={
                    "MYSQL_HOST": "localhost",
                    "MYSQL_PORT": "3306",
                    "MYSQL_USER": "root",
                    "MYSQL_PASS": "root123",
                    "MYSQL_DB": "demo_company",
                    "ALLOW_INSERT_OPERATION": "false",
                    "ALLOW_UPDATE_OPERATION": "false",
                    "ALLOW_DELETE_OPERATION": "false",
                },
            ),
        ),
    ],
)