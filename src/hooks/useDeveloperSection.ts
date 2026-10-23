import { useEffect, useRef, useState } from "react";
import { addEventListener, removeEventListener } from "@decky/api";
import { devInstallRequest, getDevBuild, listDevBuilds } from "../api";
import { canInstallThroughDecky, installThroughDecky } from "../api/deckyInstaller";
import {
  DeveloperSectionState,
  DeveloperSectionView,
  INSTALL_SETTLE_MS,
  developerSectionView,
  selectedBuild,
} from "../presentation/developerSection";
import { safeAsyncOperation } from "../utils";

/** State and calls behind the Developer section; every decision is made by its view model. */
export const useDeveloperSection = (): {
  view: DeveloperSectionView;
  onCheck: () => void;
  onSelect: (channel: string) => void;
  onInstall: () => void;
} => {
  const [state, setState] = useState<DeveloperSectionState>({
    build: null,
    list: null,
    checking: false,
    selectedChannel: null,
    install: "idle",
    download: null,
    installError: null,
    deckyInstallerAvailable: canInstallThroughDecky(),
  });

  const settleTimer = useRef<number | undefined>(undefined);
  useEffect(() => () => window.clearTimeout(settleTimer.current), []);

  // The backend reports the download of the build being installed (main.py dev_install_request).
  useEffect(() => {
    const onProgress = (_channel: string, received: number, total: number | null) =>
      setState((s) => (s.install === "downloading" ? { ...s, download: { received, total } } : s));
    const listener = addEventListener<[string, number, number | null]>("dev_build_download", onProgress);
    return () => removeEventListener("dev_build_download", listener);
  }, []);

  useEffect(() => {
    void safeAsyncOperation(getDevBuild, "DeveloperSection -> getDevBuild").then((build) => {
      if (build) setState((s) => ({ ...s, build }));
    });
  }, []);

  const onCheck = () => {
    setState((s) => ({ ...s, checking: true, installError: null }));
    void safeAsyncOperation(listDevBuilds, "DeveloperSection -> listDevBuilds").then((list) =>
      setState((s) => ({
        ...s,
        checking: false,
        list: list ?? { status: "error", message: "The plugin backend did not answer." },
      })),
    );
  };

  const onSelect = (channel: string) => setState((s) => ({ ...s, selectedChannel: channel, installError: null }));

  const onInstall = () => {
    const build = selectedBuild(state);
    if (!build) return;
    setState((s) => ({ ...s, install: "downloading", download: null, installError: null }));
    window.clearTimeout(settleTimer.current);
    void safeAsyncOperation(() => devInstallRequest(build.channel), "DeveloperSection -> devInstallRequest").then(
      (answer) => {
        if (answer?.status !== "success") {
          const message = answer?.message ?? "The plugin backend did not answer.";
          setState((s) => ({ ...s, install: "idle", installError: message }));
          return;
        }
        setState((s) => ({ ...s, install: "started" }));
        settleTimer.current = window.setTimeout(
          () => setState((s) => ({ ...s, install: "unconfirmed" })),
          INSTALL_SETTLE_MS,
        );
        installThroughDecky(answer.install_request);
      },
    );
  };

  return { view: developerSectionView(state), onCheck, onSelect, onInstall };
};
