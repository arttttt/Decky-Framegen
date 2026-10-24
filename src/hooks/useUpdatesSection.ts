import { useState } from "react";
import { toaster } from "@decky/api";
import { stableInstallRequest } from "../api";
import { canInstallThroughDecky } from "../api/deckyInstaller";
import { DEVELOPER_MODE_CONFIRMATION, updatesView } from "../presentation/updates";
import { useDeckyInstall } from "./useDeckyInstall";
import { usePluginUpdates } from "./usePluginUpdates";

/** The Updates section: checking for and installing the newest release, and Developer mode, which asks
 *  first before it turns on. */
export const useUpdatesSection = () => {
  const { check, onCheck, onDeveloperMode } = usePluginUpdates();
  const { install, start, clearError } = useDeckyInstall();
  const [asking, setAsking] = useState(false);

  const applyDeveloperMode = async (on: boolean) => {
    const failure = await onDeveloperMode(on);
    if (failure) toaster.toast({ title: "Decky Framegen", body: failure });
  };

  return {
    view: updatesView({ ...check, install, deckyInstallerAvailable: canInstallThroughDecky() }),
    onCheck: () => {
      clearError();
      onCheck();
    },
    onInstall: () => start(stableInstallRequest, "Updates -> stableInstallRequest"),
    onDeveloperMode: (on: boolean) => (on ? setAsking(true) : void applyDeveloperMode(false)),
    confirmation: asking ? DEVELOPER_MODE_CONFIRMATION : null,
    onConfirm: () => {
      setAsking(false);
      void applyDeveloperMode(true);
    },
    onCancel: () => setAsking(false),
  };
};
