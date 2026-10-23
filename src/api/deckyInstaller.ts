import type { DeckyInstallRequest } from "./index";

/**
 * Decky Loader's own plugin installer, reached through the loader's websocket router
 * (`window.DeckyBackend`, decky-loader frontend/src/index.ts). It asks the user to confirm,
 * downloads, checks the sha256, replaces the plugin and loads the new one, so this plugin
 * is unloaded before any answer could arrive.
 */
interface DeckyBackendRouter {
  call<Args extends unknown[] = [], Return = void>(route: string, ...args: Args): Promise<Return>;
}

declare global {
  interface Window {
    DeckyBackend?: DeckyBackendRouter;
  }
}

const INSTALL_ROUTE = "utilities/install_plugin";

export const canInstallThroughDecky = (): boolean => typeof window.DeckyBackend?.call === "function";

/** Starts the installation; it is not awaited, because the plugin is reloaded while it runs. */
export const installThroughDecky = (request: DeckyInstallRequest): void => {
  void window.DeckyBackend?.call<DeckyInstallRequest>(INSTALL_ROUTE, ...request);
};
