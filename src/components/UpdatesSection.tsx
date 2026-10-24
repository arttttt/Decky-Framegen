import { ButtonItem, Field, PanelSection, PanelSectionRow, ToggleField } from "@decky/ui";
import { useUpdatesSection } from "../hooks/useUpdatesSection";
import { Confirmation } from "./Confirmation";

/** The running build, the newest release, and Developer mode. */
export function UpdatesSection() {
  const updates = useUpdatesSection();
  const { view } = updates;
  return (
    <PanelSection title="Updates">
      <PanelSectionRow>
        <Field label={view.running} description={view.releaseLine ?? undefined} />
      </PanelSectionRow>
      <PanelSectionRow>
        <ButtonItem layout="below" disabled={!view.checkEnabled} onClick={updates.onCheck}>
          {view.checkLabel}
        </ButtonItem>
      </PanelSectionRow>
      {view.install.visible && (
        <PanelSectionRow>
          <ButtonItem layout="below" disabled={!view.install.enabled} onClick={updates.onInstall}>
            {view.install.label}
          </ButtonItem>
        </PanelSectionRow>
      )}
      {view.message && (
        <PanelSectionRow>
          <Field description={view.message} />
        </PanelSectionRow>
      )}
      {view.developerMode.visible && (
        <PanelSectionRow>
          <ToggleField
            label="Developer mode"
            description={view.developerMode.description}
            checked={view.developerMode.on}
            disabled={!view.developerMode.enabled}
            onChange={updates.onDeveloperMode}
          />
        </PanelSectionRow>
      )}
      <Confirmation confirmation={updates.confirmation} onConfirm={updates.onConfirm} onCancel={updates.onCancel} />
    </PanelSection>
  );
}
