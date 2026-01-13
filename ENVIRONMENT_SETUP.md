# Environment Configuration (Windows 10/11)

This project uses Electron + React (Node.js) and a Python backend (JSONL stdin/stdout with SQLite). Follow these steps to set up a working dev environment.

## Prerequisites
1) Install Node.js (LTS recommended, e.g., 18.x or 20.x). Ensure `node` and `npm` are on PATH:
   - Check: `node -v` and `npm -v`
2) Install Python 3.11+ and put `python` on PATH:
   - Check: `python --version`
3) Git (optional, for version control).

## Project Dependencies
- Node deps: managed via `npm install` in the `app/` folder.
- Python deps: backend currently uses only the standard library (no extra pip packages).

## Initial Setup
```powershell
cd app
npm install
```

## Dev Run
```powershell
cd app
npm run dev
```
- Vite dev server starts on port 5173.
- Electron window opens; the backend Python server is spawned automatically.
- Data persists in `userData/notebook.db` (Electron userData path).

### Running backend alone (CLI)
- From repo root: `python app/backend/src/server.py "%USERPROFILE%\\.ai-vocab-notebook\\notebook.db"`
- From inside `app/`: `python backend/src/server.py "%USERPROFILE%\\.ai-vocab-notebook\\notebook.db"`
  (Do **not** use `app/app/...`; there is only one `app` directory.)

## Troubleshooting
- If `npm` not found: add Node install directory to PATH or reopen the terminal.
- If `python` not found: ensure Python install path is on PATH; verify with `python --version`.
- Backend spawn issues: check console logs from Electron main; backend errors are printed there.

## Next Steps
- For production builds, we will package the Python backend via PyInstaller and the desktop app via electron-builder (NSIS). This setup doc covers dev only.
