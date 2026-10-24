import type { LaunchSetup } from "../api";

export type ProxyDllView = {
  options: { data: string; label: string }[];
  /** The proxy DLL patches use: the picked one while offered, else the backend's default; null until it answers. */
  selected: string | null;
  hint: string | null;
  /** The launch options the selected proxy needs, for copying; built by the backend. */
  launchOptions: string | null;
  wrapper: LaunchSetup["wrapper"] | null;
};

/** The proxy DLL picker and the launch strings that go with the chosen proxy. */
export const proxyDllView = (setup: LaunchSetup | null, picked: string | null): ProxyDllView => {
  if (!setup) return { options: [], selected: null, hint: null, launchOptions: null, wrapper: null };
  const proxy = setup.proxies.find((p) => p.name === picked) ?? setup.proxies.find((p) => p.name === setup.default);
  return {
    options: setup.proxies.map((p) => ({ data: p.name, label: p.name === setup.default ? `${p.name} (default)` : p.name })),
    selected: proxy?.name ?? null,
    hint: proxy?.hint ?? null,
    launchOptions: proxy?.launch_options ?? null,
    wrapper: setup.wrapper,
  };
};

/** Patching needs a library version and a proxy DLL, which arrives with the backend's launch setup. */
export const patchReady = (versionReady: boolean, launch: ProxyDllView): boolean => versionReady && launch.selected !== null;

/** Asked before the wrapper's patch command is copied: the wrapper keeps patching until it's taken out. */
export type CopyConfirmation = { title: string; lines: string[]; okLabel: string };
export const WRAPPER_PATCH_CONFIRMATION: CopyConfirmation = {
  title: "Patch Game with OptiScaler?",
  lines: [
    "WARNING: Decky Framegen does not unpatch games when uninstalled. Be sure to unpatch the game or run the OptiScaler uninstall script inside the game files if you choose to uninstall the plugin or the game has issues.",
  ],
  okLabel: "Copy Patch Command",
};

/** How long a copy button says it copied before it can copy again. */
export const COPIED_SHOWN_MS = 3000;

export const COPY_FAILED = "Couldn't copy to the clipboard.";

export type CopyState = "idle" | "copying" | "copied";

export type ClipboardButtonView = { label: string; icon: "clipboard" | "check"; pulsing: boolean; color: string | null; enabled: boolean };

/** What a copy button shows: its own label, then copying, then a green "copied" for a while. */
export const clipboardButtonView = (state: CopyState, label: string): ClipboardButtonView => {
  if (state === "copying") return { label: "Copying...", icon: "clipboard", pulsing: true, color: null, enabled: false };
  if (state === "copied") return { label: "Copied to clipboard", icon: "check", pulsing: false, color: "#4CAF50", enabled: false };
  return { label, icon: "clipboard", pulsing: false, color: null, enabled: true };
};
