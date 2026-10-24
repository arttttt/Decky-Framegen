import { useState } from "react";
import { devInstallRequest, DevBuildList, listDevBuilds } from "../api";
import { canInstallThroughDecky } from "../api/deckyInstaller";
import { DeveloperSectionView, developerSectionView, selectedBuild } from "../presentation/developerSection";
import { safeAsyncOperation } from "../utils";
import { useDeckyInstall } from "./useDeckyInstall";
import { usePluginUpdates } from "./usePluginUpdates";

/** State and calls behind the Developer section; every decision is made by its view model. */
export const useDeveloperSection = (): {
  view: DeveloperSectionView;
  onCheck: () => void;
  onSelect: (channel: string) => void;
  onInstall: () => void;
} => {
  const { check } = usePluginUpdates();
  const { install, start, clearError } = useDeckyInstall();
  const [list, setList] = useState<DevBuildList | null>(null);
  const [checking, setChecking] = useState(false);
  const [selectedChannel, setSelectedChannel] = useState<string | null>(null);

  const state = { build: check.build, list, checking, selectedChannel, install, deckyInstallerAvailable: canInstallThroughDecky() };

  const onCheck = () => {
    setChecking(true);
    clearError();
    void safeAsyncOperation(listDevBuilds, "DeveloperSection -> listDevBuilds").then((answer) => {
      setChecking(false);
      setList(answer ?? { status: "error", message: "The plugin backend did not answer." });
    });
  };

  const onSelect = (channel: string) => {
    setSelectedChannel(channel);
    clearError();
  };

  const onInstall = () => {
    const build = selectedBuild(state);
    if (build) start(() => devInstallRequest(build.channel), "DeveloperSection -> devInstallRequest");
  };

  return { view: developerSectionView(state), onCheck, onSelect, onInstall };
};
