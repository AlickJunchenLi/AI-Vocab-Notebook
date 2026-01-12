// Launch Electron with a clean environment (ELECTRON_RUN_AS_NODE must be removed)
const { spawn } = require("child_process");

const env = { ...process.env };
delete env.ELECTRON_RUN_AS_NODE;

if (!env.VITE_DEV_SERVER_URL) {
  env.VITE_DEV_SERVER_URL = "http://localhost:5173";
}

const electronPath = require("electron");

const child = spawn(electronPath, ["."], {
  stdio: "inherit",
  env
});

child.on("exit", (code) => {
  process.exit(code ?? 0);
});
