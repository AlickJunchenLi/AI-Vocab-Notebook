# AI Vocab Notebook - Implementation Workflow

This workflow shows the end-to-end steps to rebuild the project, aligned with the 7 functional areas in `FUNCTIONALITIES_REPORT.md`. Follow the phases in order; each phase lists goals, key files, and checkpoints.

## 0) Prereqs
- Install: Node.js LTS, Python 3.11+, Git, SQLite CLI, Java 17 + Graphviz (for PlantUML), pnpm/npm.
- Verify commands: `node -v`, `npm -v`, `python --version`, `sqlite3 --version`, `java -version`, `dot -V`.
- Create/activate Python venv under `app/.venv` and Node deps under `app/`.

## 1) Backend skeleton & data model
- Goal: Stable IPC surface and DB schema for entries/relations/records.
- Implement `app/backend/src/db.py`: migrations (entries, relations, records, embeddings, ann_queue), CRUD functions, record links, ANN queue helpers.
- Implement `app/backend/src/server.py`: JSONL stdin/stdout loop, handler map, error handling, wiring to db functions.
- Checkpoint: CLI call `python app/backend/src/server.py notebook.db` responds to `{cmd:"ping"}` with pong; `add_entry/list_entries` works.

## 2) Search modes
- Goal: Full-text, LIKE, and fuzzy search.
- Implement `app/backend/src/search.py` with `_to_row_dict`, `search_like`, `search_fts`, `search_fuzzy` (SequenceMatcher), triggers/FTS rebuild in db migration.
- Checkpoint: `search_entries` handler returns results for `mode=like|fts|fuzzy`.

## 3) Matching & candidate resolution
- Goal: Tokenize mixed zh/en text and resolve tokens to entry candidates.
- Implement `app/backend/src/matching/tokens.py` for token extraction.
- Implement `app/backend/src/matching/resolve.py` plus `exact.py`/`fuzzy.py` to combine exact, fuzzy, LIKE, semantic/ANN fallbacks.
- Wire `_auto_link_entry` in `server.py` to use resolver for auto-relations.
- Checkpoint: `resolve_entry` returns best + candidates; new entries auto-link when added.

## 4) Synonym graph traversal
- Goal: Explore related words via relations graph.
- Implement `app/backend/src/retrieval/graph_first.py` BFS over relations with depth and type filters.
- Wire `get_synonyms` in `server.py` to combine graph results and fallback candidates.
- Checkpoint: `get_synonyms` returns graph_results and fallback_results for an entry or a token.

## 5) Records & annotations
- Goal: Store free-form text and link spans to entries.
- In `db.py`, ensure `records` and `record_links` tables plus CRUD/helpers.
- In `server.py`, implement `add_record`, `update_record`, `get_record`, `list_records`, `link_record`, `unlink_record`; reuse `replace_record_links` and `fetch_record_links`.
- Use `matching/tokens.py` to auto-extract tokens and seed annotations when adding/updating records.
- Checkpoint: Adding a record yields annotations; linking/unlinking updates persisted links.

## 6) Semantic embeddings & ANN
- Goal: Optional semantic search and ANN acceleration.
- Implement `app/backend/src/semantic/__init__.py`: model loading, embeddings storage, semantic search, status, rebuild.
- Implement `app/backend/src/ann/index_manager.py`: load embeddings, build/search FAISS index, apply ANN queue.
- Wire handlers in `server.py`: `semantic_status`, `rebuild_embeddings`, `ann_status`, `rebuild_ann_index`, `ann_apply_updates`; enqueue ANN ops on entry upsert/delete.
- Checkpoint: `semantic_status` enabled when deps present; `ann_status` shows index meta; `ann_apply_updates` rebuilds index after changes.

## 7) Electron shell & IPC
- Goal: Desktop host that spawns backend and bridges IPC.
- Implement `app/electron/main.js` (or `main.ts`): backend spawn (dev: python server.py; prod: packaged exe), JSONL IPC bridge, logging, log tail exposure.
- Implement `app/electron/preload.js` (or `preload.ts`): expose `window.api.backendRequest` and log helpers to renderer.
- Checkpoint: `npm run dev` opens Electron window and `Ping main` returns pong; backend stdout lines reach renderer.

## 8) Renderer (React)
- Goal: Single-page UI for CRUD, search, relations, records, synonyms, diagnostics.
- Implement `app/renderer/src/App.tsx`: state for entries/relations/records/logs, handlers calling backend commands, list/detail views, search mode switcher, synonym finder, annotation linker UI, logs pane.
- Styling: `app/renderer/src/style.css` as needed; Vite entry `app/renderer/src/main.tsx`.
- Checkpoint: UI can add/update/delete entries, search in all modes, view relations, manage records/annotations, find synonyms, view logs.

## 9) Packaging & scripts
- Goal: Reproducible dev/build.
- Scripts in `app/package.json`: `dev`, `build:renderer`, `build:backend` (PyInstaller), `dist:win` (electron-builder/NSIS).
- Ensure `electron-builder` config (extraResources) copies backend exe to `resources/backend/gw_backend.exe`; dev uses python directly.
- Checkpoint: `npm run dev` works; `npm run dist:win` produces installer; backend exe runs from `process.resourcesPath`.

## 10) QA & docs
- Smoke test commands via `backendRequest` for each handler; add basic unit tests for `db.py` and resolver if desired.
- Update docs: `FUNCTIONALITIES_REPORT.md`, `functional_overview.uml/png`, `ENVIRONMENT_SETUP.md` with any new prerequisites or commands.

## Suggested implementation order (condensed)
1) Backend: db.py + server.py (IPC + CRUD + relations + records tables).
2) Search + matching + resolver + auto-link.
3) Synonym graph + records/annotations.
4) Semantic/ANN optional path.
5) Electron main/preload wiring.
6) Renderer UI flows.
7) Packaging scripts + docs refresh.