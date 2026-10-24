import type { InstalledLibrary, InstalledVersion } from "../api";
import { versionLabel } from "./library";

/**
 * Patching needs an installed OptiScaler; looking at games, unpatching them and resetting
 * them to stock do not. Without it, the Patch buttons say so instead of the sections hiding.
 */
export const patchButton = (
  ready: boolean,
  readyLabel: string,
): { label: string; enabled: boolean } =>
  ready ? { label: readyLabel, enabled: true } : { label: "Patch: no OptiScaler version installed", enabled: false };

/** Whether games can be patched: some version is in the library. Null until the library has answered. */
export const libraryReady = (library: InstalledLibrary | null): boolean | null =>
  library === null ? null : library.versions.length > 0;

/** What the patch calls send: a version id (empty lets the backend use the library's default), and
 *  whether to place it by symlinks into the library instead of copies. */
export type PatchWith = { versionId: string; link: boolean };

/** Placing by symlinks is an experiment: offered in development builds only. */
export type LinkChoice = { offered: boolean; on: boolean };

export type PatchChoiceView = {
  versionOptions: { data: string; label: string }[];
  versionId: string | null;
  versionHint: string | null;
  linkToggleVisible: boolean;
  ready: boolean;
  patchWith: PatchWith;
};

/**
 * What a patch will use: the picked version while it is installed, else the library's default,
 * else the newest. FSR 4's model is left to OptiScaler, which picks it for the GPU.
 */
export const patchChoice = (
  library: InstalledLibrary | null,
  picked: string | null,
  link: LinkChoice = { offered: false, on: false },
): PatchChoiceView => {
  const versions = library?.versions ?? [];
  const byId = (id: string | null): InstalledVersion | undefined => versions.find((v) => v.id === id);
  const version = byId(picked) ?? byId(library?.default ?? null) ?? versions[0];
  return {
    versionOptions: versions.map((v) => ({
      data: v.id,
      label: `${versionLabel(v)} (${v.channel})${v.id === library?.default ? ", default" : ""}`,
    })),
    versionId: version?.id ?? null,
    versionHint: version ? null : "No OptiScaler version is downloaded. Use Download versions… under OptiScaler versions.",
    ready: version !== undefined,
    linkToggleVisible: link.offered,
    patchWith: { versionId: version?.id ?? "", link: link.offered && link.on },
  };
};

/** What a patched game runs, and whether a later build of its channel is waiting in the library. */
export const gameVersionLine = (status: {
  patched?: boolean;
  optiscaler_version?: string | null;
  newer_version?: string | null;
} | null): string | null => {
  if (!status?.patched) return null;
  const line = status.optiscaler_version ?? "Unknown version";
  return status.newer_version ? `${line}. ${status.newer_version} is in the library; choose it and patch again to update.` : line;
};

/** A Steam game's status as get_game_status reports it. */
export type GameStatus = {
  status: "success" | "error";
  message?: string;
  install_found?: boolean;
  patched?: boolean;
  dll_name?: string | null;
  optiscaler_version?: string | null;
  newer_version?: string | null;
  linked?: boolean;
};

export type SteamGameView = {
  status: { text: string; tone: "neutral" | "warning" | "good" };
  versionLine: string | null;
  patch: { label: string; enabled: boolean };
  unpatchVisible: boolean;
  unpatch: { label: string; enabled: boolean };
};

/** What the Steam game patcher shows for the picked game, and which of its actions can run. */
export const steamGameView = (s: {
  gameSelected: boolean;
  status: GameStatus | null;
  statusLoading: boolean;
  busy: "patch" | "unpatch" | null;
  dllName: string;
  ready: boolean;
}): SteamGameView => {
  const { status, busy, dllName } = s;
  const otherDll = Boolean(status?.patched && status.dll_name && status.dll_name !== dllName);
  const dllLabel = status?.dll_name || "unknown";
  // A linked game runs OptiScaler from the library: the first thing to know about how it is patched.
  const patched = status?.linked ? "Patched with links to the library" : "Patched";

  const statusLine = ((): SteamGameView["status"] => {
    if (!s.gameSelected) return { text: "—", tone: "neutral" };
    if (s.statusLoading) return { text: "Loading...", tone: "neutral" };
    if (!status || status.status === "error") return { text: status?.message || "—", tone: "neutral" };
    if (!status.install_found) return { text: "Install not found", tone: "warning" };
    if (!status.patched) return { text: "Not patched", tone: "neutral" };
    if (otherDll) return { text: `${patched} (${dllLabel}) — switch available`, tone: "warning" };
    return { text: `${patched} (${dllLabel})`, tone: "good" };
  })();

  const patchLabel = ((): string => {
    if (busy === "patch") return "Patching...";
    if (!s.gameSelected) return "Patch this game";
    if (!status?.install_found) return "Install not found";
    if (otherDll) return `Switch to ${dllName}`;
    if (status?.patched) return `Reinstall (${dllName})`;
    return `Patch with ${dllName}`;
  })();
  const patch = patchButton(s.ready, patchLabel);
  const canPatch = s.gameSelected && Boolean(status?.install_found) && busy === null;

  return {
    status: statusLine,
    versionLine: gameVersionLine(s.statusLoading ? null : status),
    patch: { label: patch.label, enabled: patch.enabled && canPatch },
    unpatchVisible: Boolean(status?.patched),
    unpatch: { label: busy === "unpatch" ? "Unpatching..." : "Unpatch this game", enabled: busy === null },
  };
};
