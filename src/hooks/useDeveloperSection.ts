import { useEffect, useState } from "react";
import { getDevBuild, listDevBuilds } from "../api";
import { canInstallThroughDecky, installThroughDecky } from "../api/deckyInstaller";
import {
  DeveloperSectionState,
  DeveloperSectionView,
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
    installStarted: false,
    deckyInstallerAvailable: canInstallThroughDecky(),
  });

  useEffect(() => {
    void safeAsyncOperation(getDevBuild, "DeveloperSection -> getDevBuild").then((build) => {
      if (build) setState((s) => ({ ...s, build }));
    });
  }, []);

  const onCheck = () => {
    setState((s) => ({ ...s, checking: true }));
    void safeAsyncOperation(listDevBuilds, "DeveloperSection -> listDevBuilds").then((list) =>
      setState((s) => ({
        ...s,
        checking: false,
        list: list ?? { status: "error", message: "The plugin backend did not answer." },
      })),
    );
  };

  const onSelect = (channel: string) => setState((s) => ({ ...s, selectedChannel: channel }));

  const onInstall = () => {
    const build = selectedBuild(state);
    if (!build) return;
    setState((s) => ({ ...s, installStarted: true }));
    installThroughDecky(build.install_request);
  };

  return { view: developerSectionView(state), onCheck, onSelect, onInstall };
};
