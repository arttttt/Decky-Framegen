import type { AvailableDevBuild, DevBuildList, PluginBuild } from "../api";
import { DECKY_INSTALLER_UNREACHABLE, InstallState, canStartInstall, installMessage } from "./install";

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
  build: PluginBuild | null;
  list: DevBuildList | null;
  checking: boolean;
  selectedChannel: string | null;
  install: InstallState;
  deckyInstallerAvailable: boolean;
};

/** Whether development builds are offered, and with them the Developer page: Developer mode is on
 *  (always, in a development build). */
export const offered = (build: PluginBuild | null): build is Extract<PluginBuild, { known: true }> =>
  build?.known === true && build.developer_mode;

const formatDate = (iso: string): string => (iso ? iso.slice(0, 16).replace("T", " ") + " UTC" : "unknown date");

/** The build the picker points at: the user's choice, else the running build's channel, else the first. */
export const selectedBuild = (state: DeveloperSectionState): AvailableDevBuild | null => {
  if (state.list?.status !== "success" || !offered(state.build)) return null;
  const { builds } = state.list;
  const wanted = state.selectedChannel ?? state.build.channel;
  return builds.find((b) => b.channel === wanted) ?? builds[0] ?? null;
};

const statusMessage = (state: DeveloperSectionState): string | null => {
  const { deckyInstallerAvailable, list } = state;
  const installing = installMessage(state.install, selectedBuild(state)?.title ?? "the build");
  if (installing) return installing;
  if (!deckyInstallerAvailable) return DECKY_INSTALLER_UNREACHABLE;
  if (list?.status === "error") return list.message;
  if (list?.status === "success" && list.builds.length === 0) return "No development builds are published.";
  return null;
};

export const developerSectionView = (state: DeveloperSectionState): DeveloperSectionView => {
  const { build, list } = state;
  if (!offered(build)) return { visible: false };

  const selected = selectedBuild(state);
  const builds = list?.status === "success" ? list.builds : [];

  return {
    visible: true,
    running: `Running ${build.title}`,
    checkLabel: state.checking ? "Checking…" : list ? "Check again" : "Check for builds",
    checkEnabled: !state.checking && state.install.phase !== "downloading",
    pickerVisible: builds.length > 0,
    options: builds.map((b) => ({ data: b.channel, label: b.state === "installed" ? `${b.title} (running)` : b.title })),
    selectedChannel: selected?.channel ?? null,
    details: selected ? `Commit ${selected.short_commit}, published ${formatDate(selected.published_at)}` : null,
    installLabel: selected?.state === "installed" ? "Already running" : "Install",
    installEnabled:
      selected?.state === "available" &&
      state.deckyInstallerAvailable &&
      canStartInstall(state.install) &&
      !state.checking,
    message: statusMessage(state),
  };
};
