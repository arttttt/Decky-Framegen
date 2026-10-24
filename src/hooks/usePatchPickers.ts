import { useState } from "react";
import type { InstalledLibrary } from "../api";
import { patchChoice } from "../presentation/patching";
import { patchReady, proxyDllView } from "../presentation/launch";
import { useLaunchSetup } from "./useLaunchSetup";

/** The version and proxy a patch uses, as picked; every decision is made by their view models. */
export const usePatchPickers = (library: InstalledLibrary | null) => {
  const [pickedVersion, setPickedVersion] = useState<string | null>(null);
  const [pickedDll, setPickedDll] = useState<string | null>(null);
  const choice = patchChoice(library, pickedVersion);
  const launch = proxyDllView(useLaunchSetup(), pickedDll);
  return {
    choice,
    launch,
    dllName: launch.selected ?? "",
    ready: patchReady(choice.ready, launch),
    onVersion: setPickedVersion,
    onDll: setPickedDll,
  };
};

export type PatchPickers = ReturnType<typeof usePatchPickers>;
