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
