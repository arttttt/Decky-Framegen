import { definePlugin, routerHook } from "@decky/api";
import { MdOutlineAutoAwesomeMotion } from "react-icons/md";
import { FramegenPage, GamePage, QuickPanel, SettingsPage } from "./components";
import { gameClosed } from "./api";
import { showReloadedPlugin } from "./api/deckyPanel";
import { onGameStopped } from "./api/steamClient";
import { FRAMEGEN_ROUTE, GAME_ROUTE, SETTINGS_ROUTE } from "./api/framegenPage";
import { patchSteamGamePage } from "./patches/steamGamePage";

export default definePlugin(() => {
  // After a self-update the loader stores this new plugin once this factory returns; the open
  // panel then still holds the old one, so it is asked to show this one on the next tick.
  window.setTimeout(showReloadedPlugin, 0);
  routerHook.addRoute(FRAMEGEN_ROUTE, FramegenPage);
  routerHook.addRoute(GAME_ROUTE, GamePage);
  routerHook.addRoute(SETTINGS_ROUTE, SettingsPage);
  const unpatchSteamGamePage = patchSteamGamePage();
  // A panel patch runs nothing of the plugin's at launch, so a game gets the settings changed while it
  // ran once it closes.
  const stopWatchingGames = onGameStopped((appid) => void gameClosed(String(appid)).catch(() => undefined));
  return {
    name: "Decky Framegen",
    titleView: <div>Decky Framegen</div>,
    alwaysRender: true,
    content: <QuickPanel />,
    icon: <MdOutlineAutoAwesomeMotion />,
    onDismount() {
      routerHook.removeRoute(FRAMEGEN_ROUTE);
      routerHook.removeRoute(GAME_ROUTE);
      routerHook.removeRoute(SETTINGS_ROUTE);
      unpatchSteamGamePage();
      stopWatchingGames();
    },
  };
});
