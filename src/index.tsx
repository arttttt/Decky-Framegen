import { definePlugin, routerHook } from "@decky/api";
import { MdOutlineAutoAwesomeMotion } from "react-icons/md";
import { FramegenPage, GamePage, QuickPanel } from "./components";
import { showReloadedPlugin } from "./api/deckyPanel";
import { FRAMEGEN_ROUTE, GAME_ROUTE } from "./api/framegenPage";
import { patchGameContextMenu } from "./patches/gameContextMenu";
import { patchSteamGamePage } from "./patches/steamGamePage";

export default definePlugin(() => {
  // After a self-update the loader stores this new plugin once this factory returns; the open
  // panel then still holds the old one, so it is asked to show this one on the next tick.
  window.setTimeout(showReloadedPlugin, 0);
  routerHook.addRoute(FRAMEGEN_ROUTE, FramegenPage);
  routerHook.addRoute(GAME_ROUTE, GamePage);
  const unpatchSteamGamePage = patchSteamGamePage();
  const unpatchGameContextMenu = patchGameContextMenu();
  return {
    name: "Decky Framegen",
    titleView: <div>Decky Framegen</div>,
    alwaysRender: true,
    content: <QuickPanel />,
    icon: <MdOutlineAutoAwesomeMotion />,
    onDismount() {
      routerHook.removeRoute(FRAMEGEN_ROUTE);
      routerHook.removeRoute(GAME_ROUTE);
      unpatchSteamGamePage();
      unpatchGameContextMenu();
    },
  };
});
