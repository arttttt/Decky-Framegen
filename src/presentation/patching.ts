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

/** The version and FSR 4 variant the user picked; null leaves the choice to the defaults. */
export type PatchPick = { versionId: string | null; variant: string | null };

/** What the patch calls send: a version id and variant id; empty strings let the backend use its defaults. */
export type PatchWith = { versionId: string; variant: string };

export type PatchChoiceView = {
  versionOptions: { data: string; label: string }[];
  versionId: string | null;
  versionHint: string | null;
  variantOptions: { data: string; label: string }[];
  variant: string | null;
  ready: boolean;
  patchWith: PatchWith;
};

/**
 * What a patch will use: the picked version while it is installed, else the library's default,
 * else the newest; the picked variant when that version's family has it, else the family's default.
 */
export const patchChoice = (library: InstalledLibrary | null, pick: PatchPick): PatchChoiceView => {
  const versions = library?.versions ?? [];
  const byId = (id: string | null): InstalledVersion | undefined => versions.find((v) => v.id === id);
  const version = byId(pick.versionId) ?? byId(library?.default ?? null) ?? versions[0];
  const variant = version?.variants.find((v) => v.id === pick.variant) ?? version?.variants[0];
  return {
    versionOptions: versions.map((v) => ({
      data: v.id,
      label: `${versionLabel(v)} (${v.channel})${v.id === library?.default ? ", default" : ""}`,
    })),
    versionId: version?.id ?? null,
    versionHint: version ? null : "No OptiScaler version is installed. Download one in the OptiScaler library section.",
    variantOptions: version?.variants.map((v) => ({ data: v.id, label: v.label })) ?? [],
    variant: variant?.id ?? null,
    ready: version !== undefined,
    patchWith: { versionId: version?.id ?? "", variant: variant?.id ?? "" },
  };
};

/** What a patched game runs, and whether a later build of its channel is waiting in the library. */
export const gameVersionLine = (status: {
  patched?: boolean;
  optiscaler_version?: string | null;
  fsr4_variant_label?: string | null;
  newer_version?: string | null;
} | null): string | null => {
  if (!status?.patched) return null;
  const line = `${status.optiscaler_version ?? "Unknown version"}: ${status.fsr4_variant_label ?? "unknown FSR 4 variant"}`;
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
  fsr4_variant_label?: string | null;
  newer_version?: string | null;
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

  const statusLine = ((): SteamGameView["status"] => {
    if (!s.gameSelected) return { text: "—", tone: "neutral" };
    if (s.statusLoading) return { text: "Loading...", tone: "neutral" };
    if (!status || status.status === "error") return { text: status?.message || "—", tone: "neutral" };
    if (!status.install_found) return { text: "Install not found", tone: "warning" };
    if (!status.patched) return { text: "Not patched", tone: "neutral" };
    if (otherDll) return { text: `Patched (${dllLabel}) — switch available`, tone: "warning" };
    return { text: `Patched (${dllLabel})`, tone: "good" };
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
