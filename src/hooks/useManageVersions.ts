import { useCallback, useEffect, useState } from "react";
import {
  libraryInstalled,
  libraryRemoval,
  libraryReinstall,
  libraryRemove,
} from "../api";
import {
  ManageAction,
  ManageMenuItem,
  ManageState,
  RemoveConfirmation,
  actionOutcome,
  manageDone,
  manageView,
  removeConfirmation,
} from "../presentation/library";
import { safeAsyncOperation } from "../utils";
import { useLibraryDownloadEvents } from "./useLibraryDownloadEvents";

const CALLS: Record<ManageAction, (id: string) => Promise<{ status: string; message?: string }>> = {
  reinstall: libraryReinstall,
  remove: libraryRemove,
};

/** State and calls behind the dialog that manages downloaded versions; `onChanged` runs after any change. */
export const useManageVersions = (onChanged: () => void) => {
  const [state, setState] = useState<ManageState>({ library: null, busy: null, download: null, message: null });
  const [pending, setPending] = useState<{ id: string; confirmation: RemoveConfirmation } | null>(null);

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

  /** What to show before removing: the games patched with the version, or why it can't be removed. */
  const removalOf = async (id: string) => {
    const version = versionOf(id);
    if (!version) return null;
    const removal = await safeAsyncOperation(() => libraryRemoval(id), "ManageVersions -> libraryRemoval");
    return removeConfirmation(version, removal ?? null);
  };

  /** A menu item picked for a version: runs, or first asks what the view model says to ask. */
  const onSelect = async (id: string, item: ManageMenuItem) => {
    if (!item.confirms) return void run(id, item.action);
    const confirmation = await removalOf(id);
    if (confirmation) setPending({ id, confirmation });
  };

  const onConfirm = () => {
    if (pending?.confirmation.removes) void run(pending.id, "remove");
    setPending(null);
  };

  return {
    view: manageView(state),
    onSelect: (id: string, item: ManageMenuItem) => void onSelect(id, item),
    confirmation: pending?.confirmation ?? null,
    onConfirm,
    onCancel: () => setPending(null),
  };
};
