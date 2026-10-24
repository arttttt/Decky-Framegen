import { describe, expect, it } from "vitest";
import type { UnpatchPreview } from "../api";
import { unpatchOutcome, unpatchStep, unpatchSubject } from "./unpatch";

const reset = (overrides: Partial<Extract<UnpatchPreview, { mode: "reset" }>> = {}): UnpatchPreview => ({
  status: "success",
  mode: "reset",
  target_dir: "/games/Old Game",
  evidence: "marker",
  remove: ["dxgi.dll", "OptiScaler.ini"],
  restore: ["libxess.dll"],
  unrecoverable: [],
  launch_options: "mangohud %command%",
  ...overrides,
});

describe("unpatch step", () => {
  it("undoes a patch record at once, with nothing to confirm", () => {
    expect(unpatchStep({ status: "success", mode: "record", target_dir: "/games/New" }, "New")).toEqual({ kind: "now" });
  });

  it("passes a refusal through without offering anything", () => {
    expect(unpatchStep({ status: "error", message: "No sign of DeckyScaler" }, "Old Game")).toEqual({
      kind: "refused",
      message: "No sign of DeckyScaler",
    });
  });

  it("asks before resetting an older version's patch: why, where, what is restored and removed, and the launch options", () => {
    expect(unpatchStep(reset(), "Old Game")).toEqual({
      kind: "confirm",
      title: "Unpatch Old Game?",
      lines: [
        "An older version of the plugin patched this game.",
        "In /games/Old Game:",
        "Restore from backup: libxess.dll",
        "Remove: dxgi.dll, OptiScaler.ini",
        "Launch options become: mangohud %command%",
      ],
      okLabel: "Unpatch",
    });
  });

  it("names files without a backup and how to get them back, and says when launch options are cleared or kept", () => {
    const step = unpatchStep(reset({ unrecoverable: ["nvapi64.dll"], launch_options: "", restore: [], evidence: "backups" }), "Old Game");
    expect(step.kind === "confirm" && step.lines).toEqual([
      "Found backups an older version of the plugin made.",
      "In /games/Old Game:",
      "Remove: dxgi.dll, OptiScaler.ini",
      'No backup exists for nvapi64.dll. If the game shipped them, restore them with Steam\'s "Verify integrity of game files".',
      "The plugin's launch options are cleared.",
    ]);
    const kept = unpatchStep(reset({ launch_options: null, evidence: "leftovers" }), "Old Game");
    expect(kept.kind === "confirm" && kept.lines).toEqual([
      "Found files only early versions of the plugin left behind.",
      "In /games/Old Game:",
      "Restore from backup: libxess.dll",
      "Remove: dxgi.dll, OptiScaler.ini",
    ]);
  });
});

describe("unpatch wording", () => {
  it("names a game by its name and a directory by its path", () => {
    expect(unpatchSubject({ kind: "game", name: "Old Game" })).toBe("Old Game");
    expect(unpatchSubject({ kind: "directory", path: "/games/Old" })).toBe("/games/Old");
  });

  it("reports the backend's words, or a fallback", () => {
    expect(unpatchOutcome(undefined)).toBe("The plugin backend did not answer.");
    expect(unpatchOutcome({ status: "success", message: "Unpatched Old Game." })).toBe("Unpatched Old Game.");
    expect(unpatchOutcome({ status: "success" })).toBe("Unpatched.");
    expect(unpatchOutcome({ status: "error", message: "Close the game first" })).toBe("Close the game first");
  });
});
