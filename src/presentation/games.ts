import type { InstalledLibrary, PatchedGame } from "../api";
import { versionLabel } from "./library";

export type GameRowView = {
  key: string;
  title: string;
  lines: string[];
  /** A Steam game opens its page, which patches and unpatches it; a directory patched by path is
   *  unpatched here, having no page. */
  action: { kind: "open"; appid: string; label: string } | { kind: "unpatch"; directory: string; label: string };
};

export type GamesPageView =
  | { kind: "message"; message: string }
  | { kind: "ready"; rows: GameRowView[] };

/** A version as the library names it, or its id once it has been removed from the library. */
const versionName = (library: InstalledLibrary | null, id: string | null): string => {
  const version = library?.versions.find((v) => v.id === id);
  return version ? versionLabel(version) : id ?? "an unknown version";
};

/** What is wrong with a patch, if anything, and what to do about it. */
const problem = (game: PatchedGame): string | null => {
  if (game.record === "upstream") return "Patched by Decky Framegen: Unpatch resets it to the game's own files.";
  if (game.record === "incomplete") return "The patch didn't finish: unpatch it, then patch again.";
  if (!game.dll_present) return `${game.dll_name} is missing: patch it again.`;
  return null;
};

const row = (game: PatchedGame, library: InstalledLibrary | null): GameRowView => {
  const patchedOn = game.patched_at ? `, patched ${game.patched_at.slice(0, 10)}` : "";
  const lines = [
    `OptiScaler ${versionName(library, game.version_id)} via ${game.dll_name}${patchedOn}`,
    ...(game.newer_version ? [`${versionName(library, game.newer_version)} is in the library: patch again to update.`] : []),
    ...(game.own_settings ? ["Has settings of its own."] : []),
    ...[problem(game)].filter((line): line is string => line !== null),
  ];
  return {
    key: game.directory,
    title: game.name,
    lines,
    action: game.appid
      ? { kind: "open", appid: game.appid, label: "Open" }
      : { kind: "unpatch", directory: game.directory, label: "Unpatch" },
  };
};

/** The Games page: every game the plugin patched, or why there is nothing to list. */
export const gamesPageView = (
  answer: { status: string; message?: string; games?: PatchedGame[] } | null,
  library: InstalledLibrary | null,
): GamesPageView => {
  if (answer === null) return { kind: "message", message: "Loading…" };
  if (answer.status !== "success" || !answer.games) return { kind: "message", message: answer.message || "Couldn't list the patched games." };
  if (answer.games.length === 0) return { kind: "message", message: "No game is patched yet." };
  return { kind: "ready", rows: answer.games.map((game) => row(game, library)) };
};
