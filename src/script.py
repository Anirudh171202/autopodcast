"""Call 2: turn the rundown JSON into a script meant to be read aloud."""

import anthropic

from . import config
from .prompts import SCRIPT_SYSTEM, build_script_user_prompt


def run_script(
    client: anthropic.Anthropic,
    rundown: dict,
    target_words: int,
    model: str = config.SCRIPT_MODEL,
) -> str:
    user_prompt = build_script_user_prompt(rundown, target_words)

    with client.messages.stream(
        model=model,
        max_tokens=8000,
        system=SCRIPT_SYSTEM,
        messages=[{"role": "user", "content": user_prompt}],
    ) as stream:
        response = stream.get_final_message()

    if response.stop_reason == "refusal":
        raise RuntimeError(f"Script call was refused: {response.stop_details}")

    return next(b.text for b in response.content if b.type == "text").strip()
