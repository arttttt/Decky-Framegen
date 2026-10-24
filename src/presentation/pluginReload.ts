/**
 * Decky (v3.3.0) replaces a reloaded plugin in its list but keeps showing the plugin object that
 * was open (DeckyState.setPlugins leaves `_activePlugin` alone), so after a self-update the panel
 * shows the old UI until the user backs out. The open plugin is stale when its object has left
 * the list while a plugin of the same name is in it.
 */
export const staleActivePlugin = <P extends { name: string }>(active: P | null | undefined, plugins: P[]): string | null =>
  active && !plugins.includes(active) && plugins.some((plugin) => plugin.name === active.name) ? active.name : null;
