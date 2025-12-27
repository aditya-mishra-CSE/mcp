# # app.py — Minimal MCP + Streamlit chat (correct tool message ordering, no filler rendered)

# import os
# import json
# import asyncio
# import streamlit as st
# from dotenv import load_dotenv

# # from langchain_openai import ChatOpenAI
# from langchain_google_genai import ChatGoogleGenerativeAI

# from langchain_mcp_adapters.client import MultiServerMCPClient
# from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage


# # ─────────────────────────────
# # MCP servers: local math via uv + fastmcp
# # ─────────────────────────────
# SERVERS = { 
#     "Aditya Server Proxy": {
#         "transport": "streamable_http",  # if this fails, try "sse"
#         "url": "https://aggregate-rose-orca.fastmcp.app/mcp"
#     },
#     "manim-server": {
#       "command": "C:/Users/aditya.mishra01/AppData/Local/Programs/Python/Python313/python.exe",
#       "args": [
#         "C:/Users/aditya.mishra01/Downloads/manim-mcp-server/src/manim_server.py"
#       ],
#       "env": {
#         "MANIM_EXECUTABLE": "C:/Users/aditya.mishra01/AppData/Local/Programs/Python/Python313/Scripts/manim.exe"
#       },
#       "transport": "stdio",
#     },
# }


# SYSTEM_PROMPT = (
#     "You have access to tools. When you choose to call a tool, do not narrate status updates. "
#     "After tools run, return only a concise final answer."
# )

# st.set_page_config(page_title="MCP Chat", page_icon="🧰", layout="centered")
# st.title("🧰 MCP Chat")

# load_dotenv()

# # One-time init
# if "initialized" not in st.session_state:
#     # 1) LLM
#     st.session_state.llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")


#     # 2) MCP tools
#     st.session_state.client = MultiServerMCPClient(SERVERS)
#     tools = asyncio.run(st.session_state.client.get_tools())
#     st.session_state.tools = tools
#     st.session_state.tool_by_name = {t.name: t for t in tools}

#     # 3) Bind tools
#     st.session_state.llm_with_tools = st.session_state.llm.bind_tools(tools)

#     # 4) Conversation state
#     st.session_state.history = [SystemMessage(content=SYSTEM_PROMPT)]
#     st.session_state.initialized = True

# # Render chat history (skip system + tool messages; hide intermediate AI with tool_calls)
# for msg in st.session_state.history:
#     if isinstance(msg, HumanMessage):
#         with st.chat_message("user"):
#             st.markdown(msg.content)
#     elif isinstance(msg, AIMessage):
#         # Skip assistant messages that contain tool_calls (intermediate “fetching…”)
#         if getattr(msg, "tool_calls", None):
#             continue
#         with st.chat_message("assistant"):
#             st.markdown(msg.content)
#     # ToolMessage and SystemMessage are not rendered as bubbles

# # Chat input
# user_text = st.chat_input("Type a message…")
# if user_text:
#     with st.chat_message("user"):
#         st.markdown(user_text)
#     st.session_state.history.append(HumanMessage(content=user_text))

#     # First pass: let the model decide whether to call tools
#     first = asyncio.run(st.session_state.llm_with_tools.ainvoke(st.session_state.history))
#     tool_calls = getattr(first, "tool_calls", None)

#     if not tool_calls:
#         # No tools → show & store assistant reply
#         with st.chat_message("assistant"):
#             st.markdown(first.content or "")
#         st.session_state.history.append(first)
#     else:
#         # ── IMPORTANT ORDER ──
#         # 1) Append assistant message WITH tool_calls (do NOT render)
#         st.session_state.history.append(first)

#         # 2) Execute requested tools and append ToolMessages (do NOT render)
#         tool_msgs = []
#         for tc in tool_calls:
#             name = tc["name"]
#             args = tc.get("args") or {}
#             if isinstance(args, str):
#                 try:
#                     args = json.loads(args)
#                 except Exception:
#                     pass
#             tool = st.session_state.tool_by_name[name]
#             res = asyncio.run(tool.ainvoke(args))
#             tool_msgs.append(ToolMessage(tool_call_id=tc["id"], content=json.dumps(res)))

#         st.session_state.history.extend(tool_msgs)

#         # 3) Final assistant reply using tool outputs → render & store
#         final = asyncio.run(st.session_state.llm.ainvoke(st.session_state.history))
#         with st.chat_message("assistant"):
#             st.markdown(final.content or "")
#         st.session_state.history.append(AIMessage(content=final.content or ""))




# app.py — MCP + Streamlit chat (event-loop safe, production ready)

