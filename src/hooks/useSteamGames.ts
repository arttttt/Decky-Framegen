import { useCallback, useEffect, useState } from "react";
import { toaster } from "@decky/api";
import { listInstalledGames } from "../api";
import { gameToShow } from "../presentation/patching";

export type GameEntry = { appid: string; name: string; install_found?: boolean };

// The game picked in the Quick Access panel survives the panel closing.
let lastSelectedAppId = "";

/** The installed Steam games and the one picked in the panel. */
export const useSteamGames = () => {
  const [games, setGames] = useState<GameEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedAppId, setSelectedAppId] = useState<string>(() => lastSelectedAppId);

  const select = useCallback((appid: string) => {
    lastSelectedAppId = appid;
    setSelectedAppId(appid);
  }, []);

  useEffect(() => {
    void (async () => {
      try {
        const result = await listInstalledGames();
        if (result.status !== "success") throw new Error(result.message || "Failed to load games.");
        const list = result.games as GameEntry[];
        setGames(list);
        select(gameToShow(list, lastSelectedAppId));
      } catch (err) {
        toaster.toast({ title: "Decky Framegen", body: err instanceof Error ? err.message : "Failed to load games." });
      } finally {
        setLoading(false);
      }
    })();
  }, [select]);

  return { games, loading, selectedAppId, select, selected: games.find((g) => g.appid === selectedAppId) ?? null };
};
