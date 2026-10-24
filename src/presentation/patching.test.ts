import { describe, expect, it } from "vitest";
import type { InstalledLibrary } from "../api";
import { GameStatus, fsr4Line, gameToShow, toneColor, gamePageTitle, gamePickerView, gameVersionLine, quickPatchWith, libraryReady, patchButton, patchChoice, steamGameView } from "./patching";

const LIBRARY: InstalledLibrary = {
  installed_bytes: 500_000_000,
  versions: [
    {
      id: "nightly-20261023",
      version: "10.0.0-pre1",
      channel: "nightly",
      date: "20261023",
      size: 300_000_000,
    },
    {
      id: "stable-0.9.4",
      version: "0.9.4",
      channel: "stable",
      date: "20260718",
      size: 200_000_000,
    },
  ],
};

describe("patch button", () => {
  it("patches with an installed OptiScaler and says why not without one", () => {
    expect(patchButton(true, "Patch with dxgi.dll")).toEqual({ label: "Patch with dxgi.dll", enabled: true });
    expect(patchButton(false, "Patch with dxgi.dll")).toEqual({
      label: "Patch: no OptiScaler version installed",
      enabled: false,
    });
  });
});

describe("library readiness", () => {
  it("is unknown until the library answers, then whether any version is installed", () => {
    expect(libraryReady(null)).toBeNull();
    expect(libraryReady({ versions: [], installed_bytes: 0 })).toBe(false);
    expect(libraryReady(LIBRARY)).toBe(true);
  });
});

describe("patch choice", () => {
  it("starts on the newest version", () => {
    const view = patchChoice(LIBRARY, null);

    expect(view.versionId).toBe("nightly-20261023");
    expect(view.versionOptions).toEqual([
      { data: "nightly-20261023", label: "10.0.0-pre1 · 2026-10-23 (nightly)" },
      { data: "stable-0.9.4", label: "0.9.4 · 2026-07-18 (stable)" },
    ]);
    expect(view.ready).toBe(true);
    expect(view.versionHint).toBeNull();
    expect(view.patchWith).toBe("nightly-20261023");
  });

  it("keeps a picked version while it is installed", () => {
    expect(patchChoice(LIBRARY, "stable-0.9.4").patchWith).toBe("stable-0.9.4");
  });

  it("falls back to the newest when the picked version is gone", () => {
    expect(patchChoice(LIBRARY, "nightly-20250101").versionId).toBe("nightly-20261023");
  });

  it("offers nothing and says where to get a version when the library is empty", () => {
    for (const library of [null, { versions: [], installed_bytes: 0 }]) {
      const view = patchChoice(library, "stable-0.9.4");
      expect(view).toMatchObject({ versionId: null, ready: false, versionOptions: [], patchWith: "" });
      expect(view.versionHint).toMatch(/Open Framegen → OptiScaler/);
    }
  });
});

describe("game version line", () => {
  it("names what a patched game runs and a newer build of its channel", () => {
    const patched = { patched: true, optiscaler_version: "nightly-20261023" };

    expect(gameVersionLine(patched)).toBe("nightly-20261023");
    expect(gameVersionLine({ ...patched, newer_version: "nightly-20261101" })).toBe(
      "nightly-20261023. nightly-20261101 is in the library; choose it and patch again to update.",
    );
    expect(gameVersionLine({ patched: true })).toBe("Unknown version");
    expect(gameVersionLine({ patched: false })).toBeNull();
    expect(gameVersionLine(null)).toBeNull();
  });
});

describe("steam game view", () => {
  const base = { gameSelected: true, statusLoading: false, busy: null, dllName: "dxgi.dll", ready: true };
  const patched: GameStatus = {
    status: "success", install_found: true, patched: true, dll_name: "dxgi.dll",
    optiscaler_version: "stable-0.9.4",
  };

  it("offers patching an unpatched game and reinstalling or switching a patched one", () => {
    const unpatched = steamGameView({ ...base, status: { status: "success", install_found: true, patched: false } });
    expect(unpatched).toMatchObject({
      status: { text: "Not patched", tone: "neutral" }, versionLine: null,
      patch: { label: "Patch with dxgi.dll", enabled: true }, unpatchVisible: false,
    });

    expect(steamGameView({ ...base, status: patched })).toMatchObject({
      status: { text: "Patched (dxgi.dll)", tone: "good" }, versionLine: "stable-0.9.4",
      patch: { label: "Reinstall (dxgi.dll)", enabled: true }, unpatchVisible: true,
      unpatch: { label: "Unpatch this game", enabled: true },
    });

    expect(steamGameView({ ...base, dllName: "winmm.dll", status: patched })).toMatchObject({
      status: { text: "Patched (dxgi.dll) — switch available", tone: "warning" },
      patch: { label: "Switch to winmm.dll" },
    });
  });

  it("holds patching without an install, a game, a library version, or while busy", () => {
    expect(steamGameView({ ...base, status: { status: "success", install_found: false } })).toMatchObject({
      status: { text: "Install not found", tone: "warning" }, patch: { label: "Install not found", enabled: false },
    });
    expect(steamGameView({ ...base, gameSelected: false, status: null })).toMatchObject({
      status: { text: "—" }, patch: { label: "Patch this game", enabled: false }, unpatchVisible: false,
    });
    expect(steamGameView({ ...base, ready: false, status: patched }).patch).toEqual({
      label: "Patch: no OptiScaler version installed", enabled: false,
    });
    expect(steamGameView({ ...base, busy: "patch", status: patched })).toMatchObject({
      patch: { label: "Patching...", enabled: false }, unpatch: { enabled: false },
    });
    expect(steamGameView({ ...base, busy: "unpatch", status: patched }).unpatch).toEqual({
      label: "Unpatching...", enabled: false,
    });
  });

  it("shows loading and errors in the status line and no version while loading", () => {
    expect(steamGameView({ ...base, statusLoading: true, status: patched })).toMatchObject({
      status: { text: "Loading..." }, versionLine: null,
    });
    expect(steamGameView({ ...base, status: { status: "error", message: "Steam is gone" } }).status.text).toBe("Steam is gone");
  });
});

