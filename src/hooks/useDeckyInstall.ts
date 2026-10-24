import { useEffect, useRef, useState } from "react";
import { addEventListener, removeEventListener } from "@decky/api";
import { InstallRequestAnswer, PLUGIN_DOWNLOAD_EVENT } from "../api";
import { installThroughDecky } from "../api/deckyInstaller";
import { INSTALL_SETTLE_MS, InstallState, NO_INSTALL } from "../presentation/install";
import { safeAsyncOperation } from "../utils";

/** Installing a build over the plugin: the backend downloads it (its progress comes as events), then
 *  Decky installs it, and after a while a still-running plugin may install again. */
export const useDeckyInstall = () => {
  const [install, setInstall] = useState<InstallState>(NO_INSTALL);
  const settleTimer = useRef<number | undefined>(undefined);
  useEffect(() => () => window.clearTimeout(settleTimer.current), []);

  useEffect(() => {
    const onProgress = (_channel: string, received: number, total: number | null) =>
      setInstall((s) => (s.phase === "downloading" ? { ...s, download: { received, total } } : s));
    const listener = addEventListener<[string, number, number | null]>(PLUGIN_DOWNLOAD_EVENT, onProgress);
    return () => removeEventListener(PLUGIN_DOWNLOAD_EVENT, listener);
  }, []);

  const start = (request: () => Promise<InstallRequestAnswer>, context: string) => {
    setInstall({ phase: "downloading", download: null, error: null });
    window.clearTimeout(settleTimer.current);
    void safeAsyncOperation(request, context).then((answer) => {
      if (answer?.status !== "success") {
        setInstall({ ...NO_INSTALL, error: answer?.message ?? "The plugin backend did not answer." });
        return;
      }
      setInstall({ phase: "started", download: null, error: null });
      settleTimer.current = window.setTimeout(() => setInstall((s) => ({ ...s, phase: "unconfirmed" })), INSTALL_SETTLE_MS);
      installThroughDecky(answer.install_request);
    });
  };

  return { install, start, clearError: () => setInstall((s) => ({ ...s, error: null })) };
};
