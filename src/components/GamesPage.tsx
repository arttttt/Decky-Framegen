import { ButtonItem, Field, PanelSection, PanelSectionRow } from "@decky/ui";
import { openGamePage } from "../api/framegenPage";
import { usePatchedGames } from "../hooks/usePatchedGames";
import { useUnpatch } from "../hooks/useUnpatch";
import type { GameRowView } from "../presentation/games";
import { Confirmation } from "./Confirmation";

const describe = (lines: string[]) => <span style={{ whiteSpace: "pre-line" }}>{lines.join("\n")}</span>;

/** A Steam game: its page patches, unpatches and sets it up. */
function SteamGameRow({ row, appid }: { row: GameRowView; appid: string }) {
  return (
    <PanelSectionRow>
      <ButtonItem label={row.title} description={describe(row.lines)} onClick={() => openGamePage(appid)}>
        {row.action.label}
      </ButtonItem>
    </PanelSectionRow>
  );
}

/** A directory patched by path: it has no game page, so it is unpatched from its row. */
function DirectoryRow({ row, directory, onChanged }: { row: GameRowView; directory: string; onChanged: () => void }) {
  const unpatch = useUnpatch({ kind: "directory", path: directory }, onChanged);
  return (
    <PanelSectionRow>
      <ButtonItem label={row.title} description={describe(row.lines)} disabled={unpatch.busy} onClick={unpatch.onUnpatch}>
        {row.action.label}
      </ButtonItem>
      <Confirmation confirmation={unpatch.confirmation} onConfirm={unpatch.onConfirm} onCancel={unpatch.onCancel} />
    </PanelSectionRow>
  );
}

/** Every game the plugin patched: a Steam game opens its page, a directory is unpatched in place. */
export function GamesPage() {
  const { view, reload } = usePatchedGames();
  return (
    <PanelSection>
      {view.kind === "message" ? (
        <PanelSectionRow>
          <Field label={view.message} />
        </PanelSectionRow>
      ) : (
        view.rows.map((row) =>
          row.action.kind === "open" ? (
            <SteamGameRow key={row.key} row={row} appid={row.action.appid} />
          ) : (
            <DirectoryRow key={row.key} row={row} directory={row.action.directory} onChanged={() => void reload()} />
          ),
        )
      )}
    </PanelSection>
  );
}
