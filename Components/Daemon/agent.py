import asyncio
import os
import logging
from pathlib import Path
import httpx
from dotenv import load_dotenv
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
import re

try:
    from .PROMPT import WRITER_AGENT_SYSTEM_PROMPT
except ImportError:
    from PROMPT import WRITER_AGENT_SYSTEM_PROMPT


load_dotenv(Path(__file__).with_name(".env"))
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)
logger.info("Daemon agent module loading")
print("[agent] Daemon agent module loading")


class RetrieveInput(BaseModel):
    query: str = Field(description="The specific piece of missing information to search for in the vector DB")


@tool("get_extra_context", args_schema=RetrieveInput)
async def get_extra_context(query: str) -> str:
    """Query the vector DB retrieval endpoint for information missing from current context or recent history."""
    logger.info("Retrieval requested (query_length=%d)", len(query))
    print(f"[agent] Retrieval requested (query_length={len(query)})")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            logger.info("Posting retrieval request to http://localhost:8000/retrieve")
            print("[agent] Posting retrieval request")
            response = await client.post(
                "http://localhost:8000/retrieve",
                json={"query": query},
            )
            logger.info("Retrieval response received (status_code=%d)", response.status_code)
            print(f"[agent] Retrieval response received (status_code={response.status_code})")
            response.raise_for_status()
            data = response.json()
            logger.info("Retrieval response JSON parsed")
            print("[agent] Retrieval response JSON parsed")
            return str(data)
    except httpx.RequestError as e:
        logger.exception("Retrieval request failed")
        print(f"[agent] Retrieval request failed: {e}")
        return f"Retrieval request failed: {e}"
    except httpx.HTTPStatusError as e:
        logger.exception("Retrieval endpoint returned status %d", e.response.status_code)
        print(f"[agent] Retrieval endpoint returned status {e.response.status_code}")
        return f"Retrieval endpoint returned an error: {e.response.status_code}"


model = ChatOpenAI(
    model="deepseek/deepseek-chat-v3.1",
    temperature=0,
    max_tokens=500,
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)
logger.info("Chat model configured (model=deepseek/deepseek-chat-v3.1)")
print("[agent] Chat model configured")

agent = create_react_agent(model, tools=[get_extra_context])
logger.info("React agent created with get_extra_context tool")
print("[agent] React agent created")



async def call_agent(context: str) -> str:
    logger.info("call_agent started (context_length=%d)", len(context))
    print(f"[agent] call_agent started (context_length={len(context)})")

    log_path = Path(__file__).resolve().parent.parent / "Data_collector_service" / "log.txt"

    with log_path.open("r", encoding="utf-8") as f:
        file_content = f.read()

    logger.info("Activity log read (characters=%d)", len(file_content))
    print(f"[agent] Activity log read (characters={len(file_content)})")

    logger.info("Invoking writing agent")
    print("[agent] Invoking writing agent")

    result = await agent.ainvoke({
        "messages": [
            {
                "role": "system",
                "content": WRITER_AGENT_SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": (
                    "YOUR CURRENT CONTEXT/STATE IS : "
                    + context
                    + "\n\nPREVIOUS CONTEXT: "
                    + file_content
                ),
            },
        ]
    })

    last_message = result["messages"][-1]
    response = last_message.content

    logger.info("Raw agent response: %s", response)
    print(f"[agent] Raw agent response: {response}")


    match = re.search(r"<reply>(.*?)</reply>", response, re.DOTALL)

    if not match:
        logger.warning("No <reply> tags found in agent response")
        print("[agent] No <reply> tags found")

        return ""

    reply = match.group(1).strip()

    logger.info("Final reply extracted (length=%d)", len(reply))
    print(f"[agent] Final reply: {reply}")

    return reply
