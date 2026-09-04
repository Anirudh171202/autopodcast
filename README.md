# autopodcast

Every night: research what's actually new on your topics, write a script for
it, narrate it, and publish it as a private podcast feed — so it's sitting in
your podcast app ready to play on tomorrow's commute. No manual step once
it's set up.

## How it works

```
config/topics.yaml ──┐
                      ▼
              ┌───────────────┐
 state/       │ 1. research   │  Claude + web search → structured JSON
 history.json │    (curate)   │  of today's genuinely-new items
              └───────┬───────┘
                      ▼
              ┌───────────────┐
              │ 2. script     │  Claude → prose script written to be
              │    (write)    │  read aloud, not summarized
              └───────┬───────┘
                      ▼
              ┌───────────────┐
              │ 3. narrate    │  OpenAI TTS → docs/episodes/<date>.mp3
              └───────┬───────┘
                      ▼
              ┌───────────────┐
              │ 4. publish    │  regenerate docs/feed.xml, prune old
              │    (feed)     │  episodes, update state/
              └───────────────┘
```

Two separate LLM calls, deliberately — one model is bad at both researching
*and* writing well in a single pass. The research step is instructed to
report honestly when there isn't much news rather than pad; the script step
scales its target length down instead of inventing filler.

`state/history.json` remembers headlines from recent episodes so the show
doesn't repeat itself. `state/episodes_index.json` is the source of truth for
what's live; `docs/feed.xml` is fully regenerated from it every run.

## One-time setup

### 1. Install and configure locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env and paste in ANTHROPIC_API_KEY and OPENAI_API_KEY
```

Edit `config/topics.yaml` — your topics, any standing instructions, target
length. `feed_base_url` doesn't matter for local runs, only once you publish.

### 2. Test a run locally

```bash
python -m src.pipeline
```

This writes `docs/episodes/<today>.mp3`, `docs/feed.xml`, and updates
`state/`. Listen to the mp3 directly and read `state/scripts/<today>.txt`
before wiring up the nightly schedule — this is the point to tune the
prompts in `src/prompts.py` if the voice/tone isn't right, or the TTS voice
in `.env` (`TTS_VOICE`) if it doesn't sound like you want.

### 3. Push to GitHub and enable Pages

```bash
gh repo create autopodcast --private --source=. --remote=origin
git add -A && git commit -m "Initial commit"
git push -u origin main
```

Then in the repo's GitHub settings:

- **Settings → Secrets and variables → Actions**: add `ANTHROPIC_API_KEY`
  and `OPENAI_API_KEY` as repository secrets.
- **Settings → Pages**: source = "Deploy from a branch", branch = `main`,
  folder = `/docs`. GitHub will give you a URL like
  `https://yourusername.github.io/autopodcast`.
- Update `feed_base_url` in `config/topics.yaml` to that exact URL, commit,
  and push.

A private repo keeps the code and your topics list private; GitHub still
serves the Pages site itself at a public (but unguessable) URL — that's what
makes the feed URL work in a podcast app. If you'd rather the repo be public
(free either way, no functional difference for this use case since nothing
sensitive lives in it), that's fine too.

### 4. Test the scheduled workflow once by hand

In the repo's **Actions** tab, run "Nightly Podcast" via the manual
"Run workflow" button (that's what `workflow_dispatch` in the workflow file
is for) rather than waiting for the 7am UTC cron. Confirm it commits a new
episode and the feed updates.

### 5. Subscribe

In Overcast, Pocket Casts, or Apple Podcasts, use "Add by URL" with your
`feed_base_url` + `/feed.xml`. Turn on auto-download. It'll pick up new
episodes overnight and have them ready before you leave.

## Costs

Rough estimate for a 10-minute episode, every night, for a month (see the
model/voice defaults in `src/config.py`):

| Step | Default | Est. cost/night | Est. cost/month |
|---|---|---|---|
| Research (web search + curation) | Claude Haiku 4.5 | ~$0.03 | ~$1 |
| Script writing | Claude Sonnet 5 | ~$0.03 | ~$1 |
| Web search tool usage fee | a few queries/night | ~$0.02 | ~$0.60 |
| Narration | OpenAI gpt-4o-mini-tts (~$0.015/min) | ~$0.15 | ~$4.50 |
| Hosting (GitHub Pages) | — | $0 | $0 |
| **Total** | | **~$0.23** | **~$7** |

That's comfortably inside a $5–10/month budget with room to spare. The
model choices below are a deliberate cost/quality tradeoff, not a hidden
downgrade — bump either one via env vars (`.env` locally, repo secrets/vars
for Actions) if you want better prose and don't mind paying more:

- `RESEARCH_MODEL` (default `claude-haiku-4-5`) — structured extraction from
  search results doesn't need a bigger model.
- `SCRIPT_MODEL` (default `claude-sonnet-5`) — this is where writing quality
  actually shows up; `claude-opus-5` is a real upgrade here at ~2.5x the
  cost if the difference matters to you.
- `TTS_VOICE` / `TTS_MODEL` — if `gpt-4o-mini-tts` sounds too synthetic,
  ElevenLabs sounds noticeably better but its cheapest tier that covers
  ~300 minutes/month of audio (10 min × 30 nights) costs more than this
  whole pipeline combined — worth it only if voice quality matters more to
  you than the budget.

## Customizing

- **Topics / instructions / length**: `config/topics.yaml` — no code changes,
  picked up on the next run.
- **Tone, structure, style rules**: `src/prompts.py` — `RESEARCH_SYSTEM` and
  `SCRIPT_SYSTEM` are the two system prompts. The most common tweak is
  `SCRIPT_SYSTEM`'s style rules if episodes feel too stiff or too chatty.
- **Retention**: `episode_retention_days` in `topics.yaml` controls how many
  days of episodes stay in the feed and in git history (older mp3s are
  deleted automatically) — keeps the repo from growing indefinitely.
- **Schedule**: the cron line in `.github/workflows/nightly.yml`.

## Troubleshooting

- **Workflow silently stops running**: GitHub disables scheduled workflows
  after 60 days of repo inactivity. The nightly commit to `state/` counts as
  activity, so this should never trigger under normal use — but if you pause
  the schedule for a couple months, re-enable it manually in the Actions tab.
- **A run fails**: GitHub emails the repo owner on workflow failure by
  default — no extra alerting needed. Check the Actions log; the pipeline
  prints progress at each of the four steps.
- **Episode is much shorter than 10 minutes**: check the `editor_note` field
  printed in the Actions log — this is very likely the research step
  correctly declining to pad a slow news day rather than a bug.
