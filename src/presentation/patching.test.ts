import { describe, expect, it } from "vitest";
import type { InstalledLibrary } from "../api";
import { GameStatus, gameVersionLine, libraryReady, patchButton, patchChoice, steamGameView } from "./patching";

const LIBRARY: InstalledLibrary = {
  default: "stable-0.9.4",
  versions: [
    {
      id: "nightly-20261023",
      version: "10.0.0-pre1",
      channel: "nightly",
      date: "20261023",
    },
    {
      id: "stable-0.9.4",
      version: "0.9.4",
      channel: "stable",
      date: "20260718",
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
    expect(libraryReady({ default: null, versions: [] })).toBe(false);
    expect(libraryReady(LIBRARY)).toBe(true);
  });
});

describe("patch choice", () => {
  it("starts on the default version", () => {
    const view = patchChoice(LIBRARY, null);

    expect(view.versionId).toBe("stable-0.9.4");
    expect(view.versionOptions).toEqual([
      { data: "nightly-20261023", label: "10.0.0-pre1 · 2026-10-23 (nightly)" },
      { data: "stable-0.9.4", label: "0.9.4 · 2026-07-18 (stable), default" },
    ]);
    expect(view.ready).toBe(true);
    expect(view.versionHint).toBeNull();
    expect(view.patchWith).toEqual({ versionId: "stable-0.9.4" });
  });

  it("keeps a picked version while it is installed", () => {
    expect(patchChoice(LIBRARY, "nightly-20261023").patchWith).toEqual({ versionId: "nightly-20261023" });
  });

  it("falls back to the default when the picked version is gone, and to the newest without a default", () => {
    expect(patchChoice(LIBRARY, "nightly-20250101").versionId).toBe("stable-0.9.4");
    expect(patchChoice({ ...LIBRARY, default: null }, null).versionId).toBe("nightly-20261023");
  });

  it("offers nothing and says where to get a version when the library is empty", () => {
    for (const library of [null, { default: null, versions: [] }]) {
      const view = patchChoice(library, "stable-0.9.4");
      expect(view).toMatchObject({ versionId: null, ready: false, versionOptions: [], patchWith: { versionId: "" } });
      expect(view.versionHint).toMatch(/OptiScaler library section/);
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
