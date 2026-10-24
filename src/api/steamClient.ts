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
