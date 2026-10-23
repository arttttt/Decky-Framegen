/**
 * Patching needs an installed OptiScaler; looking at games, unpatching them and resetting
 * them to stock do not. Without it, the Patch buttons say so instead of the sections hiding.
 */
export const patchButton = (
  bundleInstalled: boolean,
  readyLabel: string,
): { label: string; enabled: boolean } =>
  bundleInstalled ? { label: readyLabel, enabled: true } : { label: "Patch: OptiScaler is not installed", enabled: false };
