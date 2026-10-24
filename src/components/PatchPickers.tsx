import { DropdownItem, Field, PanelSectionRow } from "@decky/ui";
import type { PatchPickers as Pickers } from "../hooks/usePatchPickers";

/** The OptiScaler version and the proxy DLL name a patch uses. */
export function PatchPickers({ pickers }: { pickers: Pickers }) {
  const { choice, launch } = pickers;
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
          <Field label="OptiScaler" description={choice.versionHint} focusable={true} highlightOnFocus={true} />
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
