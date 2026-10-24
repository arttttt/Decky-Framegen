import { useCallback, useEffect, useState } from "react";
import { InstalledLibrary, libraryInstalled } from "../api";
import { safeAsyncOperation } from "../utils";

/** The versions games can be patched with; `reload` after the library changes. */
export const useInstalledLibrary = (): { library: InstalledLibrary | null; reload: () => void } => {
  const [library, setLibrary] = useState<InstalledLibrary | null>(null);

  const reload = useCallback(() => {
    void safeAsyncOperation(libraryInstalled, "useInstalledLibrary -> libraryInstalled").then((answer) => {
      if (answer) setLibrary(answer);
    });
  }, []);

  useEffect(reload, [reload]);

  return { library, reload };
};
