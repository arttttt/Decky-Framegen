import { ButtonItem, Field, PanelSection, PanelSectionRow, showModal } from "@decky/ui";
import type { InstalledLibrary } from "../api";
import { librarySummary } from "../presentation/library";
import { DownloadVersionsModal } from "./DownloadVersionsModal";
import { ManageVersionsModal } from "./ManageVersionsModal";

/** The OptiScaler versions on the device, and the two dialogs that download and manage them. */
export function LibrarySection({ library, onChanged }: { library: InstalledLibrary | null; onChanged: () => void }) {
  return (
    <PanelSection title="OptiScaler versions">
      <PanelSectionRow>
        <Field description={librarySummary(library)} focusable={true} highlightOnFocus={true} />
      </PanelSectionRow>
      <PanelSectionRow>
        <ButtonItem layout="below" onClick={() => showModal(<DownloadVersionsModal onChanged={onChanged} />)}>
          Download versions…
        </ButtonItem>
      </PanelSectionRow>
      <PanelSectionRow>
        <ButtonItem layout="below" onClick={() => showModal(<ManageVersionsModal onChanged={onChanged} />)}>
          Manage downloaded…
        </ButtonItem>
      </PanelSectionRow>
    </PanelSection>
  );
}