import os
import json
import asyncio
import streamlit as st
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.messages import (
    HumanMessage,
    AIMessage,
    ToolMessage,
    SystemMessage,
)

# ─────────────────────────────
# MCP server configuration
# ─────────────────────────────
SERVERS = {
    "Aditya Server Proxy": {
        "transport": "streamable_http",  # fallback: "sse"
        "url": "https://aggregate-rose-orca.fastmcp.app/mcp",
    },
    "manim-server": {
        "command": "C:/Users/aditya.mishra01/AppData/Local/Programs/Python/Python313/python.exe",
        "args": [
            "C:/Users/aditya.mishra01/Downloads/manim-mcp-server/src/manim_server.py"
        ],
        "env": {
            "MANIM_EXECUTABLE": (
                "C:/Users/aditya.mishra01/"
                "AppData/Local/Programs/Python/Python313/Scripts/manim.exe"
            )
        },
        "transport": "stdio",
    },
}

SYSTEM_PROMPT = (
    "You have access to tools. When you choose to call a tool, "
    "do not narrate status updates. After tools run, return only "
    "a concise final answer."
)

# ─────────────────────────────
# Streamlit setup
# ─────────────────────────────
st.set_page_config(page_title="MCP Chat", page_icon="🧰", layout="centered")
st.title("🧰 MCP Chat")

load_dotenv()


# ─────────────────────────────
# Async helper (CRITICAL)
# ─────────────────────────────
def run_async(coro):
    """Run async code on Streamlit-safe persistent loop."""
    return st.session_state.loop.run_until_complete(coro)


# ─────────────────────────────
# One-time initialization
# ─────────────────────────────
if "initialized" not in st.session_state:
    # ✅ Create ONE event loop for entire app lifetime
    st.session_state.loop = asyncio.new_event_loop()
    asyncio.set_event_loop(st.session_state.loop)

    # LLM
    st.session_state.llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash"
    )

    # MCP client (created ONCE)
    st.session_state.client = MultiServerMCPClient(SERVERS)

    # Load tools (NO asyncio.run)
    tools = run_async(st.session_state.client.get_tools())
    st.session_state.tools = tools
    st.session_state.tool_by_name = {t.name: t for t in tools}

    # Bind tools to LLM
    st.session_state.llm_with_tools = (
        st.session_state.llm.bind_tools(tools)
    )

    # Conversation history
    st.session_state.history = [
        SystemMessage(content=SYSTEM_PROMPT)
    ]

    st.session_state.initialized = True


# ─────────────────────────────
# Render chat history
# ─────────────────────────────
for msg in st.session_state.history:
    if isinstance(msg, HumanMessage):
        with st.chat_message("user"):
            st.markdown(msg.content)

    elif isinstance(msg, AIMessage):
        # Skip intermediate tool-call messages
        if getattr(msg, "tool_calls", None):
            continue
        with st.chat_message("assistant"):
            st.markdown(msg.content)

    # ToolMessage & SystemMessage are intentionally hidden


# ─────────────────────────────
# Chat input
# ─────────────────────────────
user_text = st.chat_input("Type a message…")

if user_text:
    # Show user message
    with st.chat_message("user"):
        st.markdown(user_text)

    st.session_state.history.append(
        HumanMessage(content=user_text)
    )

    # ── First LLM pass (tool decision) ──
    first = run_async(
        st.session_state.llm_with_tools.ainvoke(
            st.session_state.history
        )
    )

    tool_calls = getattr(first, "tool_calls", None)

    # ─────────────────────────
    # Case 1: No tools needed
    # ─────────────────────────
    if not tool_calls:
        with st.chat_message("assistant"):
            st.markdown(first.content or "")
        st.session_state.history.append(first)

    # ─────────────────────────
    # Case 2: Tool calls present
    # ─────────────────────────
    else:
        # 1️⃣ Append assistant message WITH tool_calls (do not render)
        st.session_state.history.append(first)

        # 2️⃣ Execute tools
        tool_messages = []
        for tc in tool_calls:
            tool_name = tc["name"]
            args = tc.get("args") or {}

            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except Exception:
                    pass

            tool = st.session_state.tool_by_name[tool_name]
            result = run_async(tool.ainvoke(args))

            tool_messages.append(
                ToolMessage(
                    tool_call_id=tc["id"],
                    content=json.dumps(result),
                )
            )

        st.session_state.history.extend(tool_messages)

        # 3️⃣ Final assistant response
        final = run_async(
            st.session_state.llm.ainvoke(
                st.session_state.history
            )
        )

        with st.chat_message("assistant"):
            st.markdown(final.content or "")

        st.session_state.history.append(
            AIMessage(content=final.content or "")
        )
