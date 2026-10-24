import type { UnpatchPreview, UnpatchResult } from "../api";

/**
 * The step Unpatch takes after asking the backend: undo the patch record right away, or, for a
 * patch Decky Framegen made, show what a reset changes and wait for the user to confirm.
 */
export type UnpatchStep =
  | { kind: "refused"; message: string }
  | { kind: "now" }
  | { kind: "confirm"; title: string; lines: string[]; okLabel: string };

const EVIDENCE: Record<"marker" | "backups" | "leftovers", string> = {
  marker: "Decky Framegen patched this game.",
  backups: "Found backups Decky Framegen made.",
  leftovers: "Found files only early versions of Decky Framegen left behind.",
};

const listed = (label: string, names: string[]): string[] => (names.length ? [`${label}: ${names.join(", ")}`] : []);

export const unpatchStep = (preview: UnpatchPreview, subject: string): UnpatchStep => {
  if (preview.status !== "success") return { kind: "refused", message: preview.message };
  if (preview.mode === "record") return { kind: "now" };
  return {
    kind: "confirm",
    title: `Unpatch ${subject}?`,
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
    okLabel: "Unpatch",
  };
};

/** How the confirmation names what is unpatched: the game's name, or the directory. */
export const unpatchSubject = (target: { kind: "game"; name: string } | { kind: "directory"; path: string }): string =>
  target.kind === "game" ? target.name : target.path;

export const unpatchOutcome = (result: UnpatchResult | undefined): string => {
  if (!result) return "The plugin backend did not answer.";
  return result.message ?? (result.status === "success" ? "Unpatched." : "Unpatch failed.");
};
