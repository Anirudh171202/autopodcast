"""Prompt templates for the two Claude calls: research (curate) and script (write).

Kept as plain functions returning strings/dicts rather than a templating
engine — there are only two prompts and they change rarely; editing a
function body is simpler than learning a template syntax.
"""

import json

RESEARCH_SCHEMA = {
    "type": "object",
    "properties": {
        "date": {"type": "string"},
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "headline": {"type": "string"},
                    "topic": {"type": "string"},
                    "bullets": {
                        "type": "array",
                        "items": {"type": "string"},
                        "minItems": 2,
                        "maxItems": 5,
                    },
                    "source": {"type": "string"},
                    "source_date": {"type": "string"},
                    "novelty": {
                        "type": "string",
                        "description": "One sentence: what's new here vs. what was already known.",
                    },
                    "importance": {
                        "type": "integer",
                        "description": "1 (minor) to 5 (major) — used to order the episode.",
                    },
                },
                "required": [
                    "headline",
                    "topic",
                    "bullets",
                    "source",
                    "source_date",
                    "novelty",
                    "importance",
                ],
                "additionalProperties": False,
            },
        },
        "deep_dive_headline": {
            "type": ["string", "null"],
            "description": "Headline (must match one in items) of the single most "
            "consequential story worth a 2-3 minute deep dive. Null if nothing warrants it.",
        },
        "insufficient_material": {
            "type": "boolean",
            "description": "True if fewer than six genuinely new, substantive items were found.",
        },
        "editor_note": {
            "type": ["string", "null"],
            "description": "Honest note about material thinness or anything the host should know. Null if not needed.",
        },
    },
    "required": ["date", "items", "deep_dive_headline", "insufficient_material", "editor_note"],
    "additionalProperties": False,
}

RESEARCH_SYSTEM = """You are the research editor for a short daily news podcast that a \
listener plays during their morning commute.

Your job is to find what is genuinely NEW in roughly the last 24-48 hours on the \
listener's topics — not to re-summarize what a well-informed follower of these topics \
already knows. Use web search. Prefer primary sources (official blogs, filings, papers, \
press releases) and reputable original reporting over aggregator rewrites of the same story.

Every item must clear this bar: a person who already follows these topics closely would \
learn something from it. If you cannot find at least six such items across all topics \
combined, say so plainly in editor_note and return fewer items — never pad with rehashed, \
speculative, or evergreen content just to hit a quota. A short honest episode beats a \
padded one."""


def build_research_user_prompt(
    topics: list[str], instructions: str, recent_headlines: list[str], today_str: str
) -> str:
    topics_block = "\n".join(f"- {t}" for t in topics)
    covered_block = (
        "\n".join(f"- {h}" for h in recent_headlines)
        if recent_headlines
        else "(none yet — this is the first episode)"
    )
    return f"""Today's date: {today_str}

Topics to cover:
{topics_block}

Standing instructions from the listener:
{instructions.strip() or "(none)"}

Headlines already covered in recent episodes — do not repeat these unless there is a \
genuine, material update since then:
{covered_block}

Search the web and produce today's rundown as JSON matching the required schema."""


SCRIPT_SYSTEM = """You write the script for a daily solo-narrated news podcast, read \
aloud by one host (not a two-host dialogue). Follow every rule below.

- Write for the ear: no bullet points, no parentheticals, no markdown, no headers. \
Spell out numbers the way they're spoken ("one point four billion", "September third").
- Every factual claim carries its source as spoken attribution woven into the sentence \
("According to Reuters...", "per the company's blog post Tuesday...").
- Never use filler transitions or commentary: no "let's dive in", no "that's fascinating", \
no rhetorical questions aimed at the listener, no recapping what was just said.
- Structure: a cold open (roughly 20 seconds) that names today's date and previews the \
rundown in one or two sentences; then the items in the order given, most important first; \
then a deep-dive segment of about two to three minutes on the single most consequential \
item, going beyond the headline into context and implications; then a brief sign-off.
- If the rundown has fewer items than usual, do not pad to hit the target length — a \
shorter, honest episode is better than a padded one. If editor_note flags thin material, \
you may briefly and plainly acknowledge a quiet news day in the cold open.

Output ONLY the script text to be read aloud, as plain prose paragraphs separated by \
blank lines. No stage directions, no speaker labels, no section headers."""


def build_script_user_prompt(rundown: dict, target_words: int) -> str:
    return f"""Target length: approximately {target_words} words (~{target_words // 155} \
minutes at conversational pace). Scale down honestly if the rundown below doesn't support \
that length — do not pad.

Today's rundown (JSON):
{json.dumps(rundown, indent=2)}

Write the full episode script now."""
