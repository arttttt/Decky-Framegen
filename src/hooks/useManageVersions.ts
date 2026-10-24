import { useCallback, useEffect, useState } from "react";
import {
  libraryGamesUsing,
  libraryInstalled,
  libraryReinstall,
  libraryRemove,
  librarySetDefault,
} from "../api";
import { ManageAction, ManageState, actionOutcome, manageDone, manageView, removeConfirmation } from "../presentation/library";
import { safeAsyncOperation } from "../utils";
import { useLibraryDownloadEvents } from "./useLibraryDownloadEvents";

const CALLS: Record<ManageAction, (id: string) => Promise<{ status: string; message?: string }>> = {
  default: librarySetDefault,
  reinstall: libraryReinstall,
  remove: libraryRemove,
};

/** State and calls behind the dialog that manages downloaded versions; `onChanged` runs after any change. */
export const useManageVersions = (onChanged: () => void) => {
  const [state, setState] = useState<ManageState>({ library: null, busy: null, download: null, message: null });

  useLibraryDownloadEvents((id, received, total) =>
    setState((s) => (s.busy?.id === id && s.busy.action === "reinstall" ? { ...s, download: { received, total } } : s)),
  );

  const load = useCallback(() => {
    void safeAsyncOperation(libraryInstalled, "ManageVersions -> libraryInstalled").then((library) => {
      if (library) setState((s) => ({ ...s, library }));
    });
  }, []);

  useEffect(load, [load]);

  const run = async (id: string, action: ManageAction) => {
    setState((s) => ({ ...s, busy: { id, action }, download: null, message: null }));
    const answer = await safeAsyncOperation(() => CALLS[action](id), `ManageVersions -> ${action}`);
    setState((s) => ({ ...s, busy: null, download: null, message: actionOutcome(answer ?? null, manageDone(action, id)) }));
    if (answer?.status === "success") onChanged();
    load();
  };

  const versionOf = (id: string) => state.library?.versions.find((v) => v.id === id);

  /** The confirmation to show before removing, naming the games patched with the version. */
  const removalOf = async (id: string) => {
    const version = versionOf(id);
    if (!version) return null;
    const using = await safeAsyncOperation(() => libraryGamesUsing(id), "ManageVersions -> libraryGamesUsing");
    return removeConfirmation(version, using?.games ?? []);
  };

  return {
    view: manageView(state),
    isDefault: (id: string) => state.library?.default === id,
    run: (id: string, action: ManageAction) => void run(id, action),
    removalOf,
  };
};
