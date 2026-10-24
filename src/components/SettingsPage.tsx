import { ButtonItem, ConfirmModal, DialogBody, DropdownItem, Field, PanelSection, PanelSectionRow, SidebarNavigation, TextField, showModal, useParams } from "@decky/ui";
import { useDraft } from "../hooks/useDraft";
import { SettingsPage as Page, useSettings } from "../hooks/useSettings";
import { RESET_GAME_CONFIRMATION, RESET_GAME_LABEL, SettingRow, searchRows } from "../presentation/settings";

type OnChange = (section: string, key: string, picked: string) => void;

// Comment blocks keep their line breaks.
const describe = (text: string) => (text ? <span style={{ whiteSpace: "pre-line" }}>{text}</span> : undefined);

function SettingText({ row, value, disabled, onChange }: { row: SettingRow; value: string; disabled: boolean; onChange: OnChange }) {
  const { draft, setDraft, onCommit } = useDraft(value, (text) => onChange(row.section, row.key, text));
  return (
    <TextField
      label={row.label}
      description={describe(row.description)}
      value={draft}
      disabled={disabled}
      onChange={(event) => setDraft(event.target.value)}
      onBlur={onCommit}
      onKeyDown={(event) => event.key === "Enter" && onCommit()}
    />
  );
}

function SettingItem({ row, disabled, onChange }: { row: SettingRow; disabled: boolean; onChange: OnChange }) {
  const { control } = row;
  return (
    <PanelSectionRow>
      {control.kind === "dropdown" ? (
        <DropdownItem
          label={row.label}
          description={describe(row.description)}
          rgOptions={control.options}
          selectedOption={control.selected}
          disabled={disabled}
          onChange={(option) => onChange(row.section, row.key, option.data)}
        />
      ) : (
        <SettingText row={row} value={control.value} disabled={disabled} onChange={onChange} />
      )}
    </PanelSectionRow>
  );
}

function Rows({ rows, page, locked }: { rows: SettingRow[]; page: Page; locked: string | null }) {
  return (
    <>
      {locked && (
        <PanelSectionRow>
          <Field label={locked} />
        </PanelSectionRow>
      )}
      {rows.map((row) => (
        <SettingItem key={`${row.section}.${row.key}`} row={row} disabled={locked !== null} onChange={(s, k, v) => void page.onChange(s, k, v)} />
      ))}
    </>
  );
}

const confirmReset = (onReset: () => void) =>
  showModal(
    <ConfirmModal
      strTitle={RESET_GAME_CONFIRMATION.title}
      strDescription={RESET_GAME_CONFIRMATION.body}
      strOKButtonText={RESET_GAME_LABEL}
      onOK={onReset}
    />,
  );

/** The first page: what these settings are, a game's reset, and a search over every section. */
function SearchPage({ page }: { page: Page }) {
  const { view } = page;
  if (view.kind !== "ready") return null;
  return (
    <PanelSection>
      {view.notices.map((notice) => (
        <PanelSectionRow key={notice}>
          <Field description={notice} />
        </PanelSectionRow>
      ))}
      {view.resetVisible && (
        <PanelSectionRow>
          <ButtonItem layout="below" disabled={view.locked !== null} onClick={() => confirmReset(() => void page.onReset())}>
            {RESET_GAME_LABEL}
          </ButtonItem>
        </PanelSectionRow>
      )}
      <PanelSectionRow>
        <TextField label="Search" value={page.query} onChange={(event) => page.setQuery(event.target.value)} />
      </PanelSectionRow>
      <Rows rows={searchRows(view.sections, page.query)} page={page} locked={view.locked} />
    </PanelSection>
  );
}

/** The settings editor: the global settings, or a game's own over them. Search first, then every
 *  section of the version's OptiScaler.ini, in its order. */
export function SettingsPage() {
  const { scope } = useParams<{ scope: string }>();
  const page = useSettings(scope);
  const { view } = page;
  if (view.kind !== "ready") {
    return (
      <DialogBody>
        <PanelSection title={view.title}>
          <PanelSectionRow>
            <Field label={view.kind === "loading" ? "Loading…" : view.message} />
          </PanelSectionRow>
        </PanelSection>
      </DialogBody>
    );
  }
  return (
    <SidebarNavigation
      title={view.title}
      showTitle
      pages={[
        { title: "Search", identifier: "search", content: <SearchPage page={page} /> },
        ...view.sections.map((section, index) => ({
          title: section.name,
          // By position: an ini may repeat a section header.
          identifier: `section-${index}`,
          content: (
            <PanelSection>
              <Rows rows={section.rows} page={page} locked={view.locked} />
            </PanelSection>
          ),
        })),
      ]}
    />
  );
}
