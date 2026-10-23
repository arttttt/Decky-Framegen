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

/**
 * Where an install the user started stands. The plugin downloads the build itself
 * ("downloading"), then hands it to Decky ("started"). Decky's installer tells the plugin
 * nothing: a confirmed install replaces and reloads it, a cancelled one leaves it running.
 * So after INSTALL_SETTLE_MS a still-running plugin offers to install again.
 */
export type InstallPhase = "idle" | "downloading" | "started" | "unconfirmed";

/** Bytes of the build received so far, and the total when GitHub said it. */
export type DownloadProgress = { received: number; total: number | null };

export const INSTALL_SETTLE_MS = 15_000;

export type DeveloperSectionState = {
  build: DevBuild | null;
  list: DevBuildList | null;
  checking: boolean;
  selectedChannel: string | null;
  install: InstallPhase;
  download: DownloadProgress | null;
  /** Why the last Install could not start (the build is gone, GitHub failed); cleared by the next action. */
  installError: string | null;
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

const megabytes = (bytes: number): string => (bytes / 1_000_000).toFixed(1);

const downloadMessage = (title: string, download: DownloadProgress | null): string => {
  if (!download) return `Downloading ${title}…`;
  if (!download.total) return `Downloading ${title}: ${megabytes(download.received)} MB`;
  const percent = Math.floor((download.received / download.total) * 100);
  return `Downloading ${title}: ${percent}% (${megabytes(download.received)} of ${megabytes(download.total)} MB)`;
};

const statusMessage = (state: DeveloperSectionState): string | null => {
  const { install, installError, deckyInstallerAvailable, list } = state;
  if (install === "downloading") return downloadMessage(selectedBuild(state)?.title ?? "the build", state.download);
  if (install === "started") return "Downloaded. Decky asks to confirm, then reloads the plugin with the new build.";
  if (install === "unconfirmed") return "The plugin was not replaced. If you cancelled in Decky, install again.";
  if (installError) return installError;
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
    checkEnabled: !state.checking && state.install !== "downloading",
    pickerVisible: builds.length > 0,
    options: builds.map((b) => ({ data: b.channel, label: b.state === "installed" ? `${b.title} (running)` : b.title })),
    selectedChannel: selected?.channel ?? null,
    details: selected ? `Commit ${selected.short_commit}, published ${formatDate(selected.published_at)}` : null,
    installLabel: selected?.state === "installed" ? "Already running" : "Install",
    installEnabled:
      selected?.state === "available" &&
      state.deckyInstallerAvailable &&
      (state.install === "idle" || state.install === "unconfirmed") &&
      !state.checking,
    message: statusMessage(state),
  };
};
