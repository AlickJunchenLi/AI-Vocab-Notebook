import { contextBridge, ipcRenderer } from "electron";

contextBridge.exposeInMainWorld("api", {
  ping: async () => {
    const res = await ipcRenderer.invoke("ping");
    return res;
  },
  backendRequest: async (cmd: "ping" | "add_entry" | "list_entries", payload: any) => {
    const res = await ipcRenderer.invoke("backend:request", cmd, payload);
    return res;
  }
});
