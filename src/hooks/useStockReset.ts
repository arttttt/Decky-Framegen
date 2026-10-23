import { useState } from "react";
import { toaster } from "@decky/api";
import { previewResetDirectory, previewResetGame, resetDirectory, resetGame, ResetPreview } from "../api";
import { getAppLaunchOptions, setAppLaunchOptions } from "../api/steamClient";
import { ResetConfirmation, resetConfirmation, resetOutcome, resetSubject } from "../presentation/stockReset";
import { safeAsyncOperation } from "../utils";

/** One game the user picked: a Steam game, or a directory patched through the launch wrapper. */
export type ResetTarget = { kind: "game"; appid: string; name: string } | { kind: "directory"; path: string };

const currentLaunchOptions = async (appid: string): Promise<string> => {
  try {
    return await getAppLaunchOptions(Number(appid));
  } catch {
    return "";
  }
};

/** Preview, then reset only after the user confirms; every word comes from the presentation object. */
export const useStockReset = (target: ResetTarget, onDone: () => void) => {
  const [busy, setBusy] = useState(false);
  const [confirmation, setConfirmation] = useState<ResetConfirmation | null>(null);

  const subject = resetSubject(target);

  const onPreview = async () => {
    setBusy(true);
    const preview = await safeAsyncOperation<ResetPreview>(
      async () =>
        target.kind === "game"
          ? previewResetGame(target.appid, await currentLaunchOptions(target.appid))
          : previewResetDirectory(target.path),
      "StockReset -> preview"
    );
    setBusy(false);
    const shown = preview ? resetConfirmation(preview, subject) : null;
    if (!shown || shown.kind === "refused") {
      toaster.toast({ title: "Decky Framegen", body: shown?.message ?? resetOutcome(undefined) });
      return;
    }
    setConfirmation(shown);
  };

  const onConfirm = async () => {
    setConfirmation(null);
    setBusy(true);
    const result = await safeAsyncOperation<ResetPreview>(
      async () =>
        target.kind === "game"
          ? resetGame(target.appid, await currentLaunchOptions(target.appid))
          : resetDirectory(target.path),
      "StockReset -> reset"
    );
    if (target.kind === "game" && result?.status === "success" && result.launch_options !== null) {
      setAppLaunchOptions(Number(target.appid), result.launch_options);
    }
    setBusy(false);
    toaster.toast({ title: "Decky Framegen", body: resetOutcome(result) });
    onDone();
  };

  return { busy, confirmation, onPreview, onConfirm, onCancel: () => setConfirmation(null) };
};
