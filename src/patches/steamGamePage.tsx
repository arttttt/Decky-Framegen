import { Button, afterPatch, appDetailsClasses, createReactTreePatcher, findInReactTree } from "@decky/ui";
import { routerHook } from "@decky/api";
import { openGamePage } from "../api/framegenPage";
import { GAME_PAGE_BUTTON_LABEL, appIdFromLibraryPath } from "../presentation/steamGamePage";

const STEAM_GAME_ROUTE = "/library/app/:appid";

/** A button on Steam's game page that opens the game's page in the plugin; it carries no other logic. */
function GamePageButton({ appid }: { appid: string }) {
  return (
    <div style={{ position: "absolute", top: "110px", right: "20px", zIndex: 7 }}>
      <Button onClick={() => openGamePage(appid)} style={{ padding: "6px 12px", minWidth: 0 }}>
        {GAME_PAGE_BUTTON_LABEL}
      </Button>
    </div>
  );
}

/**
 * Puts the button on Steam's game page, the way other Decky plugins add their badges there. Steam's
 * page tree changes with client updates: anything unexpected leaves the page as it was, so at worst
 * the button is missing. Returns the cleanup.
 */
export function patchSteamGamePage(): () => void {
  const patch = routerHook.addPatch(STEAM_GAME_ROUTE, (tree: any) => {
    const routeProps = findInReactTree(tree, (x: any) => !!x?.renderFunc);
    if (!routeProps) return tree;
    const handler = createReactTreePatcher(
      [(node: any) => findInReactTree(node, (x: any) => !!x?.props?.children?.props?.overview)?.props?.children],
      (_args: unknown[], ret: any) => {
        try {
          const container = findInReactTree(
            ret,
            (x: any) => Array.isArray(x?.props?.children) && x?.props?.className?.includes(appDetailsClasses.InnerContainer),
          );
          const appid = appIdFromLibraryPath(window.location.pathname);
          if (!container || !appid) return ret;
          container.props.children = container.props.children.filter((child: any) => child?.type !== GamePageButton);
          container.props.children.splice(1, 0, <GamePageButton key="decky-framegen" appid={appid} />);
        } catch (err) {
          console.error("Decky Framegen: the button on Steam's game page", err);
        }
        return ret;
      },
    );
    afterPatch(routeProps, "renderFunc", handler);
    return tree;
  });
  return () => routerHook.removePatch(STEAM_GAME_ROUTE, patch);
}
