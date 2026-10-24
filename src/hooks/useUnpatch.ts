import { useState } from "react";
import { notify } from "../utils/notify";
import {
  UnpatchPreview,
  UnpatchResult,
  previewUnpatchDirectory,
  previewUnpatchGame,
  runManualUnpatch,
  unpatchGame,
} from "../api";
import { getAppLaunchOptions, setAppLaunchOptions } from "../api/steamClient";
import { UnpatchStep, unpatchOutcome, unpatchStep, unpatchSubject } from "../presentation/unpatch";
import { safeAsyncOperation } from "../utils";

/** One game the user picked: a Steam game, or a directory patched by path or through the launch wrapper. */
export type UnpatchTarget = { kind: "game"; appid: string; name: string } | { kind: "directory"; path: string };

const currentLaunchOptions = async (appid: string): Promise<string> => {
  try {
    return await getAppLaunchOptions(Number(appid));
  } catch {
    return "";
  }
};

/** Unpatch: by the patch record at once, or a reset only after the user confirms what it changes. */
export const useUnpatch = (target: UnpatchTarget | null, onDone: () => void) => {
  const [busy, setBusy] = useState(false);
  const [confirmation, setConfirmation] = useState<Extract<UnpatchStep, { kind: "confirm" }> | null>(null);

  const run = async (confirmedReset: boolean) => {
    if (!target) return;
    setConfirmation(null);
    setBusy(true);
    const result = await safeAsyncOperation<UnpatchResult>(
      async () =>
        target.kind === "game"
          ? unpatchGame(target.appid, await currentLaunchOptions(target.appid), confirmedReset)
          : runManualUnpatch(target.path, confirmedReset),
      "Unpatch -> unpatch"
    );
    if (target.kind === "game" && result?.status === "success" && typeof result.launch_options === "string") {
      setAppLaunchOptions(Number(target.appid), result.launch_options);
    }
    setBusy(false);
    notify(unpatchOutcome(result));
    onDone();
  };

  const onUnpatch = async () => {
    if (!target || busy) return;
    setBusy(true);
    const preview = await safeAsyncOperation<UnpatchPreview>(
      async () =>
        target.kind === "game"
          ? previewUnpatchGame(target.appid, await currentLaunchOptions(target.appid))
          : previewUnpatchDirectory(target.path),
      "Unpatch -> preview"
    );
    setBusy(false);
    const step: UnpatchStep = preview
      ? unpatchStep(preview, unpatchSubject(target))
      : { kind: "refused", message: unpatchOutcome(undefined) };
    if (step.kind === "refused") notify(step.message);
    else if (step.kind === "now") await run(false);
    else setConfirmation(step);
  };

  return {
    busy,
    confirmation,
    onUnpatch: () => void onUnpatch(),
    onConfirm: () => void run(true),
    onCancel: () => setConfirmation(null),
  };
};
