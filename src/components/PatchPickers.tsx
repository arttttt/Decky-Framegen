import { DropdownItem, Field, PanelSectionRow } from "@decky/ui";
import type { PatchPickers as Pickers, PickedPatch } from "../hooks/usePatchPickers";

/** The OptiScaler version and the proxy DLL name a patch uses. */
export function PatchPickers({ pickers, picked }: { pickers: Pickers; picked: PickedPatch }) {
  const { choice, launch } = picked;
  return (
    <>
      {choice.ready ? (
        <PanelSectionRow>
          <DropdownItem
            layout="below"
            label="OptiScaler version"
            menuLabel="OptiScaler version"
            selectedOption={choice.versionId}
            rgOptions={choice.versionOptions}
            onChange={(option) => pickers.onVersion(String(option.data))}
          />
        </PanelSectionRow>
      ) : (
        <PanelSectionRow>
          <Field label="OptiScaler" description={choice.versionHint} />
        </PanelSectionRow>
      )}
      <PanelSectionRow>
        <DropdownItem
          layout="below"
          label="Proxy DLL name"
          description={launch.hint}
          menuLabel="Proxy DLL name"
          selectedOption={launch.selected}
          rgOptions={launch.options}
          onChange={(option) => pickers.onDll(String(option.data))}
        />
      </PanelSectionRow>
    </>
  );
}
