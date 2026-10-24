/** The Steam game a library page shows, from its path (/library/app/<appid>); null elsewhere. */
export const appIdFromLibraryPath = (pathname: string): string | null => pathname.match(/\/library\/app\/(\d+)/)?.[1] ?? null;

/** What the button on Steam's game page says. */
export const GAME_PAGE_BUTTON_LABEL = "Decky Framegen";
