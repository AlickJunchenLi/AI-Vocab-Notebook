import path from "path";
import { app, BrowserWindow, ipcMain } from "electron";
import { spawn, ChildProcess } from "child_process";
import readline from "readline";

const isDev = !!process.env.VITE_DEV_SERVER_URL;
let backendProc: ChildProcess | null = null;
const pending = new Map<string, (value: unknown) => void>();
let reqCounter = 0;

function startBackend(dbPath: string) {
  const scriptPath = isDev
    ? path.join(__dirname, "..", "backend", "src", "server.py")
    : path.join(process.resourcesPath, "backend", "server.py"); // placeholder for prod; later swap to bundled exe

  backendProc = spawn("python", [scriptPath, dbPath], {
    stdio: ["pipe", "pipe", "pipe"]
  });

  if (backendProc.stdout) {
    const rl = readline.createInterface({ input: backendProc.stdout });
    rl.on("line", (line) => {
      try {
        const msg = JSON.parse(line);
        const id = msg.id;
        if (id && pending.has(id)) {
          pending.get(id)?.(msg);
          pending.delete(id);
        }
      } catch (err) {
        console.error("Failed to parse backend line", err);
      }
    });
  }

  backendProc.on("exit", (code) => {
    console.warn("Backend exited", code);
  });
}

function backendRequest(cmd: string, payload: any): Promise<any> {
  if (!backendProc || !backendProc.stdin || !backendProc.stdin.writable) {
    return Promise.reject(new Error("backend not running"));
  }
  const id = `req_${Date.now()}_${reqCounter++}`;
  return new Promise((resolve, reject) => {
    pending.set(id, resolve);
    const msg = JSON.stringify({ id, cmd, payload, v: 1 });
    backendProc!.stdin!.write(msg + "\n", (err) => {
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

ipcMain.handle("backend:request", async (_event, cmd: string, payload: any) => {
  return backendRequest(cmd, payload);
});
