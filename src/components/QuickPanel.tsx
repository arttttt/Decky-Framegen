import { ButtonItem, DropdownItem, Field, PanelSection, PanelSectionRow } from "@decky/ui";
import { openFramegenPage, openGamePage } from "../api/framegenPage";
import { useGamePatch } from "../hooks/useGamePatch";
import { useInstalledLibrary } from "../hooks/useInstalledLibrary";
import { useLaunchSetup } from "../hooks/useLaunchSetup";
import { usePluginUpdates } from "../hooks/usePluginUpdates";
import { useSteamGames } from "../hooks/useSteamGames";
import { proxyDllView } from "../presentation/launch";
import { librarySummary } from "../presentation/library";
import { gamePickerView, libraryReady, quickPatchWith } from "../presentation/patching";
import { updateAvailableLine } from "../presentation/updates";
import { GamePatchCard } from "./GamePatchCard";

/** The Quick Access panel: a game's patch at a glance. Everything else is on the plugin's pages. */
export function QuickPanel() {
  const { library } = useInstalledLibrary();
  const launch = proxyDllView(useLaunchSetup(), null);
  const games = useSteamGames();
  const patch = useGamePatch(games.selectedAppId || null, (status) =>
    quickPatchWith(status, launch, libraryReady(library) === true),
  );
  const picker = gamePickerView(games.games, games.loading);
  const update = updateAvailableLine(usePluginUpdates().check);

  return (
    <PanelSection>
      <PanelSectionRow>
        <DropdownItem
          layout="below"
          label="Steam game"
          menuLabel="Select a Steam game"
          strDefaultLabel={picker.placeholder}
          disabled={!picker.enabled}
          selectedOption={games.selectedAppId}
          rgOptions={picker.options}
          onChange={(option) => games.select(String(option.data))}
        />
      </PanelSectionRow>
      {games.selected && <GamePatchCard patch={patch} />}
      {games.selected && (
        <PanelSectionRow>
          <ButtonItem layout="below" onClick={() => openGamePage(games.selectedAppId)}>
            Open game page
          </ButtonItem>
        </PanelSectionRow>
      )}
      <PanelSectionRow>
        <Field label="OptiScaler" description={librarySummary(library)} />
      </PanelSectionRow>
      {update && (
        <PanelSectionRow>
          <Field label="Update" description={update} />
        </PanelSectionRow>
      )}
      <PanelSectionRow>
        <ButtonItem layout="below" onClick={openFramegenPage}>
          Open Framegen
        </ButtonItem>
      </PanelSectionRow>
    </PanelSection>
  );
}
