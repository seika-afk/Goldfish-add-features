import asyncio
import os
import httpx
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from Components.Daemon.PROMPT import WRITER_AGENT_SYSTEM_PROMPT


class RetrieveInput(BaseModel):
    query: str = Field(description="The specific piece of missing information to search for in the vector DB")


@tool("get_extra_context", args_schema=RetrieveInput)
async def get_extra_context(query: str) -> str:
    """Query the vector DB retrieval endpoint for information missing from current context or recent history."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "http://localhost:8000/retrieve",
                json={"query": query},
            )
            response.raise_for_status()
            data = response.json()
            return str(data)
    except httpx.RequestError as e:
        return f"Retrieval request failed: {e}"
    except httpx.HTTPStatusError as e:
        return f"Retrieval endpoint returned an error: {e.response.status_code}"


model = ChatOpenAI(
    model="deepseek/deepseek-chat-v3.1",
    temperature=0,
    max_tokens=500,
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)

agent = create_react_agent(model, tools=[get_extra_context])


async def call_agent(context: str) -> str:
    with open("./Data_collector_service/log.txt", "r", encoding="utf-8") as f:
        file_content = f.read()

    result = await agent.ainvoke({
        "messages": [
            {"role": "system", "content": WRITER_AGENT_SYSTEM_PROMPT},
            {"role": "user", "content": context + "\n\nFILE CONTENT: " + file_content},
        ]
    })

    last_message = result["messages"][-1]
    return last_message.content
