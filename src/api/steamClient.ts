import type { LifetimeNotification } from "@decky/ui";

/** Steam's own client API, for the launch options of a game. */

/** The game's launch options; rejects when Steam doesn't say, which is not the same as having none. */
export const getAppLaunchOptions = (appId: number): Promise<string> =>
  new Promise((resolve, reject) => {
    if (typeof SteamClient === "undefined" || !SteamClient?.Apps?.RegisterForAppDetails) {
      reject(new Error("Steam's client API is not available."));
      return;
    }
    let settled = false;
    let unregister = () => {};
    const timeout = window.setTimeout(() => {
      if (settled) return;
      settled = true;
      unregister();
      reject(new Error("Timed out reading launch options."));
    }, 5000);
    const registration = SteamClient.Apps.RegisterForAppDetails(
      appId,
      (details: { strLaunchOptions?: string }) => {
        if (settled) return;
        settled = true;
        window.clearTimeout(timeout);
        unregister();
        resolve(details?.strLaunchOptions ?? "");
      }
    );
    unregister = registration.unregister;
  });

export const setAppLaunchOptions = (appId: number, options: string): void => {
  if (typeof SteamClient !== "undefined" && SteamClient?.Apps?.SetAppLaunchOptions) {
    SteamClient.Apps.SetAppLaunchOptions(appId, options);
  }
};

/** Steam reports a stopped non-Steam shortcut with appid 0, which names no game. */
const NO_APPID = 0;
/** After Steam says a game stopped, a straggling Proton process may still hold its files for a moment. */
const STOPPED_GRACE_MS = 2000;

/** Calls back with a game's appid shortly after Steam says it stopped running; returns the unsubscribe.
 *  A no-op where Steam's client API doesn't offer it. */
export const onGameStopped = (callback: (appid: number) => void): (() => void) => {
  try {
    const registration = SteamClient?.GameSessions?.RegisterForAppLifetimeNotifications?.(
      (notification: LifetimeNotification) => {
        if (notification.bRunning || notification.unAppID === NO_APPID) return;
        window.setTimeout(() => callback(notification.unAppID), STOPPED_GRACE_MS);
      },
    );
    return () => registration?.unregister?.();
  } catch {
    return () => {};
  }
};
