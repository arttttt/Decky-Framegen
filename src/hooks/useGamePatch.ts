import { useCallback, useEffect, useState } from "react";
import { notify } from "../utils/notify";
import { getGameStatus, patchGame } from "../api";
import { getAppLaunchOptions, setAppLaunchOptions } from "../api/steamClient";
import { GameStatus, PatchWith, steamGameView } from "../presentation/patching";
import { useUnpatch } from "./useUnpatch";

/** A Steam game's patch: its status, and patching and unpatching it. `patchWithFor` says, from the
 *  game's status, which proxy and version a patch uses (a presentation rule). */
export const useGamePatch = (appid: string | null, patchWithFor: (status: GameStatus | null) => PatchWith) => {
  const [status, setStatus] = useState<GameStatus | null>(null);
  const [statusLoading, setStatusLoading] = useState(false);
  const [patching, setPatching] = useState(false);
  const [resultMessage, setResultMessage] = useState("");

  const loadStatus = useCallback(async () => {
    if (!appid) {
      setStatus(null);
      return;
    }
    setStatusLoading(true);
    try {
      setStatus((await getGameStatus(appid)) as GameStatus);
    } catch (err) {
      setStatus({ status: "error", message: err instanceof Error ? err.message : "Failed to load status." });
    } finally {
      setStatusLoading(false);
    }
  }, [appid]);

  useEffect(() => {
    setResultMessage("");
    void loadStatus();
  }, [loadStatus]);

  const patchWith = patchWithFor(status);
  const name = status?.name ?? "this game";
  // The last patch's result no longer holds once the game is unpatched.
  const unpatch = useUnpatch(appid ? { kind: "game", appid, name } : null, () => {
    setResultMessage("");
    void loadStatus();
  });
  const busy = patching ? "patch" : unpatch.busy ? "unpatch" : null;

  const onPatch = useCallback(async () => {
    if (!appid || busy) return;
    setPatching(true);
    setResultMessage("");
    try {
      // Unknown, not empty, when Steam doesn't answer: the backend then keeps what it stored or refuses.
      const currentLaunchOptions = await getAppLaunchOptions(Number(appid)).catch(() => null);
      const result = await patchGame(appid, patchWith.dllName, currentLaunchOptions, patchWith.versionId);
      if (result.status !== "success") throw new Error(result.message || "Patch failed.");
      setAppLaunchOptions(Number(appid), result.launch_options || "");
      const message = result.message || `Patched ${name}.`;
      setResultMessage(message);
      notify(message);
      await loadStatus();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Patch failed.";
      setResultMessage(`Error: ${message}`);
      notify(message);
    } finally {
      setPatching(false);
    }
  }, [appid, busy, loadStatus, name, patchWith.dllName, patchWith.versionId]);

  const view = steamGameView({
    gameSelected: Boolean(appid),
    status,
    statusLoading,
    busy,
    dllName: patchWith.dllName,
    ready: patchWith.ready,
  });

  return { status, view, onPatch, unpatch, resultMessage };
};

export type GamePatch = ReturnType<typeof useGamePatch>;
