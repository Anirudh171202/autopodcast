"""Call 1: research + curate tonight's rundown.

One Claude call with the server-side web_search tool and a strict JSON
schema for the response. Web search is a server tool — Claude searches,
reads results, and reasons about them all within this single request; no
client-side tool-execution loop is needed.
"""

import json

import anthropic

from . import config
from .prompts import RESEARCH_SCHEMA, RESEARCH_SYSTEM, build_research_user_prompt


def run_research(
    client: anthropic.Anthropic,
    topics: list[str],
    instructions: str,
    recent_headlines: list[str],
    today_str: str,
    model: str = config.RESEARCH_MODEL,
) -> dict:
    user_prompt = build_research_user_prompt(topics, instructions, recent_headlines, today_str)

    with client.messages.stream(
        model=model,
        max_tokens=4096,
        system=RESEARCH_SYSTEM,
        tools=[
            {
                "type": "web_search_20260209",
                "name": "web_search",
                "max_uses": 12,
                "allowed_callers": ["direct"],
            }
        ],
        output_config={"format": {"type": "json_schema", "schema": RESEARCH_SCHEMA}},
        messages=[{"role": "user", "content": user_prompt}],
    ) as stream:
        response = stream.get_final_message()

    if response.stop_reason == "refusal":
        raise RuntimeError(f"Research call was refused: {response.stop_details}")

    text = next(b.text for b in response.content if b.type == "text")
    return json.loads(text)
