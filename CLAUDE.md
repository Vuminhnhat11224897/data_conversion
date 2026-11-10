# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

`vbpl_v3` converts the Vietnamese legal-document store (VBPL) from the v2 Elasticsearch indices to v3/v4. It reads 3 v2 indices (read-only), rebuilds Điều/khoản/điểm/phụ lục, chunks and legal metadata with a rule-based parser (LLM only answers uncertain cases, by line number), detects inter-document relations with a 4-layer pipeline, and writes 3 target indices (`legal-docs-*`, `legal-chunk-section-*`, `legal-changed-*`). `-v4` is for trial writes; after approval, `-v3` is rewritten. It is standalone and must never touch the realtime pipeline.

All docs and most comments are in Vietnamese. `README.md` is the authoritative overview (run commands, current status); `docs/` has the detailed architecture, data contracts (v2/v3/v4), enum tables and evaluation. Start with `docs/README.md`, `docs/01-kien-truc.md`, `docs/02-luong-hoat-dong.md`.

## Commands

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env && chmod 600 .env                 # then fill in
.venv/bin/python -m unittest discover -s tests -t .    # all tests (no external services)
.venv/bin/python -m unittest tests.test_parser -v      # one test module
.venv/bin/python -m unittest tests.test_parser.<Class>.<test>   # one test
.venv/bin/python -m unittest bot.test_bot -v           # Telegram bot tests
.venv/bin/python -m vbpl_v3 check                      # verify ES / LLM / embedding connectivity
.venv/bin/python -m vbpl_v3 convert --run thu --sample 20 --dry-run
```

CLI subcommands (`vbpl_v3/__main__.py`): `check`, `init`, `convert`, `auto`, `relink`, `integrity`, `report`, `analyze`; global `--env <file>`.

- Trial writes to v4: set `TARGET_DOCUMENT_INDEX=legal-docs-v4 TARGET_CHUNK_INDEX=legal-chunk-section-v4 TARGET_CHANGE_INDEX=legal-changed-v4`, run `init`, then `convert --run <name> [--ids file] [--limit N] [--workers N]`. Full procedure and `EMBEDDING_REUSE` modes (`no`/`yes`/`target`) are in README "Ghi thử vào v4" and `docs/02`.
- Don't use `--redo`; to retry failures rename `failures.jsonl` to `failures-1.jsonl` first.
- `integrity --out work/ghi-do.txt` finds half-written docs; re-run them with `convert --ids`. `relink --out ...` (read-only) then `relink --write` reconnects target documents; no model calls.
- `auto` is the continuous v2→v4 converter (runs in Docker, one instance only, lock `work/auto/lock`). Stop it before running `convert` manually. `bot/` is a separate Telegram reporter that only reads `work/`.
- Large runs go after 22:00: the LLM server allows 3 concurrent calls by day, 10+ at night (`LLM_CONCURRENCY_DAY/NIGHT`). Run one batch at a time; all ES/embedding traffic goes through a slow VPN.
- Docker image contains only `vbpl_v3/` and `requirements.txt` (allow-list in `.dockerignore`); `eval/`, `bot/`, `work/` are not in it.

## Architecture (big picture)

Per-document flow orchestrated by `convert.py`, with two branches merged at the end:

1. **Structure** – `structure.py` (rule parser: header, căn cứ, Điều, khoản, điểm, appendix, chunk building) with `structure_ai.py` asking the LLM only for ambiguous cases and validating the reply before applying.
2. **Relations, LLM branch (4 layers)** – `extract.py` (L2: LLM extracts actions from units containing action verbs) → `resolver.py` (L3: map target docs/positions to contract format, never guess) → `governance.py` + `validate.py` (L4: verify quotes, verbs, scope; drop or hold for review). Prompts in `vbpl_v3/prompts/*.txt`.
3. **Relations, rule branch** – `relations.py`, `references.py`, `qa.py`; results merged with the LLM branch in `convert.py` (position normalisation, `distinct_edges` de-dup).
4. **Metadata** – `legal_status.py`, `temporal.py`, `metadata_fill.py`.
5. **Write** – `es.py` is the safety layer: blocks any write to source indices, only allows the 3 target indices, retries bulk, reads back (`verify_written`). Write order is chunk → relations → document so a document record implies complete data; `integrity.py` detects partial writes; `source_guard.py` checks source canaries before each run.

Cross-cutting: `llm.py` (OpenAI-style API, JSON validation, response cache, concurrency gate by time of day, `LLM_REPLAY=strict` replay from cache), `embedding.py`, `config.py` (env validation), `mappings/*.json` (ES settings/mappings shared by v3 and v4). Run state/logs/caches live in `work/<run>/` (git-ignored; contains full text sent to the model—sensitive).

`eval/` is the batch evaluation tooling (sampling, grading, strict replays); see `eval/README.md`. It is not part of the pipeline.

## Conventions

- Behavior fixes are tracked by labelled issue codes (E6, E9, E10…, group "nhóm A") in commit messages and `docs/07`; commit messages are in Vietnamese. When changing parser/relation rules, update the relevant `docs/` page (contracts in `docs/09`, rules in `docs/12`).
- Never commit `.env`, `work/`, `bernmark/`, `frontend/data/`, `work/.embedding.env` (contain secrets or full text from ES). Only `.env.example` is tracked.
- Local branch is `master`; push with `git push origin master:main`.
