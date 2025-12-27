#mcp_server.py
from fastmcp import FastMCP
from main import app  #Import your fastapi app

#Convert FastAPI app to MCP server
mcp = FastMCP.from_fastapi(
    app = app,
    name="Expenses Tracker server",
)

if __name__ == "__main__":
    mcp.run()