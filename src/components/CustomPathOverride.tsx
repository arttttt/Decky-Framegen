import { useCallback, useEffect, useMemo, useState } from "react";
import { ButtonItem, Field, PanelSectionRow, ToggleField } from "@decky/ui";
import { FileSelectionType, openFilePicker } from "@decky/api";
import { getPathDefaults, runManualPatch } from "../api";
import { UnpatchConfirmation } from "./UnpatchConfirmation";
import { useUnpatch } from "../hooks/useUnpatch";
import { patchButton } from "../presentation/patching";
import type { ApiResponse } from "../types/index";
import { SmartClipboardButton } from "./SmartClipboardButton";

interface PathDefaults {
  home: string;
  steamCommon: string;
}

const DEFAULT_HOME = "/home";
const DEFAULT_STEAM_COMMON = "/home/deck/.local/share/Steam/steamapps/common";

const INITIAL_DEFAULTS: PathDefaults = {
  home: DEFAULT_HOME,
  steamCommon: DEFAULT_STEAM_COMMON,
};

const normalizePath = (value: string) => value.replace(/\\/g, "/");

const stripTrailingSlash = (value: string) =>
  value.length > 1 && value.endsWith("/") ? value.slice(0, -1) : value;

const ensureDirectory = (value: string) => {
  const normalized = normalizePath(value);
  const lastSegment = normalized.substring(normalized.lastIndexOf("/") + 1);
  if (!lastSegment || !lastSegment.includes(".")) {
    return stripTrailingSlash(normalized);
  }
  const parent = normalized.slice(0, normalized.lastIndexOf("/"));
  return parent || "/";
};

interface ManualPatchControlsProps {
  isAvailable: boolean;
  ready: boolean;
  onManualModeChange?: (enabled: boolean) => void;
  dllName: string;
  /** What to copy as the game's launch options; built by the backend. */
  launchOptions: string | null;
  patchWith: string;
}

interface PickerState {
  selectedPath: string | null;
  lastError: string | null;
}

const INITIAL_PICKER_STATE: PickerState = {
  selectedPath: null,
  lastError: null,
};

const formatResultMessage = (result: ApiResponse | null) => {
  if (!result) return null;
  if (result.status === "success") {
    return result.message || result.output || "Operation completed successfully.";
  }
  return result.message || result.output || "Operation failed.";
};

