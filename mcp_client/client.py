import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import ToolMessage
import json


load_dotenv()

SERVERS = { 
    "Aditya Server Proxy": {
        "transport": "streamable_http",  # if this fails, try "sse"
        "url": "https://aggregate-rose-orca.fastmcp.app/mcp" #it is the fastmcp.cloud url of a remote server
    },
    "manim-server": {
      "command": "C:/Users/username/AppData/Local/Programs/Python/Python313/python.exe",
      "args": [
        "C:/Users/username/Downloads/manim-mcp-server/src/manim_server.py"
      ],
      "env": {
        "MANIM_EXECUTABLE": "C:/Users/username/AppData/Local/Programs/Python/Python313/Scripts/manim.exe"
      },
      "transport": "stdio",
    },
}

async def main():
    
    client = MultiServerMCPClient(SERVERS)
    tools = await client.get_tools()


    named_tools = {}
    for tool in tools:
        named_tools[tool.name] = tool

    print("Available tools:", named_tools.keys())

    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
    llm_with_tools = llm.bind_tools(tools)

    prompt = "Draw a tringle rotating in place using the manim tool"
    response = await llm_with_tools.ainvoke(prompt)

    if not getattr(response, "tool_calls", None):
        print("\nLLM Reply:", response.content)
        return

    tool_messages = []
    for tc in response.tool_calls:
        selected_tool = tc["name"]
        selected_tool_args = tc.get("args") or {}
        selected_tool_id = tc["id"]

        result = await named_tools[selected_tool].ainvoke(selected_tool_args)
        tool_messages.append(ToolMessage(tool_call_id=selected_tool_id, content=json.dumps(result)))
        

    final_response = await llm_with_tools.ainvoke([prompt, response, *tool_messages])
    print(f"Final response: {final_response.content}")


if __name__ == '__main__':
    asyncio.run(main())
