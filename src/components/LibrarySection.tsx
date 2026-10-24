import { ButtonItem, ConfirmModal, DropdownItem, Field, Menu, MenuItem, PanelSection, PanelSectionRow, showContextMenu, showModal } from "@decky/ui";
import { useLibrary } from "../hooks/useLibrary";
import { libraryMenu } from "../presentation/library";

/** OptiScaler versions on the device: download them from OptiScaler's releases, choose the default, remove them. */
export function LibrarySection({ onChanged }: { onChanged: () => void }) {
  const { view, versionById, onChannel, onCheck, onDownload, onMakeDefault, removalOf, onRemove } = useLibrary(onChanged);

  const confirmRemoval = async (id: string) => {
    const version = versionById(id);
    if (!version) return;
    const confirmation = await removalOf(version);
    showModal(
      <ConfirmModal
        strTitle={confirmation.title}
        strDescription={
          <>
            {confirmation.lines.map((line) => (
              <div key={line}>{line}</div>
            ))}
          </>
        }
        strOKButtonText={confirmation.okLabel}
        onOK={() => onRemove(id)}
      />
    );
  };

  const manage = (id: string, label: string) => {
    const version = versionById(id);
    if (!version) return;
    showContextMenu(
      <Menu label={label}>
        {libraryMenu(version).map((item) => (
          <MenuItem
            key={item.intent}
            tone={item.destructive ? "destructive" : undefined}
            onSelected={() => (item.intent === "remove" ? void confirmRemoval(id) : onMakeDefault(id))}
          >
            {item.label}
          </MenuItem>
        ))}
      </Menu>
    );
  };

  return (
    <PanelSection title="OptiScaler library">
      <PanelSectionRow>
        <DropdownItem
          layout="below"
          label="Channel"
          disabled={!view.channelEnabled}
          rgOptions={view.channelOptions}
          selectedOption={view.channel}
          onChange={(option) => onChannel(option.data)}
        />
      </PanelSectionRow>
      <PanelSectionRow>
        <ButtonItem layout="below" onClick={onCheck} disabled={!view.checkEnabled}>
          {view.checkLabel}
        </ButtonItem>
      </PanelSectionRow>
      {view.message && (
        <PanelSectionRow>
          <Field description={view.message} focusable={true} highlightOnFocus={true} />
        </PanelSectionRow>
      )}
      {view.rows.map((row) => (
        <PanelSectionRow key={row.id}>
          {row.action ? (
            <ButtonItem
              label={row.label}
              description={row.description}
              disabled={!row.action.enabled}
              onClick={() => (row.action?.intent === "download" ? onDownload(row.id) : manage(row.id, row.label))}
            >
              {row.action.label}
            </ButtonItem>
          ) : (
            <Field label={row.label} description={row.description} focusable={true} highlightOnFocus={true} />
          )}
        </PanelSectionRow>
      ))}
      {view.usage && (
        <PanelSectionRow>
          <Field description={view.usage} focusable={true} highlightOnFocus={true} />
        </PanelSectionRow>
      )}
    </PanelSection>
  );
}
