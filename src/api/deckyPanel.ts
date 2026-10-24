import { staleActivePlugin } from "../presentation/pluginReload";

/**
 * Decky Loader's plugin state, reached through `window.DeckyPluginLoader` (decky-loader
 * frontend/src/start.tsx). `deckyState` is private to the loader, so every piece is checked
 * before use and anything missing makes this a no-op.
 */
type LoadedPlugin = { name: string };

interface DeckyState {
  _activePlugin?: LoadedPlugin | null;
  _plugins?: LoadedPlugin[];
  setActivePlugin?: (name: string) => void;
}

declare global {
  interface Window {
    DeckyPluginLoader?: { deckyState?: DeckyState };
  }
}

/** Shows the freshly loaded plugin in place of the one the panel still holds, if it holds a stale one. */
export const showReloadedPlugin = (): void => {
  const state = window.DeckyPluginLoader?.deckyState;
  if (!state || typeof state.setActivePlugin !== "function" || !Array.isArray(state._plugins)) return;
  const name = staleActivePlugin(state._activePlugin, state._plugins);
  if (name) state.setActivePlugin(name);
};
