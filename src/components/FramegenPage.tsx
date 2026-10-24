import { ButtonItem, PanelSection, PanelSectionRow, SidebarNavigation } from "@decky/ui";
import { openSettingsPage } from "../api/framegenPage";
import { useInstalledLibrary } from "../hooks/useInstalledLibrary";
import { useIsDevBuild } from "../hooks/useIsDevBuild";
import { usePatchPickers } from "../hooks/usePatchPickers";
import { ClipboardCommands } from "./ClipboardCommands";
import { ManualPatchControls } from "./CustomPathOverride";
import { DeveloperSection } from "./DeveloperSection";
import { LibrarySection } from "./LibrarySection";
import { OptiScalerWiki } from "./OptiScalerWiki";
import { PatchPickers } from "./PatchPickers";
import { GLOBAL_SCOPE } from "../presentation/settings";

/** Patching by hand: a directory, the wrapper's commands, launch options to paste, and the wiki. */
function AdvancedPage() {
  const { library } = useInstalledLibrary();
  const pickers = usePatchPickers(library);
  const picked = pickers.forGame(null);
  return (
    <PanelSection>
      <PatchPickers pickers={pickers} picked={picked} />
      <ManualPatchControls
        ready={picked.patchWith.ready}
        dllName={picked.patchWith.dllName}
        launchOptions={picked.launch.launchOptions}
        patchWith={picked.patchWith.versionId}
      />
      <ClipboardCommands launch={picked.launch} manualModeEnabled />
      <OptiScalerWiki />
    </PanelSection>
  );
}

function OptiScalerPage() {
  const { library, reload } = useInstalledLibrary();
  return (
    <>
      <LibrarySection library={library} onChanged={reload} />
      <PanelSection title="Settings">
        <PanelSectionRow>
          <ButtonItem layout="below" description="The OptiScaler settings every game gets, unless it has its own." onClick={() => openSettingsPage(GLOBAL_SCOPE)}>
            Global settings
          </ButtonItem>
        </PanelSectionRow>
      </PanelSection>
    </>
  );
}

/** The plugin's full-screen page, opened from the Quick Access panel. */
export function FramegenPage() {
  const devBuild = useIsDevBuild();
  return (
    <SidebarNavigation
      title="Decky Framegen"
      showTitle
      pages={[
        { title: "OptiScaler", content: <OptiScalerPage /> },
        { title: "Advanced", content: <AdvancedPage /> },
        { title: "Developer", content: <DeveloperSection />, visible: devBuild },
      ]}
    />
  );
}
