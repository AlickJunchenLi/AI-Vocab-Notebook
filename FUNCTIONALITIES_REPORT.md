# Project Functionalities Report

This document answers "how many functionalities are there in this project?" and notes the source files used for each part. The current code implements 7 functional areas.

1. **Vocabulary entry CRUD & notes** - add, list, edit, and soft-delete bilingual entries with optional notes and translations.
   - Files used: `app/renderer/src/App.tsx`, `app/backend/src/server.py`, `app/backend/src/db.py`.
2. **Relation management & auto-linking** - create synonym/translation links and auto-link new or updated entries through overlap, fuzzy, and resolver passes.
   - Files used: `app/backend/src/server.py`, `app/backend/src/db.py`, `app/backend/src/matching/resolve.py`, `app/renderer/src/App.tsx`.
3. **Search & candidate resolution** - query entries via LIKE, FTS, fuzzy, and semantic/ANN modes; resolve tokens to best entry candidates.
   - Files use2d: `app/backend/src/search.py`, `app/backend/src/server.py`, `app/backend/src/matching/resolve.py`, `app/renderer/src/App.tsx`.
4. **Record ingestion & annotation linking** - save free-form text records, extract tokens, and link or unlink spans to vocabulary entries with candidate review.
   - Files used: `app/backend/src/db.py`, `app/backend/src/server.py`, `app/backend/src/matching/tokens.py`, `app/renderer/src/App.tsx`.
5. **Synonym graph exploration & suggestions** - traverse related words via relation graph and surface fallback AI candidates that can be promoted to synonyms.
   - Files used: `app/backend/src/retrieval/graph_first.py`, `app/backend/src/server.py`, `app/backend/src/search.py`, `app/backend/src/matching/resolve.py`, `app/renderer/src/App.tsx`.
6. **Semantic embeddings & ANN management** - build embeddings, run semantic/ANN searches, track pending updates, and rebuild indices.
   - Files used: `app/backend/src/semantic/__init__.py`, `app/backend/src/ann/index_manager.py`, `app/backend/src/db.py`, `app/backend/src/server.py`.
7. **Desktop shell, backend orchestration & logging** - Electron shell spawns the Python backend, sanitizes IPC, and exposes backend requests plus log tails to the renderer.
   - Files used: `app/electron/main.js`, `app/electron/preload.js`, `app/renderer/src/App.tsx`.

## New UML

See `functional_overview.uml` for an updated PlantUML view of the functional components and their interactions.