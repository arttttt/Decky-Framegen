/**
 * Patching needs an installed OptiScaler; looking at games, unpatching them and resetting
 * them to stock do not. Without it, the Patch buttons say so instead of the sections hiding.
 */
export const patchButton = (
  bundleInstalled: boolean,
  readyLabel: string,
): { label: string; enabled: boolean } =>
  bundleInstalled ? { label: readyLabel, enabled: true } : { label: "Patch: no OptiScaler version installed", enabled: false };

/** What the panel says about the OptiScaler version new patches use. */
export const libraryLine = (info: { exists: boolean; version?: string | null } | null): string =>
  info?.exists && info.version
    ? `Patches use ${info.version}, the default version in the library.`
    : "No OptiScaler version is installed yet. Downloading versions comes with the OptiScaler library section.";
