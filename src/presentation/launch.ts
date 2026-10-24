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
