import { ConfirmModal, DialogBody, DialogHeader, Field, Menu, MenuItem, ModalRoot, showContextMenu, showModal } from "@decky/ui";
import { useManageVersions } from "../hooks/useManageVersions";
import { manageMenu } from "../presentation/library";
import { VersionRows } from "./VersionRows";

/** The OptiScaler versions on the device: choose the one new patches use, download one again, remove one. */
export function ManageVersionsModal({ closeModal, onChanged }: { closeModal?: () => void; onChanged: () => void }) {
  const { view, isDefault, run, removalOf } = useManageVersions(onChanged);

  const confirmRemoval = async (id: string) => {
    const confirmation = await removalOf(id);
    if (!confirmation) return;
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
        onOK={() => run(id, "remove")}
      />
    );
  };

  const openMenu = (id: string, label: string) =>
    showContextMenu(
      <Menu label={label}>
        {manageMenu(isDefault(id)).map((item) => (
          <MenuItem
            key={item.action}
            tone={item.destructive ? "destructive" : undefined}
            onSelected={() => (item.action === "remove" ? void confirmRemoval(id) : run(id, item.action))}
          >
            {item.label}
          </MenuItem>
        ))}
      </Menu>
    );

  return (
    <ModalRoot closeModal={closeModal} bAllowFullSize={true}>
      <DialogHeader>Downloaded OptiScaler versions</DialogHeader>
      <DialogBody>
        {view.message && <Field description={view.message} focusable={true} highlightOnFocus={true} />}
        <VersionRows rows={view.rows} onAction={openMenu} />
        {view.usage && <Field description={view.usage} focusable={true} highlightOnFocus={true} />}
      </DialogBody>
    </ModalRoot>
  );
}
