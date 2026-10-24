import { DialogBody, DialogHeader, Field, Menu, MenuItem, ModalRoot, showContextMenu } from "@decky/ui";
import { useManageVersions } from "../hooks/useManageVersions";
import { MANAGE_MENU } from "../presentation/library";
import { Confirmation } from "./Confirmation";
import { VersionRows } from "./VersionRows";

/** The OptiScaler versions on the device: download one again, remove one. */
export function ManageVersionsModal({ closeModal, onChanged }: { closeModal?: () => void; onChanged: () => void }) {
  const { view, onSelect, confirmation, onConfirm, onCancel } = useManageVersions(onChanged);

  const openMenu = (id: string, label: string) =>
    showContextMenu(
      <Menu label={label}>
        {MANAGE_MENU.map((item) => (
          <MenuItem key={item.action} tone={item.destructive ? "destructive" : undefined} onSelected={() => onSelect(id, item)}>
            {item.label}
          </MenuItem>
        ))}
      </Menu>
    );

  return (
    <ModalRoot closeModal={closeModal} bAllowFullSize={true}>
      <DialogHeader>Downloaded OptiScaler versions</DialogHeader>
      <DialogBody>
        {view.message && <Field description={view.message} />}
        <VersionRows rows={view.rows} onAction={openMenu} />
        {view.usage && <Field description={view.usage} />}
      </DialogBody>
      <Confirmation confirmation={confirmation} onConfirm={onConfirm} onCancel={onCancel} />
    </ModalRoot>
  );
}
