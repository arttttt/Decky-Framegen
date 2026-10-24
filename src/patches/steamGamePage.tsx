import {
  DialogButton,
  DialogButtonProps,
  afterPatch,
  appDetailsClasses,
  appDetailsHeaderClasses,
  createReactTreePatcher,
  findInReactTree,
} from "@decky/ui";
import { FC, useEffect, useRef, useState } from "react";
import { MdOutlineAutoAwesomeMotion } from "react-icons/md";
import { routerHook } from "@decky/api";
import { openGamePage } from "../api/framegenPage";
import { GAME_PAGE_BUTTON_LABEL, appIdFromLibraryPath } from "../presentation/steamGamePage";

const STEAM_GAME_ROUTE = "/library/app/:appid";

// DialogButton's own button, without the wrapper that keeps it out of the game page's gamepad
// navigation: the way ProtonDB Badges gets its badge focused there.
const FocusableButton = (DialogButton as any).render({}).type as FC<DialogButtonProps & { className?: string }>;

const CHIP_CSS = `
.decky-framegen-chip {
  display: flex; align-items: center; gap: 6px;
  min-width: 0; width: auto; padding: 4px 10px;
  font-size: 14px; font-weight: 600; line-height: 20px;
  color: #fff; background: rgba(14, 20, 27, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.2); border-radius: 4px;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.5);
}
.decky-framegen-chip.gpfocus, .decky-framegen-chip:hover {
  background: rgba(255, 255, 255, 0.9); color: #0e141b;
}
`;

/** The header holding the chip, whose class says when Steam blows it up to fullscreen. */
function topCapsule(chip: HTMLElement | null): Element | null {
  const header = Array.from(chip?.parentElement?.children ?? []).find((child) =>
    child.className.includes(appDetailsClasses.Header),
  );
  return Array.from(header?.children ?? []).find((child) => child.className.includes(appDetailsHeaderClasses.TopCapsule)) ?? null;
}

const FULLSCREEN_CLASSES = ["FullscreenEnterStart", "FullscreenEnterActive", "FullscreenEnterDone", "FullscreenExitStart", "FullscreenExitActive"] as const;

/** A chip on Steam's game page, beside other plugins' badges, that opens the game's page in the plugin.
 *  It carries no other logic, and hides while Steam shows the header fullscreen. */
function GamePageButton({ appid }: { appid: string }) {
  const ref = useRef<HTMLDivElement | null>(null);
  const [shown, setShown] = useState(true);

  useEffect(() => {
    const capsule = topCapsule(ref.current);
    if (!capsule) return;
    const observer = new MutationObserver(() => {
      const className = capsule.className;
      const fullscreen = FULLSCREEN_CLASSES.some((name) => className.includes(appDetailsHeaderClasses[name]));
      setShown(!fullscreen || className.includes(appDetailsHeaderClasses.FullscreenExitDone));
    });
    observer.observe(capsule, { attributes: true, attributeFilter: ["class"] });
    return () => observer.disconnect();
  }, []);

  // On the row ProtonDB Badges uses by default (top-left, 40px): level with it, the gamepad moves
  // between the two with left and right.
  return (
    <div ref={ref} style={{ position: "absolute", top: "40px", right: "20px", zIndex: 7 }}>
      <style>{CHIP_CSS}</style>
      {shown && (
        <FocusableButton className="decky-framegen-chip" onClick={() => openGamePage(appid)}>
          <MdOutlineAutoAwesomeMotion />
          <span>{GAME_PAGE_BUTTON_LABEL}</span>
        </FocusableButton>
      )}
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
