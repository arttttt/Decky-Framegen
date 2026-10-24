import { useState } from "react";
import { DropdownItem, Field, PanelSection, PanelSectionRow, ToggleField } from "@decky/ui";
import { PROXY_DLL_OPTIONS, DEFAULT_PROXY_DLL } from "../utils/constants";
import { OptiScalerHeader } from "./OptiScalerHeader";
import { ClipboardCommands } from "./ClipboardCommands";
import { InstructionCard } from "./InstructionCard";
import { OptiScalerWiki } from "./OptiScalerWiki";
import { ManualPatchControls } from "./CustomPathOverride";
import { SteamGamePatcher } from "./SteamGamePatcher";
import type { InstalledLibrary } from "../api";
import { libraryReady, patchChoice } from "../presentation/patching";
import { useIsDevBuild } from "../hooks/useIsDevBuild";

interface OptiScalerControlsProps {
  library: InstalledLibrary | null;
}

export function OptiScalerControls({ library }: OptiScalerControlsProps) {
  const [advancedModeEnabled, setAdvancedModeEnabled] = useState(false);
  const [manualClipboardModeEnabled, setManualClipboardModeEnabled] = useState(false);
  const [dllName, setDllName] = useState<string>(DEFAULT_PROXY_DLL);
  const [picked, setPicked] = useState<string | null>(null);
  const pathExists = libraryReady(library);
  const [link, setLink] = useState(false);
  const devBuild = useIsDevBuild();
  const choice = patchChoice(library, picked, { offered: devBuild, on: link });

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

      {choice.linkToggleVisible && (
        <PanelSectionRow>
          <ToggleField
            label="Link instead of copy (experimental)"
            description="Place symlinks to the library version in the game instead of copies."
            checked={link}
            onChange={setLink}
          />
        </PanelSectionRow>
      )}

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

      <SteamGamePatcher dllName={dllName} patchWith={choice.patchWith} ready={choice.ready} />

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
        ready={choice.ready}
        onManualModeChange={setAdvancedModeEnabled}
        dllName={dllName}
        patchWith={choice.patchWith}
      />

      {!advancedModeEnabled && (
        <InstructionCard pathExists={pathExists} />
      )}
      <OptiScalerWiki pathExists={pathExists} />
    </PanelSection>
  );
}
