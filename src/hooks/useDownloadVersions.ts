import { useCallback, useEffect, useState } from "react";
import { LibraryChannel, libraryInstall, libraryVersions } from "../api";
import { DownloadState, actionOutcome, downloadView } from "../presentation/library";
import { safeAsyncOperation } from "../utils";
import { useLibraryDownloadEvents } from "./useLibraryDownloadEvents";

/** State and calls behind the download dialog; `onChanged` runs after a version is added. */
export const useDownloadVersions = (onChanged: () => void) => {
  const [state, setState] = useState<DownloadState>({
    channel: "stable",
    listing: null,
    checking: false,
    busy: null,
    download: null,
    message: null,
  });

  useLibraryDownloadEvents((id, received, total) =>
    setState((s) => (s.busy === id ? { ...s, download: { received, total } } : s)),
  );

  const check = useCallback((channel: LibraryChannel, message: string | null = null) => {
    setState((s) => ({ ...s, channel, checking: true, message }));
    void safeAsyncOperation(() => libraryVersions(channel), "DownloadVersions -> libraryVersions").then((listing) =>
      setState((s) =>
        s.channel === channel
          ? { ...s, checking: false, listing: listing ?? { status: "error", message: "The plugin backend did not answer." } }
          : s,
      ),
    );
  }, []);

  useEffect(() => check("stable"), [check]);

  const onDownload = async (id: string) => {
    const channel = state.channel;
    setState((s) => ({ ...s, busy: id, download: null, message: null }));
    const answer = await safeAsyncOperation(() => libraryInstall(channel, id), "DownloadVersions -> libraryInstall");
    setState((s) => ({ ...s, busy: null, download: null }));
    if (answer?.status === "success") onChanged();
    check(channel, actionOutcome(answer ?? null, `${id} is downloaded.`));
  };

  return {
    view: downloadView(state),
    onChannel: (channel: LibraryChannel) => check(channel),
    onCheck: () => check(state.channel),
    onDownload: (id: string) => void onDownload(id),
  };
};
