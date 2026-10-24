import { ButtonItem, DropdownItem, Field, PanelSection, PanelSectionRow } from "@decky/ui";
import { useDeveloperSection } from "../hooks/useDeveloperSection";

/** Shown only in development builds: switch to main's latest build or a pull request's. */
export function DeveloperSection() {
  const { view, onCheck, onSelect, onInstall } = useDeveloperSection();
  if (!view.visible) return null;

  return (
    <PanelSection title="Developer">
      <PanelSectionRow>
        <Field label={view.running} />
      </PanelSectionRow>
      <PanelSectionRow>
        <ButtonItem layout="below" onClick={onCheck} disabled={!view.checkEnabled}>
          {view.checkLabel}
        </ButtonItem>
      </PanelSectionRow>
      {view.pickerVisible && (
        <PanelSectionRow>
          <DropdownItem
            layout="below"
            label="Build"
            description={view.details ?? undefined}
            rgOptions={view.options}
            selectedOption={view.selectedChannel}
            onChange={(option) => onSelect(String(option.data))}
          />
        </PanelSectionRow>
      )}
      {view.pickerVisible && (
        <PanelSectionRow>
          <ButtonItem layout="below" onClick={onInstall} disabled={!view.installEnabled}>
            {view.installLabel}
          </ButtonItem>
        </PanelSectionRow>
      )}
      {view.message && (
        <PanelSectionRow>
          <Field description={view.message} />
        </PanelSectionRow>
      )}
    </PanelSection>
  );
}
