/**
 * Installing a build over the running plugin, a release or a development build alike. The plugin
 * downloads the build itself ("downloading"), then hands it to Decky ("started"). Decky's installer tells
 * the plugin nothing: a confirmed install replaces and reloads it, a cancelled one leaves it running. So
 * after INSTALL_SETTLE_MS a still-running plugin offers to install again ("unconfirmed").
 */
export type InstallPhase = "idle" | "downloading" | "started" | "unconfirmed";

/** Bytes of the build received so far, and the total when GitHub said it. */
export type DownloadProgress = { received: number; total: number | null };

export const INSTALL_SETTLE_MS = 15_000;

export type InstallState = {
  phase: InstallPhase;
  download: DownloadProgress | null;
  /** Why the last install could not start (the build is gone, GitHub failed); cleared by the next action. */
  error: string | null;
};

export const NO_INSTALL: InstallState = { phase: "idle", download: null, error: null };

/** Whether another install may start: none is running, or the last one was cancelled in Decky. */
export const canStartInstall = (install: InstallState): boolean => install.phase === "idle" || install.phase === "unconfirmed";

export const DECKY_INSTALLER_UNREACHABLE = "Decky's installer is not reachable from this plugin; install builds by URL instead.";

const megabytes = (bytes: number): string => (bytes / 1_000_000).toFixed(1);

const downloadMessage = (title: string, download: DownloadProgress | null): string => {
  if (!download) return `Downloading ${title}…`;
  if (!download.total) return `Downloading ${title}: ${megabytes(download.received)} MB`;
  const percent = Math.floor((download.received / download.total) * 100);
  return `Downloading ${title}: ${percent}% (${megabytes(download.received)} of ${megabytes(download.total)} MB)`;
};

/** What an install says while it runs or after it stopped; null when there is nothing to say. */
export const installMessage = (install: InstallState, title: string): string | null => {
  if (install.phase === "downloading") return downloadMessage(title, install.download);
  if (install.phase === "started") return "Downloaded. Decky asks to confirm, then reloads the plugin with the new build.";
  if (install.phase === "unconfirmed") return "The plugin was not replaced. If you cancelled in Decky, install again.";
  return install.error;
};
