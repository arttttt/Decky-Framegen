import { ButtonItem, PanelSectionRow } from "@decky/ui";
import { FaCheck, FaClipboard } from "react-icons/fa";
import { useClipboardCopy } from "../hooks/useClipboardCopy";
import type { CopyConfirmation } from "../presentation/launch";
import { Confirmation } from "./Confirmation";

interface SmartClipboardButtonProps {
  command: string;
  buttonText: string;
  /** Asked before copying, when the command needs a second thought. */
  confirmation?: CopyConfirmation;
}

const PULSE = { animation: "deckyscaler-pulse 1s ease-in-out infinite", opacity: 0.7 };

export function SmartClipboardButton({ command, buttonText, confirmation }: SmartClipboardButtonProps) {
  const copy = useClipboardCopy(command, buttonText, confirmation);
  const { view } = copy;
  const Icon = view.icon === "check" ? FaCheck : FaClipboard;
  return (
    <PanelSectionRow>
      <ButtonItem layout="below" onClick={copy.onClick} disabled={!view.enabled}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <Icon style={{ ...(view.pulsing ? PULSE : {}), ...(view.color ? { color: view.color } : {}) }} />
          <div style={view.color ? { color: view.color, fontWeight: "bold" } : undefined}>{view.label}</div>
        </div>
      </ButtonItem>
      <Confirmation confirmation={copy.confirmation} onConfirm={copy.onConfirm} onCancel={copy.onCancel} />
      <style>{`
        @keyframes deckyscaler-pulse {
          0% { opacity: 0.7; }
          50% { opacity: 1; }
          100% { opacity: 0.7; }
        }
      `}</style>
    </PanelSectionRow>
  );
}
