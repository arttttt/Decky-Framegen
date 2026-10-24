import { useEffect, useState } from "react";
import { toaster } from "@decky/api";
import { COPIED_SHOWN_MS, COPY_FAILED, CopyConfirmation, CopyState, clipboardButtonView } from "../presentation/launch";
import { copyText } from "../utils/clipboard";

/** A copy button: asks first when there is a confirmation, copies, and shows it copied for a while. */
export const useClipboardCopy = (command: string, label: string, confirmation?: CopyConfirmation) => {
  const [state, setState] = useState<CopyState>("idle");
  const [asking, setAsking] = useState(false);

  useEffect(() => {
    if (state !== "copied") return undefined;
    const timer = window.setTimeout(() => setState("idle"), COPIED_SHOWN_MS);
    return () => window.clearTimeout(timer);
  }, [state]);

  const copy = async () => {
    setState("copying");
    const copied = await copyText(command);
    setState(copied ? "copied" : "idle");
    if (!copied) toaster.toast({ title: "Decky Framegen", body: COPY_FAILED });
  };

  const view = clipboardButtonView(state, label);
  const onClick = () => {
    if (!view.enabled) return;
    if (confirmation) setAsking(true);
    else void copy();
  };

  return {
    view,
    onClick,
    confirmation: asking && confirmation ? confirmation : null,
    onConfirm: () => {
      setAsking(false);
      void copy();
    },
    onCancel: () => setAsking(false),
  };
};
