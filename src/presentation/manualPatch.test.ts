import { describe, expect, it } from "vitest";
import { manualPatchView, pickerStartPaths } from "./manualPatch";

describe("the directory picker", () => {
  it("opens at the directory picked last, then the Steam library, then home", () => {
    const defaults = { home: "/home/deck", steam_common: "/home/deck/.local/share/Steam/steamapps/common" };
    expect(pickerStartPaths("/games/Foo", defaults)).toEqual(["/games/Foo", defaults.steam_common, "/home/deck"]);
    expect(pickerStartPaths(null, defaults)).toEqual([defaults.steam_common, "/home/deck"]);
  });

  it("leaves out what it doesn't know yet", () => {
    expect(pickerStartPaths(null, null)).toEqual([]);
    expect(pickerStartPaths(null, { home: "/home/deck" })).toEqual(["/home/deck"]);
  });
});

describe("patching a directory by hand", () => {
  it("patches and unpatches when idle and a version is installed", () => {
    expect(manualPatchView({ ready: true, busy: null, result: null })).toEqual({
      patch: { label: "Patch directory", enabled: true },
      unpatch: { label: "Unpatch directory", enabled: true },
      result: null,
    });
  });

  it("says why Patch can't run without a version, and still unpatches", () => {
    const view = manualPatchView({ ready: false, busy: null, result: null });
    expect(view.patch).toEqual({ label: "Patch: no OptiScaler version installed", enabled: false });
    expect(view.unpatch.enabled).toBe(true);
  });

  it("runs neither while either runs, and says which runs", () => {
    expect(manualPatchView({ ready: true, busy: "patch", result: null })).toMatchObject({
      patch: { label: "Patching...", enabled: false },
      unpatch: { enabled: false },
    });
    expect(manualPatchView({ ready: true, busy: "unpatch", result: null })).toMatchObject({
      patch: { enabled: false },
      unpatch: { label: "Unpatching...", enabled: false },
    });
  });

  it("reports the last patch, with the reason it failed", () => {
    const view = (result: { status: string; message?: string; output?: string }) =>
      manualPatchView({ ready: true, busy: null, result }).result;
    expect(view({ status: "success", message: "Patched." })).toEqual({ label: "Game patched", text: null });
    expect(view({ status: "error", message: "No exe here." })).toEqual({ label: "Patch failed", text: "No exe here." });
    expect(view({ status: "error", message: "No exe here.", output: "log" })).toEqual({ label: "Patch failed", text: "No exe here." });
    expect(view({ status: "error", output: "log" })).toEqual({ label: "Patch failed", text: "log" });
    expect(view({ status: "error" })).toEqual({ label: "Patch failed", text: "No reason given." });
  });
});
