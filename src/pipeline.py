"""Nightly entrypoint: research -> script -> TTS -> feed. Run as:

    python -m src.pipeline

Reads config/topics.yaml, ANTHROPIC_API_KEY, and OPENAI_API_KEY (from the
environment, or a local .env via python-dotenv). Writes an mp3 under
docs/episodes/, regenerates docs/feed.xml, and updates state/.
"""

import json
import os
from datetime import date

import anthropic
import mutagen.mp3
from dotenv import load_dotenv

from . import config, feed
from .research import run_research
from .script import run_script
from .tts import synthesize

MIN_WORDS = 500
BASELINE_ITEMS_FOR_FULL_LENGTH = 7


def load_history() -> list[dict]:
    if config.HISTORY_PATH.exists():
        with open(config.HISTORY_PATH) as f:
            return json.load(f)
    return []


def save_history(history: list[dict], keep_days: int = 60) -> None:
    config.STATE_DIR.mkdir(parents=True, exist_ok=True)
    history = history[-keep_days:]
    with open(config.HISTORY_PATH, "w") as f:
        json.dump(history, f, indent=2)


def recent_headlines(history: list[dict], lookback_days: int) -> list[str]:
    headlines: list[str] = []
    for entry in history[-lookback_days:]:
        headlines.extend(entry.get("headlines", []))
    return headlines


def sort_items_by_importance(rundown: dict) -> dict:
    rundown["items"] = sorted(rundown["items"], key=lambda i: i.get("importance", 0), reverse=True)
    return rundown


def target_word_count(cfg: dict, item_count: int) -> int:
    full_target = cfg["target_minutes"] * config.WORDS_PER_MINUTE
    if item_count >= BASELINE_ITEMS_FOR_FULL_LENGTH:
        return full_target
    scaled = round(full_target * item_count / BASELINE_ITEMS_FOR_FULL_LENGTH)
    return max(MIN_WORDS, scaled)


def build_episode_title(rundown: dict, today_str: str) -> str:
    items = rundown.get("items", [])
    if not items:
        return f"{today_str}: Quiet news day"
    top = items[0]["headline"]
    return f"{today_str}: {top}" if len(top) < 80 else f"{today_str} briefing"


def build_episode_description(rundown: dict) -> str:
    headlines = [i["headline"] for i in rundown.get("items", [])]
    if not headlines:
        return rundown.get("editor_note") or "A quiet news day."
    return "In this episode: " + "; ".join(headlines[:6]) + "."


def main() -> None:
    load_dotenv()
    cfg = config.load_topics_config()
    today = date.today()
    today_str = today.isoformat()

    history = load_history()
    headlines_to_avoid = recent_headlines(history, cfg["lookback_days"])

    client = anthropic.Anthropic()

    print(f"[{today_str}] researching...")
    rundown = run_research(
        client,
        topics=cfg["topics"],
        instructions=cfg["instructions"],
        recent_headlines=headlines_to_avoid,
        today_str=today_str,
    )
    rundown = sort_items_by_importance(rundown)
    item_count = len(rundown["items"])
    print(f"[{today_str}] found {item_count} item(s)."
          f" insufficient_material={rundown.get('insufficient_material')}")
    if rundown.get("editor_note"):
        print(f"[{today_str}] editor note: {rundown['editor_note']}")

    if item_count == 0:
        print(f"[{today_str}] nothing to publish tonight — skipping episode.")
        return

    words = target_word_count(cfg, item_count)
    print(f"[{today_str}] writing script (~{words} words)...")
    script_text = run_script(client, rundown, words)

    config.SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(config.SCRIPTS_DIR / f"{today_str}.txt", "w") as f:
        f.write(script_text)

    mp3_rel_path = f"episodes/{today_str}.mp3"
    mp3_abs_path = str(config.DOCS_DIR / mp3_rel_path)
    print(f"[{today_str}] synthesizing audio ({len(script_text.split())} words)...")
    synthesize(script_text, mp3_abs_path)

    duration_seconds = mutagen.mp3.MP3(mp3_abs_path).info.length
    size_bytes = os.path.getsize(mp3_abs_path)

    index = feed.load_index()
    index = feed.add_episode(
        index,
        date_str=today_str,
        title=build_episode_title(rundown, today_str),
        description=build_episode_description(rundown),
        file_rel_path=mp3_rel_path,
        duration_seconds=duration_seconds,
        size_bytes=size_bytes,
    )
    index = feed.prune_old_episodes(index, cfg["episode_retention_days"])
    feed.save_index(index)
    feed.build_feed(index, cfg)

    history.append({"date": today_str, "headlines": [i["headline"] for i in rundown["items"]]})
    save_history(history)

    print(f"[{today_str}] done: {mp3_rel_path} ({duration_seconds:.0f}s, {size_bytes} bytes)")


if __name__ == "__main__":
    main()
