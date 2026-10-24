import type { LibraryChannel, LibraryListing, LibraryVersion } from "../api";

/** What the library section is doing to one version right now. */
export type LibraryBusy = { id: string; action: "download" | "remove" | "default" };

/** Bytes of the version being downloaded received so far, and the total when GitHub said it. */
export type LibraryDownload = { received: number; total: number | null };

export type LibraryState = {
  channel: LibraryChannel;
  listing: LibraryListing | null;
  checking: boolean;
  busy: LibraryBusy | null;
  download: LibraryDownload | null;
  /** What the last action came to (installed, removed, failed and why); cleared by the next one. */
  message: string | null;
};

/** A version's row: tapping it downloads it, or opens what can be done with an installed one. */
export type LibraryRowView = {
  id: string;
  label: string;
  description: string;
  action: { intent: "download" | "manage"; label: string; enabled: boolean } | null;
};

export type LibraryView = {
  channelOptions: { data: LibraryChannel; label: string }[];
  channel: LibraryChannel;
  /** The channel stays put while a version is downloaded or removed: the action reloads its listing. */
  channelEnabled: boolean;
  checkLabel: string;
  checkEnabled: boolean;
  usage: string | null;
  rows: LibraryRowView[];
  message: string | null;
};

export type LibraryMenuItem = { intent: "default" | "remove"; label: string; destructive: boolean };

export const CHANNEL_OPTIONS: { data: LibraryChannel; label: string }[] = [
  { data: "stable", label: "Stable releases" },
  { data: "nightly", label: "Nightly builds" },
];

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

const busyDescription = (busy: LibraryBusy, download: LibraryDownload | null): string =>
  busy.action === "download" ? downloadProgress(download) : busy.action === "remove" ? "Removing…" : "Making it the default…";

const describe = (version: LibraryVersion): string => {
  if (version.state === "installed")
    return `Installed · ${megabytes(version.size)}${version.default ? " · default for new patches" : ""}`;
  if (version.state === "unsupported") return `Can't be installed: ${version.reason ?? "unknown reason"}`;
  return `${megabytes(version.size)} download`;
};

const row = (version: LibraryVersion, state: LibraryState): LibraryRowView => {
  const idle = state.busy === null;
  const description =
    state.busy?.id === version.id ? busyDescription(state.busy, state.download) : describe(version);
  const action =
    version.state === "installed"
      ? { intent: "manage" as const, label: "Manage", enabled: idle }
      : version.state === "available"
        ? { intent: "download" as const, label: "Download", enabled: idle }
        : null;
  return { id: version.id, label: versionLabel(version), description, action };
};

const listingMessage = (listing: LibraryListing | null, channel: LibraryChannel): string | null => {
  if (listing?.status === "error") return listing.message;
  if (listing?.listing_error)
    return `Could not list what OptiScaler publishes (${listing.listing_error}). Installed versions are shown.`;
  if (listing?.versions.length === 0) return `No ${channel} versions are published.`;
  return null;
};

export const libraryView = (state: LibraryState): LibraryView => {
  const { listing, checking, busy, channel } = state;
  return {
    channelOptions: CHANNEL_OPTIONS,
    channel,
    channelEnabled: busy === null,
    checkLabel: checking ? "Checking…" : "Check for new versions",
    checkEnabled: !checking && busy === null,
    usage:
      listing?.status === "success" && listing.installed_bytes > 0
        ? `The library takes ${megabytes(listing.installed_bytes)}.`
        : null,
    rows: listing?.status === "success" ? listing.versions.map((version) => row(version, state)) : [],
    message: state.message ?? listingMessage(listing, channel),
  };
};

/** What can be done with an installed version. */
export const libraryMenu = (version: LibraryVersion): LibraryMenuItem[] => [
  ...(version.default ? [] : [{ intent: "default" as const, label: "Use for new patches", destructive: false }]),
  { intent: "remove" as const, label: "Remove", destructive: true },
];

/** Asked before removing a version; games patched with it keep working, they just can't be patched with it again. */
export const removeConfirmation = (
  version: LibraryVersion,
  games: string[],
): { title: string; lines: string[]; okLabel: string } => ({
  title: `Remove OptiScaler ${versionLabel(version)}?`,
  lines: games.length
    ? [
        "These stay patched with it and keep working; patching them again needs another version:",
        ...games,
      ]
    : ["No game is patched with it."],
  okLabel: "Remove",
});

/** The section's note once an action ends: the backend's words, or a fallback when it did not answer. */
export const actionOutcome = (answer: { status: string; message?: string } | null, done: string): string =>
  answer?.message ?? (answer?.status === "success" ? done : "The plugin backend did not answer.");
