/** The Steam game a library page shows, from its path (/library/app/<appid>); null elsewhere. */
export const appIdFromLibraryPath = (pathname: string): string | null => pathname.match(/\/library\/app\/(\d+)/)?.[1] ?? null;

/** What the button on Steam's game page says. */
export const GAME_PAGE_BUTTON_LABEL = "Framegen";

/** What the entry in a game's context menu says. */
export const CONTEXT_MENU_LABEL = "Decky Framegen…";

/** Whether an app id is a Steam game's: a non-Steam shortcut's id has the top bit set, and the plugin
 *  patches only games in the Steam libraries. */
export const isSteamGame = (appid: number): boolean => appid > 0 && appid < 0x80000000;
