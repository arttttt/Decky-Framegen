import { ConfirmModal, showModal } from "@decky/ui";
import { useEffect } from "react";
import type { UnpatchStep } from "../presentation/unpatch";

/** Shows the reset confirmation while there is one; renders nothing in the panel itself. */
export function UnpatchConfirmation({
  confirmation,
  onConfirm,
  onCancel,
}: {
  confirmation: Extract<UnpatchStep, { kind: "confirm" }> | null;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  useEffect(() => {
    if (!confirmation) return;
    showModal(
      <ConfirmModal
        strTitle={confirmation.title}
        strDescription={
          <>
            {confirmation.lines.map((line) => (
              <div key={line}>{line}</div>
            ))}
          </>
        }
        strOKButtonText={confirmation.okLabel}
        onOK={onConfirm}
        onCancel={onCancel}
      />
    );
  }, [confirmation]);
  return null;
}
