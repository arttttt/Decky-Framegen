import { useCallback, useEffect, useState } from "react";
import { addEventListener, removeEventListener } from "@decky/api";
import {
  LibraryChannel,
  LibraryVersion,
  libraryGamesUsing,
  libraryInstall,
  libraryRemove,
  librarySetDefault,
  libraryVersions,
} from "../api";
import { LibraryBusy, LibraryState, actionOutcome, libraryView, removeConfirmation } from "../presentation/library";
import { safeAsyncOperation } from "../utils";

/** State and calls behind the OptiScaler library section; every decision is made by its view model.
 *  `onChanged` runs after the installed versions change, so patching offers the new set. */
export const useLibrary = (onChanged: () => void) => {
  const [state, setState] = useState<LibraryState>({
    channel: "stable",
    listing: null,
    checking: false,
    busy: null,
    download: null,
    message: null,
  });

  // The backend reports the download of the version being installed (main.py library_install).
  useEffect(() => {
    const onProgress = (_id: string, received: number, total: number | null) =>
      setState((s) => (s.busy?.action === "download" ? { ...s, download: { received, total } } : s));
    const listener = addEventListener<[string, number, number | null]>("library_download", onProgress);
    return () => removeEventListener("library_download", listener);
  }, []);

  const check = useCallback((channel: LibraryChannel, message: string | null = null) => {
    setState((s) => ({ ...s, channel, checking: true, message }));
    void safeAsyncOperation(() => libraryVersions(channel), "Library -> libraryVersions").then((listing) =>
      setState((s) =>
        s.channel === channel
          ? { ...s, checking: false, listing: listing ?? { status: "error", message: "The plugin backend did not answer." } }
          : s,
      ),
    );
  }, []);

  useEffect(() => check("stable"), [check]);

  const run = async (busy: LibraryBusy, call: () => Promise<{ status: string; message?: string } | undefined>, done: string) => {
    setState((s) => ({ ...s, busy, download: null, message: null }));
    const answer = await call();
    setState((s) => ({ ...s, busy: null, download: null }));
    if (answer?.status === "success") onChanged();
    check(state.channel, actionOutcome(answer ?? null, done));
  };

  const onDownload = (id: string) =>
    void run(
      { id, action: "download" },
      () => safeAsyncOperation(() => libraryInstall(state.channel, id), "Library -> libraryInstall"),
      `${id} is installed.`,
    );

  const onMakeDefault = (id: string) =>
    void run(
      { id, action: "default" },
      () => safeAsyncOperation(() => librarySetDefault(id), "Library -> librarySetDefault"),
      `New patches use ${id}.`,
    );

  /** The confirmation to show before removing, naming the games patched with the version. */
  const removalOf = async (version: LibraryVersion) => {
    const using = await safeAsyncOperation(() => libraryGamesUsing(version.id), "Library -> libraryGamesUsing");
    return removeConfirmation(version, using?.games ?? []);
  };

  const onRemove = (id: string) =>
    void run(
      { id, action: "remove" },
      () => safeAsyncOperation(() => libraryRemove(id), "Library -> libraryRemove"),
      `${id} is removed.`,
    );

  const versionById = (id: string): LibraryVersion | undefined =>
    state.listing?.status === "success" ? state.listing.versions.find((v) => v.id === id) : undefined;

  return {
    view: libraryView(state),
    versionById,
    onChannel: (channel: LibraryChannel) => check(channel),
    onCheck: () => check(state.channel),
    onDownload,
    onMakeDefault,
    removalOf,
    onRemove,
  };
};
