import { ButtonItem, DialogBody, PanelSection, PanelSectionRow, useParams } from "@decky/ui";
import { openSettingsPage } from "../api/framegenPage";
import { useGamePatch } from "../hooks/useGamePatch";
import { useInstalledLibrary } from "../hooks/useInstalledLibrary";
import { usePatchPickers } from "../hooks/usePatchPickers";
import { gamePageTitle } from "../presentation/patching";
import { GamePatchCard } from "./GamePatchCard";
import { PatchPickers } from "./PatchPickers";

/** A Steam game's page in the plugin: its patch with the version and proxy to use, and its settings. */
export function GamePage() {
  const { appid } = useParams<{ appid: string }>();
  const { library } = useInstalledLibrary();
  const pickers = usePatchPickers(library);
  const patch = useGamePatch(appid, (status) => pickers.forGame(status).patchWith);
  const picked = pickers.forGame(patch.status);

  return (
    <DialogBody>
      <PanelSection title={gamePageTitle(patch.status)}>
        <PatchPickers pickers={pickers} picked={picked} />
        <GamePatchCard patch={patch} />
        <PanelSectionRow>
          <ButtonItem layout="below" onClick={() => openSettingsPage(appid)}>
            OptiScaler settings
          </ButtonItem>
        </PanelSectionRow>
      </PanelSection>
    </DialogBody>
  );
}
