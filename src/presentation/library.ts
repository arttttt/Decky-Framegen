import type {
  InstalledLibrary,
  InstalledVersion,
  LibraryChannel,
  LibraryListing,
  LibraryRemoval,
  LibraryVersion,
} from "../api";

/** Bytes of the version being downloaded received so far, and the total when GitHub said it. */
export type LibraryDownload = { received: number; total: number | null };

/** A version's row in either dialog: tapping it downloads it, or opens what can be done with it. */
export type LibraryRowView = {
  id: string;
  label: string;
  description: string;
  action: { label: string; enabled: boolean } | null;
};

const megabytes = (bytes: number): string => `${Math.max(1, Math.round(bytes / 1_000_000))} MB`;

const formatDate = (yyyymmdd: string): string =>
  /^\d{8}$/.test(yyyymmdd) ? `${yyyymmdd.slice(0, 4)}-${yyyymmdd.slice(4, 6)}-${yyyymmdd.slice(6)}` : yyyymmdd;

/** How a version is named everywhere: a nightly's number repeats across builds, its date does not. */
export const versionLabel = (version: { version: string; date: string }): string =>
  `${version.version} · ${formatDate(version.date)}`;

const downloadProgress = (download: LibraryDownload | null): string => {
  if (!download) return "Downloading…";
  if (!download.total) return `Downloading: ${megabytes(download.received)}`;
  const percent = Math.floor((download.received / download.total) * 100);
  return `Downloading: ${percent}% of ${megabytes(download.total)}`;
};

/** A dialog's note once an action ends: the backend's words, or a fallback when it did not answer. */
export const actionOutcome = (answer: { status: string; message?: string } | null, done: string): string =>
  answer?.message ?? (answer?.status === "success" ? done : "The plugin backend did not answer.");

// ── The panel ────────────────────────────────────────────────────────────────

/** One line in the panel: how many versions are on the device and which one new patches use. */
export const librarySummary = (library: InstalledLibrary | null): string => {
  if (library === null) return "Loading…";
  const count = library.versions.length;
  if (count === 0) return "No version is downloaded yet.";
  const chosen = library.versions.find((v) => v.id === library.default);
  const downloaded = `${count} ${count === 1 ? "version" : "versions"} downloaded`;
  return chosen ? `${downloaded}. New patches use ${versionLabel(chosen)}.` : `${downloaded}.`;
};

// ── Download dialog ──────────────────────────────────────────────────────────

export type DownloadState = {
  channel: LibraryChannel;
  listing: LibraryListing | null;
  checking: boolean;
  /** The version being downloaded. */
  busy: string | null;
  download: LibraryDownload | null;
  /** What the last download came to; cleared by the next action. */
  message: string | null;
};

export type DownloadView = {
  channelOptions: { data: LibraryChannel; label: string }[];
  channel: LibraryChannel;
  /** The channel stays put during a download: its end reloads the channel's listing. */
  channelEnabled: boolean;
  checkLabel: string;
  checkEnabled: boolean;
  rows: LibraryRowView[];
  message: string | null;
};

export const CHANNEL_OPTIONS: { data: LibraryChannel; label: string }[] = [
  { data: "stable", label: "Stable releases" },
  { data: "nightly", label: "Nightly builds" },
];

const describePublished = (version: LibraryVersion): string => {
  if (version.state === "installed") return "Downloaded";
  if (version.state === "unsupported") return `Can't be downloaded: ${version.reason ?? "unknown reason"}`;
  return `${megabytes(version.size)} download`;
};

const listingMessage = (listing: LibraryListing | null, channel: LibraryChannel): string | null => {
  if (listing?.status === "error") return listing.message;
  if (listing?.listing_error) return `Could not list what OptiScaler publishes (${listing.listing_error}).`;
  if (listing?.versions.length === 0) return `No ${channel} versions are published.`;
  return null;
};

