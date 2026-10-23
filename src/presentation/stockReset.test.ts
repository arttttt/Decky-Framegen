import { describe, expect, it } from "vitest";
import type { ResetPreview } from "../api";
import { resetButtonLabel, resetConfirmation, resetOutcome, resetSubject } from "./stockReset";

const preview = (overrides: Partial<Extract<ResetPreview, { status: "success" }>> = {}): ResetPreview => ({
  status: "success",
  target_dir: "/games/Old Game",
  evidence: "marker",
  remove: ["dxgi.dll", "OptiScaler.ini"],
  restore: ["libxess.dll"],
  unrecoverable: [],
  launch_options: "mangohud %command%",
  ...overrides,
});

describe("reset confirmation", () => {
  it("passes a refusal through without offering to reset", () => {
    expect(resetConfirmation({ status: "error", message: "No sign of Decky Framegen" }, "Old Game")).toEqual({
      kind: "refused",
      message: "No sign of Decky Framegen",
    });
  });

  it("says why, where, what is restored and removed, and the launch options afterwards", () => {
    const confirmation = resetConfirmation(preview(), "Old Game");

    expect(confirmation).toEqual({
      kind: "confirm",
      title: "Reset Old Game to stock?",
      lines: [
        "Found the plugin's patch record.",
        "In /games/Old Game:",
        "Restore from backup: libxess.dll",
        "Remove: dxgi.dll, OptiScaler.ini",
        "Launch options become: mangohud %command%",
      ],
      okLabel: "Reset",
    });
  });

  it("warns about removed files without a backup and points to Steam's integrity check", () => {
    const confirmation = resetConfirmation(preview({ unrecoverable: ["nvapi64.dll"], restore: [] }), "Old Game");

    expect(confirmation.kind === "confirm" && confirmation.lines).toEqual([
      "Found the plugin's patch record.",
      "In /games/Old Game:",
      "Remove: dxgi.dll, OptiScaler.ini",
      'No backup exists for nvapi64.dll. If the game shipped them, restore them with Steam\'s "Verify integrity of game files".',
      "Launch options become: mangohud %command%",
    ]);
  });

  it("says when launch options are cleared and stays silent when they are left alone", () => {
    const cleared = resetConfirmation(preview({ launch_options: "" }), "Old Game");
    const untouched = resetConfirmation(preview({ launch_options: null, evidence: "backups" }), "/games/Old Game");

    expect(cleared.kind === "confirm" && cleared.lines.at(-1)).toBe("The plugin's launch options are cleared.");
    expect(untouched.kind === "confirm" && untouched.lines).toEqual([
      "Found backups an earlier plugin version made.",
      "In /games/Old Game:",
      "Restore from backup: libxess.dll",
      "Remove: dxgi.dll, OptiScaler.ini",
    ]);
  });
});

describe("reset outcome", () => {
  it("reports the backend's words, or that it did not answer", () => {
    expect(resetOutcome(preview({ message: "Old Game is back to how it shipped." }))).toBe(
      "Old Game is back to how it shipped."
    );
    expect(resetOutcome({ status: "error", message: "Close the game before resetting it." })).toBe(
      "Close the game before resetting it."
    );
    expect(resetOutcome(undefined)).toBe("The plugin backend did not answer.");
  });
});

describe("reset button and subject", () => {
  it("names the game, or the directory for a launch-wrapper patch, and shows when it works", () => {
    expect(resetSubject({ kind: "game", name: "Old Game" })).toBe("Old Game");
    expect(resetSubject({ kind: "directory", path: "/games/Old Game" })).toBe("/games/Old Game");
    expect(resetButtonLabel(false)).toBe("Reset to stock…");
    expect(resetButtonLabel(true)).toBe("Working…");
  });
});
