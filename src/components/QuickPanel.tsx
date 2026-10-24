import { ButtonItem, Field, PanelSection, PanelSectionRow } from "@decky/ui";
import { openFramegenPage } from "../api/framegenPage";
import { useInstalledLibrary } from "../hooks/useInstalledLibrary";
import { usePatchPickers } from "../hooks/usePatchPickers";
import { librarySummary } from "../presentation/library";
import { PatchPickers } from "./PatchPickers";
import { SteamGamePatcher } from "./SteamGamePatcher";

/** The Quick Access panel: a game's patch at a glance. Everything else is on the plugin's page. */
export function QuickPanel() {
  const { library } = useInstalledLibrary();
  const pickers = usePatchPickers(library);

  return (
    <PanelSection>
      <SteamGamePatcher dllName={pickers.dllName} patchWith={pickers.choice.patchWith} ready={pickers.ready} />
      <PatchPickers pickers={pickers} />
      <PanelSectionRow>
        <Field label="OptiScaler" description={librarySummary(library)} focusable={true} highlightOnFocus={true} />
      </PanelSectionRow>
      <PanelSectionRow>
        <ButtonItem layout="below" onClick={openFramegenPage}>
          Open Framegen
        </ButtonItem>
      </PanelSectionRow>
    </PanelSection>
  );
}
