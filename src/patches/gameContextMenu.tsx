import { MenuItem, Patch, afterPatch, fakeRenderComponent, findInReactTree, findInTree, findModuleByExport } from "@decky/ui";
import { openGamePage } from "../api/framegenPage";
import { CONTEXT_MENU_LABEL, isSteamGame } from "../presentation/steamGamePage";

// Adds "Decky Framegen…" to a game's context menu (the gear on its page, Options in the library), the
// way SteamGridDB adds "Change Artwork…" (decky-steamgriddb src/patches/contextMenuPatch.tsx): a native
// menu entry the gamepad reaches like any other. Steam's internals it relies on change with client
// updates; every step is guarded, so at worst the entry is missing and the menu stays as it was.

const ITEM_KEY = "decky-framegen";

/** Steam's game context menu component, or null when this client hides it differently. */
function libraryContextMenu(): any {
  try {
    const module = findModuleByExport((e: any) => e?.toString && e.toString().includes("().LibraryContextMenu"));
    const sibling = Object.values(module ?? {}).find((s: any) => s?.toString?.().includes("navigator:"));
    return sibling ? fakeRenderComponent(sibling as () => unknown).type ?? null : null;
  } catch (err) {
    console.error("Decky Framegen: finding the game context menu", err);
    return null;
  }
}

/** Whether the items are a game's menu, not the one for screenshots or others. */
const isGameMenu = (items: unknown): boolean =>
  Array.isArray(items) &&
  items.length > 0 &&
  !!findInReactTree(items, (x: any) => x?.props?.onSelected?.toString().includes("launchSource"));

/** The game a menu is for: Steam passes a cached id at times, so the menu's own items decide. */
function appidOf(items: any[], fallback: number): number {
  const owner = items.find((x: any) => {
    const appid = x?._owner?.pendingProps?.overview?.appid;
    return appid && appid !== fallback;
  });
  if (owner) return owner._owner.pendingProps.overview.appid;
  // The October 2025 client keeps it on the items' app.
  return findInTree(items, (x: any) => x?.app?.appid, { walkable: ["props", "children"] })?.app?.appid ?? fallback;
}

/** Puts the entry before "Properties…", replacing one an earlier render put there. */
function addItem(items: any[], fallback: number): void {
  const previous = items.findIndex((x: any) => x?.key === ITEM_KEY);
  if (previous !== -1) items.splice(previous, 1);
  const appid = appidOf(items, fallback);
  if (!isSteamGame(appid)) return;
  const properties = items.findIndex((item) =>
    findInReactTree(item, (x: any) => x?.onSelected?.toString().includes("AppProperties")),
  );
  const entry = (
    <MenuItem key={ITEM_KEY} onSelected={() => openGamePage(String(appid))}>
      {CONTEXT_MENU_LABEL}
    </MenuItem>
  );
  items.splice(properties === -1 ? items.length : properties, 0, entry);
}

/** Patches the game context menu; returns the cleanup. */
export function patchGameContextMenu(): () => void {
  const menu = libraryContextMenu();
  if (!menu) return () => undefined;
  let inner: Patch | undefined;
  const outer = afterPatch(menu.prototype, "render", (_args: unknown[], component: any) => {
    try {
      const fallback: number =
        component?._owner?.pendingProps?.overview?.appid ??
        findInTree(component?.props?.children, (x: any) => x?.app?.appid, { walkable: ["props", "children"] })?.app
          ?.appid ??
        0;
      if (!inner) {
        inner = afterPatch(component, "type", (_a: unknown[], ret: any) => {
          const prototype = ret?.type?.prototype;
          if (!prototype) return ret;
          afterPatch(prototype, "render", (_b: unknown[], rendered: any) => {
            const items = rendered?.props?.children?.[0];
            try {
              if (isGameMenu(items)) addItem(items, fallback);
            } catch (err) {
              console.error("Decky Framegen: the game context menu entry", err);
            }
            return rendered;
          });
          // Steam re-renders the menu when the game's overview refreshes.
          afterPatch(prototype, "shouldComponentUpdate", ([next]: any[], update: boolean) => {
            try {
              if (update === true && isGameMenu(next?.children)) addItem(next.children, fallback);
            } catch {
              // another menu: left as it is
            }
            return update;
          });
          return ret;
        });
      } else if (isGameMenu(component?.props?.children)) {
        addItem(component.props.children, fallback);
      }
    } catch (err) {
      console.error("Decky Framegen: the game context menu", err);
    }
    return component;
  });
  return () => {
    outer?.unpatch();
    inner?.unpatch();
  };
}
