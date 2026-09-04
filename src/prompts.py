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
                        "description": "3 to 5 short factual bullets covering this item.",
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
            "description": "True if there isn't enough genuinely new, substantive material "
            "today to justify a real episode — not a specific item count, since a single "
            "story covered in real depth is a fine episode on its own.",
        },
        "editor_note": {
            "type": ["string", "null"],
            "description": "Honest note about material thinness or anything the host should know. Null if not needed.",
        },
        "weather": {
            "type": "string",
            "description": "One brief sentence on today's Bay Area weather (via web search). "
            "Always populate this regardless of how much news material exists — it is a "
            "standing utility feature, not subject to the newsworthiness bar applied to items.",
        },
    },
    "required": [
        "date",
        "items",
        "deep_dive_headline",
        "insufficient_material",
        "editor_note",
        "weather",
    ],
    "additionalProperties": False,
}

RESEARCH_SYSTEM = """You are the research editor for a short daily news podcast that a \
listener plays during their morning commute.

Your job is to find what is genuinely NEW in the last 24 hours on the listener's topics — \
not to re-summarize what a well-informed follower of these topics already knows, and not \
to report an older development just because someone wrote about it again today. Use web \
search and check the actual date of the underlying event, not just the date of the article. \
Prefer primary sources (official blogs, filings, papers, press releases) and reputable \
original reporting over aggregator rewrites of the same story. If a topic names a specific \
source or community (e.g. "Hacker News"), search that source directly rather than relying \
on generic web results about it.

Every item must clear this bar: a person who already follows these topics closely would \
learn something concrete from it — a specific event, release, launch, paper, or incident. \
An opinion piece or trend roundup that just restates a narrative already in circulation \
does not qualify, even if it was published today.

There is no target item count. This listener would rather hear two or three genuinely \
interesting stories covered in real depth than a wider list covered thinly — depth beats \
breadth. If a topic has nothing that clears the bar today, leave it out entirely rather \
than including something weak to round out the list; if that leaves very little or nothing \
across all topics, say so plainly in editor_note rather than padding with rehashed, \
speculative, or evergreen content. A short honest episode beats a padded one.

Topics are listed in priority order. When there is more good material than fits in the \
target runtime, prefer items from higher-priority topics — but don't drop a lower-priority \
topic entirely just because a higher one is busy, if it genuinely has new material.

Separately, always populate the `weather` field with one brief sentence on today's Bay \
Area weather (search the web for it). This applies even on a day with zero qualifying \
news items — weather is a standing utility feature the listener wants every day, not \
something gated by newsworthiness."""


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

Topics to cover, in priority order (most important first):
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
- When moving from a somber or heavy story (conflict, disaster, casualties) into a lighter \
one (sports, weather), use a short, plain transition that signals the shift — a bare topic \
label like "In sports:" is enough. Never juxtapose them with no signal at all, and never \
editorialize about the tonal shift itself.
- Structure: a cold open (roughly 20 seconds) that names today's date and previews the \
rundown in one or two sentences; then the items in the order given, most important first, \
each given real space to explain why it matters or how it works — not just what was \
announced, since there are usually few enough items that none should get bare headline \
treatment; then a deep-dive segment of about two to three minutes on the single most \
consequential item, going even further into context and implications; then the weather \
line; then a brief sign-off.
- If the rundown has fewer items than usual, do not pad to hit the target length — a \
shorter, honest episode is better than a padded one. If editor_note flags thin material, \
you may briefly and plainly acknowledge a quiet news day in the cold open.
- If items is empty, this is a quiet day by design, not an error: skip the normal \
structure entirely and write a short cold open naming the date, one plain sentence \
acknowledging nothing cleared the bar today (drawing on editor_note if present, without \
reading it verbatim), the weather line, and a sign-off. A few sentences total is correct \
— do not stretch this to the target length.

Output ONLY the script text to be read aloud, as plain prose paragraphs separated by \
blank lines. No stage directions, no speaker labels, no section headers."""


def build_script_user_prompt(rundown: dict, target_words: int) -> str:
    return f"""Target length: approximately {target_words} words (~{target_words // 155} \
minutes at conversational pace). Scale down honestly if the rundown below doesn't support \
that length — do not pad.

Today's rundown (JSON):
{json.dumps(rundown, indent=2)}

Write the full episode script now."""
