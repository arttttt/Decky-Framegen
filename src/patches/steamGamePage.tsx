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
import { openGamePage } from "../api/pages";
import { CHIP_LEFT, GAME_PAGE_BUTTON_LABEL, Overlay, appIdFromLibraryPath, chipTop } from "../presentation/steamGamePage";

const STEAM_GAME_ROUTE = "/library/app/:appid";

type ChipButton = FC<DialogButtonProps & { className?: string }>;
let focusableButton: ChipButton | null = null;

/** DialogButton's own button, without the wrapper that keeps it out of the game page's gamepad
 *  navigation: the way ProtonDB Badges gets its badge focused there. Looked up when first needed, and
 *  DialogButton itself if @decky/ui changes: then only the chip's focus suffers, never the plugin. */
function chipButton(): ChipButton {
  if (!focusableButton) {
    try {
      focusableButton = ((DialogButton as any).render({}).type as ChipButton) ?? DialogButton;
    } catch {
      focusableButton = DialogButton;
    }
  }
  return focusableButton;
}

const CHIP_CSS = `
.deckyscaler-chip {
  display: flex; align-items: center; gap: 10px;
  min-width: 0; width: auto; padding: 8px 16px;
  font-size: 20px; font-weight: 700; line-height: 28px;
  color: #fff; background: rgba(14, 20, 27, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.2); border-radius: 4px;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.5);
}
.deckyscaler-chip svg { width: 24px; height: 24px; }
.deckyscaler-chip.gpfocus, .deckyscaler-chip:hover {
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

/** The badges other plugins placed before the chip in the header, relative to the header. */
function overlaysBefore(chip: HTMLElement): { overlays: Overlay[]; width: number } {
  const parent = chip.parentElement;
  if (!parent) return { overlays: [], width: 0 };
  const origin = parent.getBoundingClientRect();
  const overlays: Overlay[] = [];
  for (let node = chip.previousElementSibling; node; node = node.previousElementSibling) {
    if (getComputedStyle(node).position !== "absolute") continue;
    const rect = node.getBoundingClientRect();
    overlays.push({ left: rect.left - origin.left, top: rect.top - origin.top, bottom: rect.bottom - origin.top });
  }
  return { overlays, width: origin.width };
}

/** A chip on Steam's game page that opens the game's page in the plugin; it carries no other logic.
 *  It stacks under the badges other plugins put in the header and comes right before the play section,
 *  so Up from Play reaches it first and the next Up the badge above it. It hides while Steam shows
 *  the header fullscreen. */
function GamePageButton({ appid }: { appid: string }) {
  const ref = useRef<HTMLDivElement | null>(null);
  const [shown, setShown] = useState(true);
  const [top, setTop] = useState<number | null>(null);

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

  // Other plugins' badges appear and grow as their data loads: the chip follows them.
  useEffect(() => {
    const chip = ref.current;
    const parent = chip?.parentElement;
    if (!chip || !parent) return;
    const place = () => {
      const { overlays, width } = overlaysBefore(chip);
      setTop(chipTop(overlays, width));
    };
    place();
    const resizes = new ResizeObserver(place);
    const watchSiblings = () => {
      resizes.disconnect();
      for (let node = chip.previousElementSibling; node; node = node.previousElementSibling) resizes.observe(node);
    };
    watchSiblings();
    const children = new MutationObserver(() => {
      watchSiblings();
      place();
    });
    children.observe(parent, { childList: true, subtree: true });
    return () => {
      resizes.disconnect();
      children.disconnect();
    };
  }, []);

  const FocusableButton = chipButton();
  return (
    <div ref={ref} style={{ position: "absolute", top: `${top ?? 40}px`, left: `${CHIP_LEFT}px`, zIndex: 7 }}>
      <style>{CHIP_CSS}</style>
      {shown && top !== null && (
        <FocusableButton className="deckyscaler-chip" onClick={() => openGamePage(appid)}>
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
          const children = container.props.children.filter((child: any) => child?.type !== GamePageButton);
          // Right before the element holding Play, which comes just before the app panel (found by its
          // props; MoonDeck anchors its button the same way), and after any badge another plugin put at
          // the top: Up from Play reaches the chip first, whatever loaded first.
          const appPanel = children.findIndex((x: any) => x?.props?.overview && x?.props?.onShowLaunchingDetails);
          children.splice(appPanel > 1 ? appPanel - 1 : 1, 0, <GamePageButton key="deckyscaler" appid={appid} />);
          container.props.children = children;
        } catch (err) {
          console.error("DeckyScaler: the button on Steam's game page", err);
        }
        return ret;
      },
    );
    afterPatch(routeProps, "renderFunc", handler);
    return tree;
  });
  return () => routerHook.removePatch(STEAM_GAME_ROUTE, patch);
}
