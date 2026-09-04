"""Central place for paths, env vars, and the topics.yaml loader."""

import os
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "config" / "topics.yaml"
STATE_DIR = REPO_ROOT / "state"
SCRIPTS_DIR = STATE_DIR / "scripts"
DOCS_DIR = REPO_ROOT / "docs"
EPISODES_DIR = DOCS_DIR / "episodes"
HISTORY_PATH = STATE_DIR / "history.json"
INDEX_PATH = STATE_DIR / "episodes_index.json"
FEED_PATH = DOCS_DIR / "feed.xml"

DEFAULTS = {
    "target_minutes": 10,
    "lookback_days": 5,
    "episode_retention_days": 21,
    "feed_base_url": "https://YOUR-GITHUB-USERNAME.github.io/autopodcast",
    "podcast_title": "My Nightly Briefing",
    "podcast_description": "An automatically researched and narrated daily briefing.",
    "instructions": "",
}


def load_topics_config() -> dict:
    with open(CONFIG_PATH) as f:
        cfg = yaml.safe_load(f) or {}
    for key, value in DEFAULTS.items():
        cfg.setdefault(key, value)
    if not cfg.get("topics"):
        raise ValueError(f"{CONFIG_PATH} needs at least one entry under `topics:`")
    return cfg


# Model choice is deliberately cheap-by-default: research is a structured
# extraction task well within Haiku's ability, script writing benefits more
# from Sonnet's prose quality. Override via env vars if you want to spend
# more for better writing (e.g. SCRIPT_MODEL=claude-opus-5).
RESEARCH_MODEL = os.environ.get("RESEARCH_MODEL", "claude-haiku-4-5")
SCRIPT_MODEL = os.environ.get("SCRIPT_MODEL", "claude-sonnet-5")

TTS_MODEL = os.environ.get("TTS_MODEL", "gpt-4o-mini-tts")
TTS_VOICE = os.environ.get("TTS_VOICE", "onyx")
# Optional steering text for gpt-4o-mini-tts's `instructions` param, e.g.
# "Calm, measured, morning-news anchor pace."
TTS_INSTRUCTIONS = os.environ.get("TTS_INSTRUCTIONS", "")

WORDS_PER_MINUTE = 155
