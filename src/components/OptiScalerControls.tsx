import { useState } from "react";
import { DropdownItem, Field, PanelSection, PanelSectionRow, ToggleField } from "@decky/ui";
import { OptiScalerHeader } from "./OptiScalerHeader";
import { ClipboardCommands } from "./ClipboardCommands";
import { InstructionCard } from "./InstructionCard";
import { OptiScalerWiki } from "./OptiScalerWiki";
import { ManualPatchControls } from "./CustomPathOverride";
import { SteamGamePatcher } from "./SteamGamePatcher";
import type { InstalledLibrary } from "../api";
import { libraryReady, patchChoice } from "../presentation/patching";
import { patchReady, proxyDllView } from "../presentation/launch";
import { useLaunchSetup } from "../hooks/useLaunchSetup";

interface OptiScalerControlsProps {
  library: InstalledLibrary | null;
}

export function OptiScalerControls({ library }: OptiScalerControlsProps) {
  const [advancedModeEnabled, setAdvancedModeEnabled] = useState(false);
  const [manualClipboardModeEnabled, setManualClipboardModeEnabled] = useState(false);
  const [pickedDll, setPickedDll] = useState<string | null>(null);
  const [picked, setPicked] = useState<string | null>(null);
  const pathExists = libraryReady(library);
  const choice = patchChoice(library, picked);
  const launch = proxyDllView(useLaunchSetup(), pickedDll);
  const dllName = launch.selected ?? "";
  const ready = patchReady(choice.ready, launch);

  return (
    <PanelSection>
      <OptiScalerHeader pathExists={pathExists} />

      {choice.ready ? (
        <PanelSectionRow>
          <DropdownItem
            layout="below"
            label="OptiScaler version"
            menuLabel="OptiScaler version"
            selectedOption={choice.versionId}
            rgOptions={choice.versionOptions}
            onChange={(option) => setPicked(String(option.data))}
          />
        </PanelSectionRow>
      ) : (
        <PanelSectionRow>
          <Field label="OptiScaler" description={choice.versionHint} focusable={true} highlightOnFocus={true} />
        </PanelSectionRow>
      )}

      <PanelSectionRow>
        <DropdownItem
          layout="below"
          label="Proxy DLL name"
          description={launch.hint}
          menuLabel="Proxy DLL name"
          selectedOption={launch.selected}
          rgOptions={launch.options}
          onChange={(option) => setPickedDll(String(option.data))}
        />
      </PanelSectionRow>

      <SteamGamePatcher dllName={dllName} patchWith={choice.patchWith} ready={ready} />

      <ClipboardCommands pathExists={pathExists} launch={launch} />

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
          launch={launch}
          manualModeEnabled
          showLaunchOptions={false}
        />
      ) : null}

      <ManualPatchControls
        isAvailable={true}
        ready={ready}
        onManualModeChange={setAdvancedModeEnabled}
        dllName={dllName}
        launchOptions={launch.launchOptions}
        patchWith={choice.patchWith}
      />

      {!advancedModeEnabled && (
        <InstructionCard pathExists={pathExists} />
      )}
      <OptiScalerWiki pathExists={pathExists} />
    </PanelSection>
  );
}
