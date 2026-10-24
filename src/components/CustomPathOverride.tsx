import { ButtonItem, Field, PanelSectionRow } from "@decky/ui";
import { useManualPatch } from "../hooks/useManualPatch";
import { SmartClipboardButton } from "./SmartClipboardButton";
import { UnpatchConfirmation } from "./UnpatchConfirmation";

interface ManualPatchControlsProps {
  ready: boolean;
  dllName: string;
  /** What to copy as the game's launch options; built by the backend. */
  launchOptions: string | null;
  patchWith: string;
}

const PATH_STYLE = {
  fontFamily: "monospace",
  backgroundColor: "rgba(255, 255, 255, 0.05)",
  border: "1px solid rgba(255, 255, 255, 0.1)",
  borderRadius: "4px",
  padding: "6px 8px",
  width: "100%",
  boxSizing: "border-box",
  whiteSpace: "pre-wrap",
  wordBreak: "break-word",
} as const;

/** Patch a directory picked by hand: a game outside Steam, or one the Steam section can't find. */
export const ManualPatchControls = ({ ready, dllName, launchOptions, patchWith }: ManualPatchControlsProps) => {
  const { view, selectedPath, pickerError, onPick, onPatch, unpatch } = useManualPatch({ ready, dllName, patchWith });
  return (
    <>
      {launchOptions && <SmartClipboardButton command={launchOptions} buttonText="Manual launch cmd" />}
      <PanelSectionRow>
        <ButtonItem
          layout="below"
          onClick={() => void onPick()}
          description="Choose the game's installation directory (where the EXE lives)."
        >
          Select directory
        </ButtonItem>
      </PanelSectionRow>

      {pickerError && (
        <PanelSectionRow>
          <Field label="Picker error" description={pickerError} />
        </PanelSectionRow>
      )}

      {selectedPath && (
        <>
          <PanelSectionRow>
            <Field label="Target directory" description="OptiScaler is placed here as links into the library.">
              <div style={PATH_STYLE}>{selectedPath}</div>
            </Field>
          </PanelSectionRow>
          <PanelSectionRow>
            <ButtonItem layout="below" disabled={!view.patch.enabled} onClick={() => void onPatch()}>
              {view.patch.label}
            </ButtonItem>
          </PanelSectionRow>
          <PanelSectionRow>
            <ButtonItem layout="below" disabled={!view.unpatch.enabled} onClick={unpatch.onUnpatch}>
              {view.unpatch.label}
            </ButtonItem>
          </PanelSectionRow>
          <UnpatchConfirmation confirmation={unpatch.confirmation} onConfirm={unpatch.onConfirm} onCancel={unpatch.onCancel} />
        </>
      )}

      {view.result && (
        <PanelSectionRow>
          <Field label={view.result.label}>{view.result.text}</Field>
        </PanelSectionRow>
      )}
    </>
  );
};
