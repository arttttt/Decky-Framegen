import { PanelSection, SidebarNavigation } from "@decky/ui";
import { useInstalledLibrary } from "../hooks/useInstalledLibrary";
import { useIsDevBuild } from "../hooks/useIsDevBuild";
import { usePatchPickers } from "../hooks/usePatchPickers";
import { ClipboardCommands } from "./ClipboardCommands";
import { ManualPatchControls } from "./CustomPathOverride";
import { DeveloperSection } from "./DeveloperSection";
import { LibrarySection } from "./LibrarySection";
import { OptiScalerWiki } from "./OptiScalerWiki";
import { PatchPickers } from "./PatchPickers";

/** Patching by hand: a directory, the wrapper's commands, launch options to paste, and the wiki. */
function AdvancedPage() {
  const { library } = useInstalledLibrary();
  const pickers = usePatchPickers(library);
  return (
    <PanelSection>
      <PatchPickers pickers={pickers} />
      <ManualPatchControls
        ready={pickers.ready}
        dllName={pickers.dllName}
        launchOptions={pickers.launch.launchOptions}
        patchWith={pickers.choice.patchWith}
      />
      <ClipboardCommands launch={pickers.launch} manualModeEnabled />
      <OptiScalerWiki />
    </PanelSection>
  );
}

function OptiScalerPage() {
  const { library, reload } = useInstalledLibrary();
  return <LibrarySection library={library} onChanged={reload} />;
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