describe("FSR 4 line", () => {
  it("says whether the game's Proton has FSR 4, will download it, or can't", () => {
    expect(fsr4Line({ state: "in-prefix", tool: "GE-Proton11-11", version: "4.1.1" })).toBe(
      "FSR 4 4.1.1 is in this game's Proton prefix.",
    );
    expect(fsr4Line({ state: "in-prefix", tool: null, version: null })).toBe("FSR 4 is in this game's Proton prefix.");
    expect(fsr4Line({ state: "will-fetch", tool: "GE-Proton11-11", version: null })).toBe(
      "GE-Proton11-11 downloads FSR 4 on the game's first launch after patching.",
    );
    expect(fsr4Line({ state: "unsupported", tool: "proton_experimental", version: null })).toBe(
      "proton_experimental can't provide FSR 4. Choose GE-Proton or Proton-CachyOS for this game.",
    );
    expect(fsr4Line({ state: "unsupported", tool: null, version: null })).toBe(
      "Steam's default Proton can't provide FSR 4. Choose GE-Proton or Proton-CachyOS for this game.",
    );
  });

  it("says nothing off AMD, and nothing while the status loads", () => {
    expect(fsr4Line(null)).toBeNull();
    const fsr4 = { state: "unsupported" as const, tool: null, version: null };
    const base = { gameSelected: true, busy: null, dllName: "dxgi.dll", ready: true };
    const status = { status: "success" as const, install_found: true, patched: false, fsr4 };
    expect(steamGameView({ ...base, statusLoading: true, status }).fsr4Line).toBeNull();
    expect(steamGameView({ ...base, statusLoading: false, status }).fsr4Line).toMatch(/can't provide FSR 4/);
  });
});

describe("Quick Access panel", () => {
  const launch = { options: [], selected: "dxgi.dll", hint: null, launchOptions: null, wrapper: null };

  it("patches a patched game with its own proxy and version, and a new one with the default proxy and the newest", () => {
    const patched: GameStatus = { status: "success", patched: true, dll_name: "winmm.dll" };

    expect(quickPatchWith(patched, launch, true)).toEqual({ dllName: "winmm.dll", versionId: "", ready: true });
    expect(quickPatchWith({ status: "success", patched: false }, launch, true)).toEqual({ dllName: "dxgi.dll", versionId: "", ready: true });
    expect(quickPatchWith(null, launch, false).ready).toBe(false);
    expect(quickPatchWith(null, { ...launch, selected: null }, true)).toEqual({ dllName: "", versionId: "", ready: false });
  });

  it("offers the games, says when they load or there are none, and marks the ones not installed", () => {
    expect(gamePickerView([], true)).toEqual({ placeholder: "Loading games...", enabled: false, options: [] });
    expect(gamePickerView([], false)).toMatchObject({ placeholder: "No Steam games found", enabled: false });
    expect(gamePickerView([{ appid: "1", name: "A" }, { appid: "2", name: "B", install_found: false }], false)).toEqual({
      placeholder: "Choose a game",
      enabled: true,
      options: [{ data: "1", label: "A" }, { data: "2", label: "B (not installed)" }],
    });
  });

  it("titles a game page with the game's name once known", () => {
    expect(gamePageTitle(null)).toBe("Loading…");
    expect(gamePageTitle({ status: "success", name: "Cyberpunk 2077" })).toBe("Cyberpunk 2077");
  });
});

describe("status tone", () => {
  it("colours a warning yellow and a good state green, and leaves neutral plain", () => {
    expect(toneColor("warning")).toBe("#ffd866");
    expect(toneColor("good")).toBe("#3fb950");
    expect(toneColor("neutral")).toBeNull();
  });
});

describe("the game the panel shows", () => {
  const games = [{ appid: "1" }, { appid: "2" }];
  it("is the one picked last while it is installed, else the first, else none", () => {
    expect(gameToShow(games, "2")).toBe("2");
    expect(gameToShow(games, "9")).toBe("1");
    expect(gameToShow(games, "")).toBe("1");
    expect(gameToShow([], "2")).toBe("");
  });
});
