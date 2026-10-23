import { useState } from "react";
import { DropdownItem, Field, PanelSection, PanelSectionRow, ToggleField } from "@decky/ui";
import { PROXY_DLL_OPTIONS, DEFAULT_PROXY_DLL } from "../utils/constants";
import { OptiScalerHeader } from "./OptiScalerHeader";
import { ClipboardCommands } from "./ClipboardCommands";
import { InstructionCard } from "./InstructionCard";
import { OptiScalerWiki } from "./OptiScalerWiki";
import { ManualPatchControls } from "./CustomPathOverride";
import { SteamGamePatcher } from "./SteamGamePatcher";
import { libraryLine } from "../presentation/patching";

interface FgmodInfo {
  exists: boolean;
  version?: string | null;
}

interface OptiScalerControlsProps {
  pathExists: boolean | null;
  fgmodInfo?: FgmodInfo | null;
}

export function OptiScalerControls({ pathExists, fgmodInfo }: OptiScalerControlsProps) {
  const [advancedModeEnabled, setAdvancedModeEnabled] = useState(false);
  const [manualClipboardModeEnabled, setManualClipboardModeEnabled] = useState(false);
  const [dllName, setDllName] = useState<string>(DEFAULT_PROXY_DLL);

  return (
    <PanelSection>
      <OptiScalerHeader pathExists={pathExists} />

      <PanelSectionRow>
        <Field label="OptiScaler" description={libraryLine(fgmodInfo ?? null)} focusable={true} highlightOnFocus={true} />
      </PanelSectionRow>

      <PanelSectionRow>
        <DropdownItem
          layout="below"
          label="Proxy DLL name"
          description={PROXY_DLL_OPTIONS.find((o) => o.value === dllName)?.hint}
          menuLabel="Proxy DLL name"
          selectedOption={dllName}
          rgOptions={PROXY_DLL_OPTIONS.map((o) => ({ data: o.value, label: o.label }))}
          onChange={(option) => setDllName(String(option.data))}
        />
      </PanelSectionRow>

      <SteamGamePatcher dllName={dllName} bundleInstalled={pathExists === true} />

      <ClipboardCommands pathExists={pathExists} dllName={dllName} />

      {pathExists === true && (
        <PanelSectionRow>
          <ToggleField
            label="Manual Mode"
            description="Show wrapper command clipboard buttons for patching and unpatching through ~/fgmod scripts."
            checked={manualClipboardModeEnabled}
            onChange={setManualClipboardModeEnabled}
          />
        </PanelSectionRow>
      )}

      {pathExists === true && manualClipboardModeEnabled ? (
        <ClipboardCommands
          pathExists={pathExists}
          dllName={dllName}
          manualModeEnabled
          showLaunchOptions={false}
        />
      ) : null}

      <ManualPatchControls
        isAvailable={true}
        bundleInstalled={pathExists === true}
        onManualModeChange={setAdvancedModeEnabled}
        dllName={dllName}
      />

      {!advancedModeEnabled && (
        <InstructionCard pathExists={pathExists} />
      )}
      <OptiScalerWiki pathExists={pathExists} />
    </PanelSection>
  );
}
