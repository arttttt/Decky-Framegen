/** The Steam game a library page shows, from its path (/library/app/<appid>); null elsewhere. */
export const appIdFromLibraryPath = (pathname: string): string | null => pathname.match(/\/library\/app\/(\d+)/)?.[1] ?? null;

/** What the button on Steam's game page says. */
export const GAME_PAGE_BUTTON_LABEL = "Framegen";

/** Where other plugins' badges sit in the game page header, relative to it. */
export type Overlay = { left: number; top: number; bottom: number };

export const CHIP_LEFT = 20;
const CHIP_TOP = 40;
const CHIP_GAP = 8;

/** The chip's top in the game page header: under the lowest badge other plugins put in its left half,
 *  else where such badges usually start. Nothing here knows which plugin put a badge there. */
export const chipTop = (overlays: Overlay[], headerWidth: number): number => {
  const leftHalf = overlays.filter((o) => o.left < headerWidth / 2 && o.bottom > o.top);
  return leftHalf.length ? Math.max(...leftHalf.map((o) => o.bottom)) + CHIP_GAP : CHIP_TOP;
};
