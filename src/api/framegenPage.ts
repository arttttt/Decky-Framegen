import { Navigation } from "@decky/ui";

/** The plugin's own full-screen page, registered in index.tsx. */
export const FRAMEGEN_ROUTE = "/framegen";

/** Opens the plugin's page from the Quick Access panel. */
export const openFramegenPage = (): void => {
  Navigation.Navigate(FRAMEGEN_ROUTE);
  Navigation.CloseSideMenus();
};
