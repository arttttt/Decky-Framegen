import type { ResetPreview } from "../api";

/** What the confirmation shows before a reset; the modal maps it and decides nothing. */
export type ResetConfirmation =
  | { kind: "refused"; message: string }
  | { kind: "confirm"; title: string; lines: string[]; okLabel: string };

const EVIDENCE: Record<"marker" | "backups" | "leftovers", string> = {
  marker: "Found the plugin's patch record.",
  backups: "Found backups an earlier plugin version made.",
  leftovers: "Found files only early plugin versions left behind.",
};

const listed = (label: string, names: string[]): string[] => (names.length ? [`${label}: ${names.join(", ")}`] : []);

export const resetConfirmation = (preview: ResetPreview, subject: string): ResetConfirmation => {
  if (preview.status !== "success") return { kind: "refused", message: preview.message };
  return {
    kind: "confirm",
    title: `Reset ${subject} to stock?`,
    lines: [
      EVIDENCE[preview.evidence],
      `In ${preview.target_dir}:`,
      ...listed("Restore from backup", preview.restore),
      ...listed("Remove", preview.remove),
      ...(preview.unrecoverable.length
        ? [
            `No backup exists for ${preview.unrecoverable.join(", ")}. If the game shipped them, ` +
              `restore them with Steam's "Verify integrity of game files".`,
          ]
        : []),
      ...(preview.launch_options === null
        ? []
        : [
            preview.launch_options
              ? `Launch options become: ${preview.launch_options}`
              : "The plugin's launch options are cleared.",
          ]),
    ],
    okLabel: "Reset",
  };
};

export const resetButtonLabel = (busy: boolean): string => (busy ? "Working…" : "Reset to stock…");

/** How the confirmation names what is reset: the game's name, or the directory. */
export const resetSubject = (target: { kind: "game"; name: string } | { kind: "directory"; path: string }): string =>
  target.kind === "game" ? target.name : target.path;

export const resetOutcome = (result: ResetPreview | undefined): string => {
  if (!result) return "The plugin backend did not answer.";
  if (result.status !== "success") return result.message;
  return result.message ?? "Reset to stock.";
};
