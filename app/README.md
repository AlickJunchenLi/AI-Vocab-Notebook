# AI Vocab Notebook (Electron + React + Python backend)

## Dev quick start
```
cd app
npm install
npm run dev
```
- Vite dev server on http://localhost:5173
- Electron window auto opens; "Ping main" returns pong
- Data stored at `app.getPath("userData")/notebook.db`

## Build / Package (Windows)
- Build renderer: `npm run build:renderer`
- Build Python backend exe (PyInstaller onedir): `npm run build:backend`
- Build NSIS installer: `npm run dist:win`
  - electron-builder config uses extraResources to place backend exe under `resources/backend/gw_backend.exe`
  - In production, main.js spawns that exe; dev uses `python backend/src/server.py`
  - All writable data (db, caches, ann index, HF cache) lives in `userData`

## Reinstall / Repair
- Just rerun the Windows installer; it detects an existing install and will reinstall/repair in place. App files are overwritten; notebook data in `app.getPath("userData")` stays untouched.
- For a force repair on a broken/partial install, run the setup from PowerShell/CMD with the flag: `.\AI Vocab Notebook Setup.exe /reinstall` (adjust the file name to your built installer). This forces overwrite of app files even if the same version is already present.
- The bundled Node.js installer is optional; if Node is already on the machine you can skip it, or accept it during reinstall to standardize the runtime.

## Scripts
- `dev`: run renderer + electron
- `build:backend`: PyInstaller on `backend/src/server.py` -> `backend/dist/gw_backend/`
- `dist:win`: renderer build + backend build + electron-builder nsis

## Directory layout
- `electron/` main + preload
- `renderer/` React UI
- `backend/src` Python server, DB, search, semantic, ann
- `backend/dist/gw_backend/` PyInstaller output (added via extraResources)

## Notes
- IPC: JSONL over stdin/stdout between Electron main and backend exe
- Production backend path: `path.join(process.resourcesPath, 'backend', 'gw_backend.exe')`
- Dev backend path: `python backend/src/server.py`
