import { useCallback, useEffect, useMemo, useState } from "react";
import { ButtonItem, DropdownItem, Field, PanelSectionRow } from "@decky/ui";
import { toaster } from "@decky/api";
import { listInstalledGames, getGameStatus, patchGame } from "../api";
import { getAppLaunchOptions, setAppLaunchOptions } from "../api/steamClient";
import { UnpatchConfirmation } from "./UnpatchConfirmation";
import { useUnpatch } from "../hooks/useUnpatch";
import { GameStatus, PatchWith, SteamGameView, steamGameView } from "../presentation/patching";

type GameEntry = { appid: string; name: string; install_found?: boolean };

const TONE_COLORS: Record<SteamGameView["status"]["tone"], string | undefined> = {
  neutral: undefined,
  warning: "#ffd866",
  good: "#3fb950",
};

// ─── Module-level state persistence ──────────────────────────────────────────

let lastSelectedAppId = "";

// ─── Component ───────────────────────────────────────────────────────────────

interface SteamGamePatcherProps {
  dllName: string;
  patchWith: PatchWith;
  ready: boolean;
}

export function SteamGamePatcher({ dllName, patchWith, ready }: SteamGamePatcherProps) {
  const [games, setGames] = useState<GameEntry[]>([]);
  const [gamesLoading, setGamesLoading] = useState(true);
  const [selectedAppId, setSelectedAppId] = useState<string>(() => lastSelectedAppId);
  const [gameStatus, setGameStatus] = useState<GameStatus | null>(null);
  const [statusLoading, setStatusLoading] = useState(false);
  const [patching, setPatching] = useState(false);
  const [resultMessage, setResultMessage] = useState<string>("");

  // ── Data loaders ───────────────────────────────────────────────────────────

  const loadGames = useCallback(async () => {
    setGamesLoading(true);
    try {
      const result = await listInstalledGames();
      if (result.status !== "success") throw new Error(result.message || "Failed to load games.");
      const gameList = result.games as GameEntry[];
      setGames(gameList);
      if (!gameList.length) {
        lastSelectedAppId = "";
        setSelectedAppId("");
        return;
      }
      setSelectedAppId((current) => {
        const valid =
          current && gameList.some((g) => g.appid === current) ? current : gameList[0].appid;
        lastSelectedAppId = valid;
        return valid;
      });
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to load games.";
      toaster.toast({ title: "Decky Framegen", body: msg });
    } finally {
      setGamesLoading(false);
    }
  }, []);

  const loadStatus = useCallback(async (appid: string) => {
    if (!appid) {
      setGameStatus(null);
      return;
    }
    setStatusLoading(true);
    try {
      const result = await getGameStatus(appid);
      setGameStatus(result as GameStatus);
    } catch (err) {
      setGameStatus({
        status: "error",
        message: err instanceof Error ? err.message : "Failed to load status.",
      });
    } finally {
      setStatusLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadGames();
  }, [loadGames]);

  useEffect(() => {
    if (!selectedAppId) {
      setGameStatus(null);
      return;
    }
    void loadStatus(selectedAppId);
  }, [selectedAppId, loadStatus]);

  // ── Derived state ──────────────────────────────────────────────────────────

  const selectedGame = useMemo(
    () => games.find((g) => g.appid === selectedAppId) ?? null,
    [games, selectedAppId]
  );


  const unpatch = useUnpatch(
    selectedGame ? { kind: "game", appid: selectedGame.appid, name: selectedGame.name } : null,
    () => void loadStatus(selectedAppId),
  );
  const busyAction = patching ? "patch" : unpatch.busy ? "unpatch" : null;

  const view = steamGameView({
    gameSelected: selectedGame !== null,
    status: gameStatus,
    statusLoading,
    busy: busyAction,
    dllName,
    ready,
  });

  // ── Actions ────────────────────────────────────────────────────────────────

  const handlePatch = useCallback(async () => {
    if (!selectedGame || !selectedAppId || busyAction) return;
    setPatching(true);
    setResultMessage("");
    try {
      let currentLaunchOptions = "";
      try {
        currentLaunchOptions = await getAppLaunchOptions(Number(selectedAppId));
      } catch {
        // non-fatal: proceed without current launch options
      }
      const result = await patchGame(selectedAppId, dllName, currentLaunchOptions, patchWith.versionId, patchWith.link);
      if (result.status !== "success") throw new Error(result.message || "Patch failed.");
      setAppLaunchOptions(Number(selectedAppId), result.launch_options || "");
      const msg = result.message || `Patched ${selectedGame.name}.`;
      setResultMessage(msg);
      toaster.toast({ title: "Decky Framegen", body: msg });
      await loadStatus(selectedAppId);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Patch failed.";
      setResultMessage(`Error: ${msg}`);
      toaster.toast({ title: "Decky Framegen", body: msg });
    } finally {
      setPatching(false);
    }
  }, [busyAction, dllName, loadStatus, patchWith, selectedAppId, selectedGame]);


  const focusableFieldProps = { focusable: true, highlightOnFocus: true } as const;

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <>
      <PanelSectionRow>
        <DropdownItem
          layout="below"
          label="Steam game"
          menuLabel="Select a Steam game"
          strDefaultLabel={gamesLoading ? "Loading games..." : "Choose a game"}
          disabled={gamesLoading || games.length === 0}
          selectedOption={selectedAppId}
          rgOptions={games.map((g) => ({
            data: g.appid,
            label: g.install_found === false ? `${g.name} (not installed)` : g.name,
          }))}
          onChange={(option) => {
            const next = String(option.data);
            lastSelectedAppId = next;
            setSelectedAppId(next);
            setResultMessage("");
          }}
        />
      </PanelSectionRow>

      {selectedGame && (
        <>
          <PanelSectionRow>
            <Field {...focusableFieldProps} label="Patch status">
              {TONE_COLORS[view.status.tone] ? (
                <span style={{ color: TONE_COLORS[view.status.tone], fontWeight: 600 }}>{view.status.text}</span>
              ) : (
                view.status.text
              )}
            </Field>
          </PanelSectionRow>

          {view.versionLine && (
            <PanelSectionRow>
              <Field {...focusableFieldProps} label="OptiScaler" description={view.versionLine} />
            </PanelSectionRow>
          )}

          <PanelSectionRow>
            <ButtonItem layout="below" disabled={!view.patch.enabled} onClick={handlePatch}>
              {view.patch.label}
            </ButtonItem>
          </PanelSectionRow>

          {view.unpatchVisible && (
            <PanelSectionRow>
              <ButtonItem layout="below" disabled={!view.unpatch.enabled} onClick={unpatch.onUnpatch}>
                {view.unpatch.label}
              </ButtonItem>
            </PanelSectionRow>
          )}

          <UnpatchConfirmation
            confirmation={unpatch.confirmation}
            onConfirm={unpatch.onConfirm}
            onCancel={unpatch.onCancel}
          />

          <PanelSectionRow>
            <ButtonItem
              layout="below"
              disabled={!selectedAppId || busyAction !== null || statusLoading}
              onClick={() => void loadStatus(selectedAppId)}
            >
              {statusLoading ? "Refreshing..." : "Refresh status"}
            </ButtonItem>
          </PanelSectionRow>

          {resultMessage && (
            <PanelSectionRow>
              <Field {...focusableFieldProps} label="Result">
                {resultMessage}
              </Field>
            </PanelSectionRow>
          )}
        </>
      )}
    </>
  );
}
