import { useEffect, useSyncExternalStore } from "react";
import { InstalledLibrary, libraryInstalled } from "../api";
import { safeAsyncOperation } from "../utils";

// One copy for the Quick Access panel and the plugin's page: a download on the page shows in the panel.
let library: InstalledLibrary | null = null;
let requested = false;
const listeners = new Set<() => void>();

const reload = (): void => {
  requested = true;
  void safeAsyncOperation(libraryInstalled, "useInstalledLibrary -> libraryInstalled").then((answer) => {
    if (!answer) return;
    library = answer;
    listeners.forEach((listener) => listener());
  });
};

const subscribe = (listener: () => void) => {
  listeners.add(listener);
  return () => listeners.delete(listener);
};

/** The versions games can be patched with; `reload` after the library changes. */
export const useInstalledLibrary = (): { library: InstalledLibrary | null; reload: () => void } => {
  const current = useSyncExternalStore(subscribe, () => library);
  useEffect(() => {
    if (!requested) reload();
  }, []);
  return { library: current, reload };
};
