const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("api", {
  ping: async () => ipcRenderer.invoke("ping"),
  backendRequest: async (cmd, payload) => ipcRenderer.invoke("backend:request", cmd, payload)
});

contextBridge.exposeInMainWorld("logs", {
  getPath: async () => ipcRenderer.invoke("logs:getPath"),
  getTail: async () => ipcRenderer.invoke("logs:getTail"),
  openFolder: async () => ipcRenderer.invoke("logs:openFolder")
});