export const ManualPatchControls = ({
  isAvailable,
  ready,
  onManualModeChange,
  dllName,
  launchOptions,
  patchWith,
}: ManualPatchControlsProps) => {
  const [isEnabled, setEnabled] = useState(false);
  const [defaults, setDefaults] = useState<PathDefaults>(INITIAL_DEFAULTS);
  const [pickerState, setPickerState] = useState<PickerState>(INITIAL_PICKER_STATE);
  const [isPatching, setIsPatching] = useState(false);
  const [operationResult, setOperationResult] = useState<ApiResponse | null>(null);
  const [lastOperation, setLastOperation] = useState<"patch" | null>(null);

  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        const response = await getPathDefaults();
        if (!response || cancelled) return;

        const home = response.home ? normalizePath(response.home) : DEFAULT_HOME;
        const steamCommon = response.steam_common
          ? normalizePath(response.steam_common)
          : normalizePath(`${stripTrailingSlash(home)}/.local/share/Steam/steamapps/common`);

        setDefaults({
          home,
          steamCommon: steamCommon || DEFAULT_STEAM_COMMON,
        });
      } catch (err) {
        console.error("ManualPatchControls -> getPathDefaults", err);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!isAvailable) {
      setEnabled(false);
      setPickerState(INITIAL_PICKER_STATE);
      setOperationResult(null);
      setLastOperation(null);
      onManualModeChange?.(false);
    }
  }, [isAvailable, onManualModeChange]);

  const canInteract = isAvailable && isEnabled;
  const patchAction = patchButton(ready, isPatching ? "Patching..." : "Patch directory");
  const selectedPath = pickerState.selectedPath;
  const statusMessage = useMemo(() => formatResultMessage(operationResult), [operationResult]);
  const wasSuccessful = operationResult?.status === "success";
  const statusLabel = useMemo(() => {
    if (!operationResult || !lastOperation) return null;
    return operationResult.status === "success" ? "Game patched" : "Patch failed";
  }, [lastOperation, operationResult]);

  const openDirectoryPicker = useCallback(async () => {
    const candidates = [
      selectedPath,
      defaults.steamCommon,
      defaults.home,
    ];

    let lastError: string | null = null;

    for (const candidate of candidates) {
      if (!candidate) continue;

      const startPath = ensureDirectory(candidate);

      try {
        const result = await openFilePicker(
          FileSelectionType.FOLDER,
          startPath,
          true,
          true,
          undefined,
          undefined,
          true
        );

        if (result?.path) {
          setPickerState({ selectedPath: normalizePath(result.path), lastError: null });
          setOperationResult(null);
          return;
        }
      } catch (err) {
        console.error("ManualPatchControls -> openDirectoryPicker", err);
        lastError = err instanceof Error ? err.message : String(err);
      }
    }

    setPickerState((prev) => ({ ...prev, lastError }));
  }, [defaults.home, defaults.steamCommon, selectedPath]);

  const unpatch = useUnpatch(selectedPath ? { kind: "directory", path: selectedPath } : null, () => {
    setLastOperation(null);
    setOperationResult(null);
  });

  const runPatch = useCallback(
    async () => {
      if (!selectedPath) return;

      setLastOperation("patch");
      setIsPatching(true);
      setOperationResult(null);

      try {
        const response = await runManualPatch(selectedPath, dllName, patchWith);
        setOperationResult(response ?? { status: "error", message: "No response from backend." });
      } catch (err) {
        setOperationResult({
          status: "error",
          message: err instanceof Error ? err.message : String(err),
        });
      } finally {
        setIsPatching(false);
      }
    },
    [selectedPath, dllName, patchWith]
  );

  const handleToggle = (value: boolean) => {
    if (!isAvailable) {
      setEnabled(false);
      return;
    }

    setEnabled(value);
    onManualModeChange?.(value);
    if (!value) {
      setPickerState(INITIAL_PICKER_STATE);
      setOperationResult(null);
      setLastOperation(null);
    }
  };

  const busy = isPatching || unpatch.busy;

  return (
    <>
      <PanelSectionRow>
        <ToggleField
          label="Advanced Mode"
          description={
            isAvailable
              ? "Manually apply OptiScaler to a specific game directory."
              : "Install OptiScaler first to enable manual patching."
          }
          checked={isEnabled && isAvailable}
          disabled={!isAvailable}
          onChange={handleToggle}
        />
      </PanelSectionRow>

      {canInteract && (
        <>
          {launchOptions && <SmartClipboardButton command={launchOptions} buttonText="Manual launch cmd" />}
          <PanelSectionRow>
            <ButtonItem
              layout="below"
              onClick={openDirectoryPicker}
              description="Choose the game's installation directory (where the EXE lives)."
            >
              Select directory
            </ButtonItem>
          </PanelSectionRow>

          {pickerState.lastError && (
            <PanelSectionRow>
              <Field
                label="Picker error"
                description={pickerState.lastError}
              />
            </PanelSectionRow>
          )}

          {selectedPath && (
            <>
              <PanelSectionRow>
                <Field
                  label="Target directory"
                  description="OptiScaler files will be copied here."
                >
                  <div
                    style={{
                      fontFamily: "monospace",
                      backgroundColor: "rgba(255, 255, 255, 0.05)",
                      border: "1px solid rgba(255, 255, 255, 0.1)",
                      borderRadius: "4px",
                      padding: "6px 8px",
                      width: "100%",
                      boxSizing: "border-box",
                      whiteSpace: "pre-wrap",
                      wordBreak: "break-word",
                    }}
                  >
                    {selectedPath}
                  </div>
                </Field>
              </PanelSectionRow>

              <PanelSectionRow>
                <ButtonItem
                  layout="below"
                  disabled={busy || !patchAction.enabled}
                  onClick={() => void runPatch()}
                >
                  {patchAction.label}
                </ButtonItem>
              </PanelSectionRow>

              <PanelSectionRow>
                <ButtonItem
                  layout="below"
                  disabled={busy}
                  onClick={unpatch.onUnpatch}
                >
                  {unpatch.busy ? "Unpatching..." : "Unpatch directory"}
                </ButtonItem>
              </PanelSectionRow>

              <UnpatchConfirmation
                confirmation={unpatch.confirmation}
                onConfirm={unpatch.onConfirm}
                onCancel={unpatch.onCancel}
              />
            </>
          )}

          {operationResult && (
            <PanelSectionRow>
              <Field
                label={statusLabel ?? (wasSuccessful ? "Last action succeeded" : "Last action failed")}
              >
                {!wasSuccessful && statusMessage ? statusMessage : null}
              </Field>
            </PanelSectionRow>
          )}
        </>
      )}
    </>
  );
};