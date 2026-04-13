from google.adk.agents import Agent, LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters
from dotenv import load_dotenv

load_dotenv()

root_agent = LlmAgent(
    model="gemini-3.1-pro-preview",
    name="root_agent",
    description="Queries MySQL and PostgreSQL databases using natural language.",
    instruction=(
        "You are a dual-database coordinator. Determine the target DB first:\n"
        "1. POSTGRESQL (Products/Orders): Use the PostgreSQL MCP tool. "
        "   IMPORTANT: Use standard SQL. The schema 'productsdb' is already set as default.\n"
        "2. MYSQL (Employees/Projects): Use the MySQL MCP tool.\n\n"

        "RULES:\n"
        "- If you are unsure of column names, call the tool's 'list_tables' or 'describe' functions first.\n"
        "- Do not explain the SQL; just provide the final answer based on the data returned.\n"
        "- If a tool returns an error, correct your syntax and try once more."
    ),
    tools=[
        # ── PostgreSQL — pgedge via Docker ────────────────────
        # PGEDGE_DB_SCHEMA forces search_path to productsdb
        MCPToolset(
            connection_params=StdioServerParameters(
                command="docker",
                args=[
                    "run", "-i", "--rm",
                    "--add-host", "host.docker.internal:host-gateway",
                    "-e", "PGEDGE_DB_HOST=host.docker.internal",
                    "-e", "PGEDGE_DB_PORT=5432",
                    "-e", "PGEDGE_DB_NAME=postgres",
                    "-e", "PGEDGE_DB_USER=postgres",
                    "-e", "PGEDGE_DB_PASSWORD=postgres123",
                    "-e", "PGEDGE_DB_SCHEMA=productsdb",  # 👈 forces schema/search_path
                    "ghcr.io/pgedge/postgres-mcp:latest",
                ],
            ),
        ),

        # ── MySQL — demo_company via npx ──────────────────────
        MCPToolset(
            connection_params=StdioServerParameters(
                command="npx",
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