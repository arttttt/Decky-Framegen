import { describe, expect, it } from "vitest";
import type { InstalledLibrary, PatchedGame } from "../api";
import { gamesPageView } from "./games";

const LIBRARY: InstalledLibrary = {
  installed_bytes: 0,
  versions: [
    { id: "nightly-20261024", version: "10.0.0-pre1", channel: "nightly", date: "20261024", size: 1 },
    { id: "nightly-20261023", version: "10.0.0-pre1", channel: "nightly", date: "20261023", size: 1 },
  ],
};

const game = (overrides: Partial<PatchedGame>): PatchedGame => ({
  directory: "/games/Cyberpunk 2077",
  name: "Cyberpunk 2077",
  appid: "1091500",
  dll_name: "dxgi.dll",
  dll_present: true,
  version_id: "nightly-20261023",
  newer_version: null,
  patched_at: "2026-10-23T18:04:00+00:00",
  record: "ok",
  own_settings: false,
  ...overrides,
});

const rowOf = (g: PatchedGame, library: InstalledLibrary | null = LIBRARY) => {
  const view = gamesPageView({ status: "success", games: [g] }, library);
  if (view.kind !== "ready") throw new Error(view.kind);
  return view.rows[0];
};

describe("the Games page", () => {
  it("is loading, then the backend's error, or says nothing is patched", () => {
    expect(gamesPageView(null, LIBRARY)).toEqual({ kind: "message", message: "Loading…" });
    expect(gamesPageView({ status: "error", message: "Broken." }, LIBRARY)).toEqual({ kind: "message", message: "Broken." });
    expect(gamesPageView({ status: "success", games: [] }, LIBRARY)).toEqual({ kind: "message", message: "No game is patched yet." });
  });

  it("names a game's version as the library does, its proxy and when it was patched", () => {
    expect(rowOf(game({}))).toEqual({
      key: "/games/Cyberpunk 2077",
      title: "Cyberpunk 2077",
      lines: ["OptiScaler 10.0.0-pre1 · 2026-10-23 via dxgi.dll, patched 2026-10-23"],
      action: { kind: "open", appid: "1091500", label: "Open" },
    });
  });

  it("falls back to a version's id once the library no longer has it", () => {
    expect(rowOf(game({ version_id: "stable-0.9.4", patched_at: null })).lines[0]).toBe("OptiScaler stable-0.9.4 via dxgi.dll");
    expect(rowOf(game({}), null).lines[0]).toContain("OptiScaler nightly-20261023");
  });

  it("tells of a newer build and settings of its own", () => {
    expect(rowOf(game({ newer_version: "nightly-20261024", own_settings: true })).lines.slice(1)).toEqual([
      "10.0.0-pre1 · 2026-10-24 is in the library: patch again to update.",
      "Has settings of its own.",
    ]);
  });

  it("says what is wrong with a patch and what to do", () => {
    expect(rowOf(game({ dll_present: false })).lines[1]).toBe("dxgi.dll is missing: patch it again.");
    expect(rowOf(game({ record: "incomplete", dll_present: false })).lines[1]).toBe("The patch didn't finish: unpatch it, then patch again.");
    expect(rowOf(game({ record: "upstream" })).lines[1]).toBe(
      "Patched by Decky Framegen: Unpatch resets it to the game's own files.",
    );
  });

  it("opens a Steam game's page, and unpatches a directory patched by path in place", () => {
    expect(rowOf(game({ appid: "", name: "/games/Manual", directory: "/games/Manual" })).action).toEqual({
      kind: "unpatch",
      directory: "/games/Manual",
      label: "Unpatch",
    });
  });
});
