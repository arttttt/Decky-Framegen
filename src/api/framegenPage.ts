import { Navigation } from "@decky/ui";

/** The plugin's own full-screen pages, registered in index.tsx. */
export const FRAMEGEN_ROUTE = "/framegen";
// Not under /framegen: a route that isn't matched exactly would show the plugin's page instead.
export const GAME_ROUTE = "/framegen-game/:appid";
/** The settings editor; :scope is "global" or a game's appid. */
export const SETTINGS_ROUTE = "/framegen-settings/:scope";

const open = (path: string): void => {
  Navigation.Navigate(path);
  Navigation.CloseSideMenus();
};

/** Opens the plugin's page. */
export const openFramegenPage = (): void => open(FRAMEGEN_ROUTE);

/** Opens a Steam game's page in the plugin. */
export const openGamePage = (appid: string): void => open(GAME_ROUTE.replace(":appid", appid));

/** Opens the settings editor: the global settings, or a game's own. */
export const openSettingsPage = (scope: string): void => open(SETTINGS_ROUTE.replace(":scope", scope));
