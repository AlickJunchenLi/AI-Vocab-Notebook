# AI Vocab Notebook — 0→1 Rebuild & Usage Guide

Audience: developers who need to recreate, run, and explain the project so others can follow exactly.

## 1) What the project is
- Desktop bilingual vocab notebook (Electron + React front-end) with a Python + SQLite backend.
- Features: CRUD words, synonym/translation relations, record annotations, multi-mode search (LIKE/FTS/fuzzy), optional semantic + ANN search, log viewing.

## 2) Prerequisites (Windows, macOS, Linux)
- Node.js 18/20 LTS + npm (`node -v`, `npm -v`).
- Python 3.11+ on PATH (`python --version`).
- Git; SQLite CLI optional; Java 17 + Graphviz only if you want to render UML files.
- Optional for semantic/ANN: `pip install sentence-transformers faiss-cpu numpy`.

## 3) Repository layout (important paths)
- `app/electron/main.js` — starts backend process, IPC bridge, logs.
- `app/electron/preload.js` — exposes `window.api` and `window.logs` to renderer.
- `app/renderer/src/App.tsx` — UI flows (entries, search, relations, records, synonyms, logs).
- `app/backend/src/server.py` — JSONL stdin/stdout server; command handlers.
- `app/backend/src/db.py` — SQLite schema/migrations and CRUD.
- `app/backend/src/search.py`, `matching/`, `retrieval/`, `semantic/`, `ann/` — search, tokenization, synonym graph, embeddings, ANN.
- Docs: `ENVIRONMENT_SETUP.md`, `IMPLEMENTATION_WORKFLOW.md`, `FUNCTIONALITIES_REPORT.md`, `PROJECT_DESIGN.md`.

## 4) One-command dev start
```bash
cd app
npm install
npm run dev
```
- Opens Electron window; Vite dev server on http://localhost:5173.
- Backend `server.py` is spawned automatically with DB at Electron userData path (e.g., `%APPDATA%/AI Vocab Notebook/notebook.db` on Windows, `~/Library/Application Support/AI Vocab Notebook/notebook.db` on macOS/Linux).

## 5) End-to-end build plan (follow in order)
1) **Backend skeleton & DB**
   - Ensure `db.py` migrations run; start backend alone to verify:
     ```bash
     python app/backend/src/server.py notebook.db
     # then send: {"cmd":"ping","id":1,"payload":{}}
     ```
2) **Search modes**
   - Implement/verify `search_like`, `search_fts`, `search_fuzzy` in `app/backend/src/search.py`; FTS5 triggers are set in migrations.
3) **Matching & auto-link**
   - Tokenize mixed zh/en (`matching/tokens.py`), resolve candidates (`matching/resolve.py`), keep `_auto_link_entry` in `server.py` wiring new relations.
4) **Synonym graph traversal**
   - BFS in `retrieval/graph_first.py`; exposed via `get_synonyms` handler.
5) **Records & annotations**
   - CRUD `records` + `record_links` tables; auto-extract tokens on add/update; manual relink via `link_record`/`unlink_record`.
6) **Semantic embeddings & ANN (optional)**
   - Install deps, run:
     ```bash
     python app/backend/src/server.py notebook.db  # in another shell, send JSONL
     # once running through Electron or CLI, call:
     # rebuild embeddings
     {"cmd":"rebuild_embeddings","id":2,"payload":{}}
     # build ANN index
     {"cmd":"rebuild_ann_index","id":3,"payload":{}}
     ```
7) **Electron shell & React UI**
   - `electron/main.js` spawns backend; `preload.js` exposes IPC; `renderer/src/App.tsx` drives UI flows.
8) **Packaging (Windows)**
   - From `app/`: `npm run dist:win` (runs renderer build, PyInstaller backend, then electron-builder NSIS). Backend exe copied to `resources/backend/gw_backend.exe`.

## 6) Using the app (happy path)
- **Add entry**: choose language, fill word/translation/notes → backend auto-links synonyms/translations.
- **Search**: type query; choose mode (FTS/Like/Fuzzy/Semantic). Semantic needs embeddings/ANN built.
- **Detail view**: edit fields; soft-delete; view relations list.
- **Records**: paste bilingual text → tokens auto-highlighted; click a highlight to see candidates; choose “Link” to bind to an entry or “Unlink”.
- **Synonyms**: press “Find synonyms” to traverse graph + AI fallback; “Add as synonym” creates relation.
- **Logs**: Diagnostics shows log path, ring buffer, file tail; “Open log folder” opens location.

## 7) Running backend without Electron (debug)
```bash
python app/backend/src/server.py "%USERPROFILE%\.ai-vocab-notebook\notebook.db"  # Windows example
# macOS/Linux: python app/backend/src/server.py "~/Library/Application Support/AI Vocab Notebook/notebook.db"
# send lines like:
{"id":1,"cmd":"ping","payload":{}}
```

## 8) Troubleshooting quick hits
- `npm` not found → add Node to PATH or reopen terminal.
- Backend not spawning → check Electron devtools console and log file shown in Diagnostics panel.
- `SEMANTIC_DISABLED` errors → install optional deps, rebuild embeddings, then rebuild ANN.
- Port 5173 taken → set env `VITE_DEV_SERVER_URL=http://localhost:<free_port>` before `npm run dev`.
- Unicode issues → backend sanitizes inputs (`_safe_text`), but ensure files are UTF-8.

## 9) Talking points when explaining to others
- Two layers: Electron/React UI + Python/SQLite backend; JSONL IPC over stdio.
- Data model: `entries` + `relations` + `records` + `record_links` + `entry_embeddings` (+ ANN queue).
- Search stack: LIKE, FTS5, difflib fuzzy; optional semantic/ANN via sentence-transformers + FAISS.
- Auto-linking: new/updated entries are linked via translation overlap, fuzzy matches, and resolver candidates.
- Extensibility: semantic model name is configurable; ANN rebuilt from embeddings; legacy thesaurus files can be imported via planned C++ adapter.

