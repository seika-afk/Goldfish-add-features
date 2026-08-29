import requests
import json
from PROMPT import SYSTEM_PROMPT
import os
from dotenv import load_dotenv
load_dotenv()


OPENROUTER_API_KEY =os.environ["OPENROUTER_API_KEY"]


def get_structured_entry(raw_text: str):
    response = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "anthropic/claude-3.5-sonnet",
            "messages": [
                {
                    "role": "system",
                    "content":SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": raw_text
                }
            ]
        },
        timeout=15
    )
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]

    content = content.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    return json.loads(content)
def execute_save2db_and_delete():
    # use endpoint -> to save the data from the file , using llm
    with open("log.txt","r",encoding="utf-8") as f:
        text=f.read()

    otp= get_structured_entry(text)
    response = requests.post(
         "http://localhost:8000/save",
         json=otp  ,
         timeout=5,


     )
    print(response.status_code)
    print(response.json())
    with open("log.txt", "w") as file:
        pass
