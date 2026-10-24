import { ConfirmModal, showModal } from "@decky/ui";
import { useEffect } from "react";

/** A question a view model asks before an action: its lines, and an alert has only OK. */
export type ConfirmationView = { title: string; lines: string[]; okLabel: string; alert?: boolean };

/** Shows the confirmation while there is one; renders nothing in the page itself. */
export function Confirmation({
  confirmation,
  onConfirm,
  onCancel,
}: {
  confirmation: ConfirmationView | null;
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
        bAlertDialog={confirmation.alert}
        onOK={onConfirm}
        onCancel={onCancel}
      />
    );
  }, [confirmation]);
  return null;
}
