import { ButtonItem, Field, PanelSectionRow } from "@decky/ui";
import type { GamePatch } from "../hooks/useGamePatch";
import type { SteamGameView } from "../presentation/patching";
import { UnpatchConfirmation } from "./UnpatchConfirmation";

const TONE_COLORS: Record<SteamGameView["status"]["tone"], string | undefined> = {
  neutral: undefined,
  warning: "#ffd866",
  good: "#3fb950",
};

/** A game's patch status, its FSR 4 state, and Patch and Unpatch. The lines are plain text the
 *  gamepad skips: only the buttons take focus. */
export function GamePatchCard({ patch }: { patch: GamePatch }) {
  const { view, unpatch } = patch;
  const color = TONE_COLORS[view.status.tone];
  return (
    <>
      <PanelSectionRow>
        <Field label="Patch status">
          {color ? <span style={{ color, fontWeight: 600 }}>{view.status.text}</span> : view.status.text}
        </Field>
      </PanelSectionRow>
      {view.versionLine && (
        <PanelSectionRow>
          <Field label="OptiScaler" description={view.versionLine} />
        </PanelSectionRow>
      )}
      {view.fsr4Line && (
        <PanelSectionRow>
          <Field label="FSR 4" description={view.fsr4Line} />
        </PanelSectionRow>
      )}
      <PanelSectionRow>
        <ButtonItem layout="below" disabled={!view.patch.enabled} onClick={() => void patch.onPatch()}>
          {view.patch.label}
        </ButtonItem>
      </PanelSectionRow>
      {view.unpatchVisible && (
        <PanelSectionRow>
          <ButtonItem layout="below" disabled={!view.unpatch.enabled} onClick={unpatch.onUnpatch}>
            {view.unpatch.label}
          </ButtonItem>
        </PanelSectionRow>
      )}
      <UnpatchConfirmation confirmation={unpatch.confirmation} onConfirm={unpatch.onConfirm} onCancel={unpatch.onCancel} />
      {patch.resultMessage && (
        <PanelSectionRow>
          <Field label="Result">
            {patch.resultMessage}
          </Field>
        </PanelSectionRow>
      )}
    </>
  );
}
