import { ButtonItem, DialogBody, DialogHeader, DropdownItem, Field, ModalRoot } from "@decky/ui";
import { useDownloadVersions } from "../hooks/useDownloadVersions";
import { VersionRows } from "./VersionRows";

/** Download OptiScaler versions from its stable or nightly releases. */
export function DownloadVersionsModal({ closeModal, onChanged }: { closeModal?: () => void; onChanged: () => void }) {
  const { view, onChannel, onCheck, onDownload } = useDownloadVersions(onChanged);

  return (
    <ModalRoot closeModal={closeModal} bAllowFullSize={true}>
      <DialogHeader>Download OptiScaler</DialogHeader>
      <DialogBody>
        <DropdownItem
          label="Channel"
          disabled={!view.channelEnabled}
          rgOptions={view.channelOptions}
          selectedOption={view.channel}
          onChange={(option) => onChannel(option.data)}
        />
        <ButtonItem layout="below" onClick={onCheck} disabled={!view.checkEnabled}>
          {view.checkLabel}
        </ButtonItem>
        {view.message && <Field description={view.message} focusable={true} highlightOnFocus={true} />}
        <VersionRows rows={view.rows} onAction={onDownload} />
      </DialogBody>
    </ModalRoot>
  );
}
