import { ButtonItem, ConfirmModal, PanelSectionRow, showModal } from "@decky/ui";
import { useEffect } from "react";
import { ResetTarget, useStockReset } from "../hooks/useStockReset";
import { resetButtonLabel } from "../presentation/stockReset";

/** Returns one game an earlier plugin version patched to how it shipped — after showing what that does. */
export function ResetToStock({ target, onDone }: { target: ResetTarget; onDone: () => void }) {
  const { busy, confirmation, onPreview, onConfirm, onCancel } = useStockReset(target, onDone);

  useEffect(() => {
    if (confirmation?.kind !== "confirm") return;
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
        onOK={() => void onConfirm()}
        onCancel={onCancel}
      />
    );
  }, [confirmation]);

  return (
    <PanelSectionRow>
      <ButtonItem layout="below" disabled={busy} onClick={() => void onPreview()}>
        {resetButtonLabel(busy)}
      </ButtonItem>
    </PanelSectionRow>
  );
}