export const downloadView = (state: DownloadState): DownloadView => {
  const { listing, checking, busy, channel } = state;
  const idle = busy === null;
  return {
    channelOptions: CHANNEL_OPTIONS,
    channel,
    channelEnabled: idle,
    checkLabel: checking ? "Checking…" : "Check for new versions",
    checkEnabled: !checking && idle,
    rows:
      listing?.status === "success"
        ? listing.versions.map((version) => ({
            id: version.id,
            label: versionLabel(version),
            description: busy === version.id ? downloadProgress(state.download) : describePublished(version),
            action: version.state === "available" ? { label: "Download", enabled: idle } : null,
          }))
        : [],
    message: state.message ?? listingMessage(listing, channel),
  };
};

// ── Manage dialog ────────────────────────────────────────────────────────────

export type ManageAction = "default" | "reinstall" | "remove";

export type ManageState = {
  library: InstalledLibrary | null;
  busy: { id: string; action: ManageAction } | null;
  download: LibraryDownload | null;
  /** What the last action came to; cleared by the next one. */
  message: string | null;
};

export type ManageView = {
  rows: LibraryRowView[];
  usage: string | null;
  message: string | null;
};

export type ManageMenuItem = { action: ManageAction; label: string; destructive: boolean };

const describeInstalled = (version: InstalledVersion, isDefault: boolean): string =>
  `${version.channel === "nightly" ? "Nightly" : "Stable"} · ${megabytes(version.size)}${
    isDefault ? " · used for new patches" : ""
  }`;

const busyDescription = (action: ManageAction, download: LibraryDownload | null): string => {
  if (action === "reinstall") return downloadProgress(download);
  return action === "remove" ? "Removing…" : "Making it the version for new patches…";
};

export const manageView = (state: ManageState): ManageView => {
  const { library, busy } = state;
  const versions = library?.versions ?? [];
  return {
    rows: versions.map((version) => ({
      id: version.id,
      label: versionLabel(version),
      description:
        busy?.id === version.id
          ? busyDescription(busy.action, state.download)
          : describeInstalled(version, version.id === library?.default),
      action: { label: "Manage", enabled: busy === null },
    })),
    usage: library && library.installed_bytes > 0 ? `Downloaded versions take ${megabytes(library.installed_bytes)}.` : null,
    message: state.message ?? (library && versions.length === 0 ? "No version is downloaded yet." : null),
  };
};

/** What the dialog says when an action succeeded and the backend gave no words of its own. */
export const manageDone = (action: ManageAction, id: string): string =>
  action === "default" ? `New patches use ${id}.` : action === "reinstall" ? `${id} is downloaded again.` : `${id} is removed.`;

/** What can be done with a downloaded version. */
export const manageMenu = (isDefault: boolean): ManageMenuItem[] => [
  ...(isDefault ? [] : [{ action: "default" as const, label: "Use for new patches", destructive: false }]),
  { action: "reinstall" as const, label: "Download again", destructive: false },
  { action: "remove" as const, label: "Remove", destructive: true },
];

/** What the dialog shows when Remove is picked: the question, or — told before asking — why it can't be removed. */
export type RemoveConfirmation = { title: string; lines: string[]; okLabel: string; removes: boolean };

const cantRemove = (version: InstalledVersion, reason: string): RemoveConfirmation => ({
  title: `Can't remove OptiScaler ${versionLabel(version)}`,
  lines: [reason],
  okLabel: "OK",
  removes: false,
});

/** Games patched with a version by copies keep working once it is removed; they just can't be patched with it again. */
export const removeConfirmation = (version: InstalledVersion, removal: LibraryRemoval | null): RemoveConfirmation => {
  if (removal === null) return cantRemove(version, "The plugin backend did not answer.");
  if (removal.refused !== null) return cantRemove(version, removal.refused);
  return {
    title: `Remove OptiScaler ${versionLabel(version)}?`,
    lines: removal.games.length
      ? ["These stay patched with it and keep working; patching them again needs another version:", ...removal.games]
      : ["No game is patched with it."],
    okLabel: "Remove",
    removes: true,
  };
};
