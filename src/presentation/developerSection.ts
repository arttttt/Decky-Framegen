import type { AvailableDevBuild, DevBuild, DevBuildList } from "../api";

/** Everything the Developer section shows; the component maps it and decides nothing. */
export type DeveloperSectionView =
  | { visible: false }
  | {
      visible: true;
      running: string;
      checkLabel: string;
      checkEnabled: boolean;
      pickerVisible: boolean;
      options: { data: string; label: string }[];
      selectedChannel: string | null;
      details: string | null;
      installLabel: string;
      installEnabled: boolean;
      message: string | null;
    };

export type DeveloperSectionState = {
  build: DevBuild | null;
  list: DevBuildList | null;
  checking: boolean;
  selectedChannel: string | null;
  installStarted: boolean;
  deckyInstallerAvailable: boolean;
};

const formatDate = (iso: string): string => (iso ? iso.slice(0, 16).replace("T", " ") + " UTC" : "unknown date");

/** The build the picker points at: the user's choice, else the running build's channel, else the first. */
export const selectedBuild = (state: DeveloperSectionState): AvailableDevBuild | null => {
  if (state.list?.status !== "success" || state.build?.is_dev_build !== true) return null;
  const { builds } = state.list;
  const wanted = state.selectedChannel ?? state.build.channel;
  return builds.find((b) => b.channel === wanted) ?? builds[0] ?? null;
};

const statusMessage = ({ installStarted, deckyInstallerAvailable, list }: DeveloperSectionState): string | null => {
  if (installStarted) return "Decky asks to confirm, then reloads the plugin with the new build.";
  if (!deckyInstallerAvailable) return "Decky's installer is not reachable from this plugin; install builds by URL instead.";
  if (list?.status === "error") return list.message;
  if (list?.status === "success" && list.builds.length === 0) return "No development builds are published.";
  return null;
};

export const developerSectionView = (state: DeveloperSectionState): DeveloperSectionView => {
  const { build, list } = state;
  if (build?.is_dev_build !== true) return { visible: false };

  const selected = selectedBuild(state);
  const builds = list?.status === "success" ? list.builds : [];

  return {
    visible: true,
    running: `Running ${build.title}`,
    checkLabel: state.checking ? "Checking…" : list ? "Check again" : "Check for builds",
    checkEnabled: !state.checking && !state.installStarted,
    pickerVisible: builds.length > 0,
    options: builds.map((b) => ({ data: b.channel, label: b.state === "installed" ? `${b.title} (running)` : b.title })),
    selectedChannel: selected?.channel ?? null,
    details: selected ? `Commit ${selected.short_commit}, published ${formatDate(selected.published_at)}` : null,
    installLabel: selected?.state === "installed" ? "Already running" : "Install",
    installEnabled:
      selected?.state === "available" && state.deckyInstallerAvailable && !state.installStarted && !state.checking,
    message: statusMessage(state),
  };
};
