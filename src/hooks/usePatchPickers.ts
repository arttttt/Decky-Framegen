import { useState } from "react";
import type { InstalledLibrary } from "../api";
import { GameStatus, PatchWith, patchChoice } from "../presentation/patching";
import { patchReady, proxyDllView } from "../presentation/launch";
import { useLaunchSetup } from "./useLaunchSetup";

/** The version and proxy a patch uses, as picked. For a patched game nothing picked yet means what
 *  the game is patched with; every decision is made by the view models. */
export const usePatchPickers = (library: InstalledLibrary | null) => {
  const [pickedVersion, setPickedVersion] = useState<string | null>(null);
  const [pickedDll, setPickedDll] = useState<string | null>(null);
  const setup = useLaunchSetup();

  const forGame = (status: GameStatus | null) => {
    const patched = status?.patched ? status : null;
    const choice = patchChoice(library, pickedVersion ?? patched?.optiscaler_version ?? null);
    const launch = proxyDllView(setup, pickedDll ?? patched?.dll_name ?? null);
    const patchWith: PatchWith = { dllName: launch.selected ?? "", versionId: choice.patchWith, ready: patchReady(choice.ready, launch) };
    return { choice, launch, patchWith };
  };

  return { forGame, onVersion: setPickedVersion, onDll: setPickedDll };
};

export type PatchPickers = ReturnType<typeof usePatchPickers>;
export type PickedPatch = ReturnType<PatchPickers["forGame"]>;
