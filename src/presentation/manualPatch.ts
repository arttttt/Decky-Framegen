import { patchButton } from "./patching";

/** Where the backend says the directory picker may start: home, and the first Steam library's games. */
export type PathDefaults = { home: string; steam_common?: string };

/** Where the directory picker tries to open, in order: the directory picked last, then the Steam
 *  library's games, then home. Unknown ones are left out. */
export const pickerStartPaths = (selected: string | null, defaults: PathDefaults | null): string[] =>
  [selected, defaults?.steam_common, defaults?.home].filter((path): path is string => Boolean(path));

/** The last patch of a picked directory, as the backend answered it. */
export type ManualPatchResult = { status: string; message?: string; output?: string };

export type ManualPatchView = {
  patch: { label: string; enabled: boolean };
  unpatch: { label: string; enabled: boolean };
  /** The last patch's outcome; a failure says why. */
  result: { label: string; text: string | null } | null;
};

/** What patching a directory by hand shows: Patch needs a version, neither runs while either does. */
export const manualPatchView = ({
  ready,
  busy,
  result,
}: {
  ready: boolean;
  busy: "patch" | "unpatch" | null;
  result: ManualPatchResult | null;
}): ManualPatchView => {
  const patch = patchButton(ready, busy === "patch" ? "Patching..." : "Patch directory");
  return {
    patch: { label: patch.label, enabled: patch.enabled && busy === null },
    unpatch: { label: busy === "unpatch" ? "Unpatching..." : "Unpatch directory", enabled: busy === null },
    result:
      result === null
        ? null
        : result.status === "success"
          ? { label: "Game patched", text: null }
          : { label: "Patch failed", text: result.message || result.output || "No reason given." },
  };
};
