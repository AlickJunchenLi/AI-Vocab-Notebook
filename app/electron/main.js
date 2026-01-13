const path = require("path");
const electron = require("electron");
const log = require("electron-log");
const { TextDecoder } = require("util");
if (!electron) {
  throw new Error("Failed to load electron module");
}
const { app, BrowserWindow, ipcMain, shell } = electron;
const { spawn } = require("child_process");
const fs = require("fs");
const ringBuffer = [];
const MAX_RING = 500;

const isDev = !!process.env.VITE_DEV_SERVER_URL;
let backendProc = null;
const pending = new Map();
let reqCounter = 0;
let logFilePath = "";
const REPLACEMENT_CHAR = String.fromCharCode(0xfffd);

// set logs path
app.setAppLogsPath();
log.transports.file.maxSize = 5 * 1024 * 1024;
log.info("App starting, isDev:", isDev);

function getBackendCommand(dbPath) {
  if (isDev) {
    return {
      cmd: "python",
      args: [path.join(__dirname, "..", "backend", "src", "server.py"), dbPath],
    };
  }
  // production exe packaged via PyInstaller and copied to resources/backend/gw_backend.exe
  const exePath = path.join(process.resourcesPath, "backend", "gw_backend.exe");
  return { cmd: exePath, args: [dbPath] };
}

function startBackend(dbPath) {
  console.log("Starting backend with DB path:", dbPath, "isDev:", isDev);
  const { cmd, args } = getBackendCommand(dbPath);
  const hfCache = path.join(app.getPath("userData"), "hf_cache");
  backendProc = spawn(cmd, args, {
    stdio: ["pipe", "pipe", "pipe"],
    windowsHide: true,
    env: {
      ...process.env,
      PYTHONUTF8: "1",
      PYTHONIOENCODING: "utf-8",
      HF_HOME: hfCache,
      HF_HUB_CACHE: hfCache,
      TRANSFORMERS_CACHE: hfCache,
      SENTENCE_TRANSFORMERS_HOME: hfCache,
    },
  });
  log.info("Spawn backend", cmd, args);

  backendProc.on("error", (err) => {
    log.error("Failed to start backend process", err);
  });

  if (backendProc.stderr) {
    attachDecodedLines(backendProc.stderr, "stderr", (line) => {
      log.error("[backend stderr]", line);
      pushRing("[backend stderr] " + line);
    });
  }

  if (backendProc.stdout) {
    attachDecodedLines(backendProc.stdout, "stdout", (line) => {
      pushRing("[backend stdout] " + line);
      try {
        const msg = JSON.parse(line);
        const id = msg.id;
        if (id && pending.has(id)) {
          pending.get(id)?.(msg);
          pending.delete(id);
        }
      } catch (err) {
        log.error("Failed to parse backend line", err);
      }
    });
  }

  backendProc.on("exit", (code) => {
    log.warn("Backend exited", code);
    pushRing("[backend exit] code=" + code);
  });
}

function pushRing(line) {
  ringBuffer.push(line);
  if (ringBuffer.length > MAX_RING) {
    ringBuffer.shift();
  }
}

function backendRequest(cmd, payload) {
  if (!backendProc || !backendProc.stdin || !backendProc.stdin.writable) {
    return Promise.reject(new Error("backend not running"));
  }
  const id = `req_${Date.now()}_${reqCounter++}`;
  return new Promise((resolve, reject) => {
    pending.set(id, resolve);
    const sanitizedMsg = sanitizeValue({ id, cmd, payload, v: 1 });
    const msg = JSON.stringify(sanitizedMsg);
    const data = Buffer.from(msg + "\n", "utf8");
    backendProc.stdin.write(data, (err) => {
      if (err) {
        pending.delete(id);
        reject(err);
      }
    });
    setTimeout(() => {
      if (pending.has(id)) {
        pending.delete(id);
        reject(new Error("backend timeout"));
      }
    }, 10000);
  });
}

function createWindow() {
  const win = new BrowserWindow({
    width: 1000,
    height: 700,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false
    }
  });

  if (isDev && process.env.VITE_DEV_SERVER_URL) {
    win.loadURL(process.env.VITE_DEV_SERVER_URL);
    win.webContents.openDevTools({ mode: "detach" });
  } else {
    win.loadFile(path.join(__dirname, "..", "renderer", "dist", "index.html"));
  }
}

app.whenReady().then(() => {
  logFilePath = log.transports.file.getFile().path;
  log.info("Log file path:", logFilePath);
  const dbPath = path.join(app.getPath("userData"), "notebook.db");
  startBackend(dbPath);

  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on("window-all-closed", () => {
  if (backendProc) {
    backendProc.kill();
    backendProc = null;
  }
  if (process.platform !== "darwin") {
    app.quit();
  }
});

ipcMain.handle("ping", async () => {
  return "pong";
});

ipcMain.handle("backend:request", async (_event, cmd, payload) => {
  return backendRequest(cmd, payload);
});

ipcMain.handle("logs:getPath", async () => {
  return logFilePath;
});

ipcMain.handle("logs:getTail", async () => {
  // combine ring buffer and file tail
  let fileTail = "";
  try {
    const data = fs.readFileSync(logFilePath, "utf-8");
    fileTail = data.slice(-8000);
  } catch (e) {
    log.warn("read log tail failed", e);
  }
  return {
    path: logFilePath,
    ring: ringBuffer.slice(-MAX_RING),
    fileTail,
  };
});

ipcMain.handle("logs:openFolder", async () => {
  const folder = path.dirname(logFilePath);
  await shell.openPath(folder);
  return true;
});

function sanitizeString(str) {
  let out = "";
  for (let i = 0; i < str.length; i++) {
    const code = str.charCodeAt(i);
    const isHigh = code >= 0xd800 && code <= 0xdbff;
    const isLow = code >= 0xdc00 && code <= 0xdfff;
    if (isHigh) {
      if (i + 1 < str.length) {
        const next = str.charCodeAt(i + 1);
        const nextIsLow = next >= 0xdc00 && next <= 0xdfff;
        if (nextIsLow) {
          out += str[i] + str[i + 1];
          i += 1;
          continue;
        }
      }
      out += REPLACEMENT_CHAR;
    } else if (isLow) {
      out += REPLACEMENT_CHAR;
    } else {
      out += str[i];
    }
  }
  return out;
}

function sanitizeValue(val) {
  if (typeof val === "string") {
    return sanitizeString(val);
  }
  if (Array.isArray(val)) {
    return val.map((v) => sanitizeValue(v));
  }
  if (val && typeof val === "object") {
    const out = {};
    for (const [k, v] of Object.entries(val)) {
      const safeKey = typeof k === "string" ? sanitizeString(k) : k;
      out[safeKey] = sanitizeValue(v);
    }
    return out;
  }
  return val;
}

function attachDecodedLines(stream, label, onLine) {
  // Backend writes UTF-8 (PYTHONUTF8=1), so decode stdout/stderr as UTF-8 to avoid mojibake
  const decoder = new TextDecoder("utf-8", { fatal: false });
  let buffer = "";

  stream.on("data", (chunk) => {
    buffer += decoder.decode(chunk, { stream: true });
    let idx;
    while ((idx = buffer.indexOf("\n")) !== -1) {
      const line = buffer.slice(0, idx).replace(/\r$/, "");
      buffer = buffer.slice(idx + 1);
      onLine(line);
    }
  });

  stream.on("close", () => {
    buffer += decoder.decode();
    if (buffer) {
      onLine(buffer);
    }
  });
}
