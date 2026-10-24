import { SmartClipboardButton } from "./SmartClipboardButton";
import type { ProxyDllView } from "../presentation/launch";

interface ClipboardCommandsProps {
  pathExists: boolean | null;
  launch: ProxyDllView;
  manualModeEnabled?: boolean;
  showLaunchOptions?: boolean;
}

export function ClipboardCommands({
  pathExists,
  launch,
  manualModeEnabled = false,
  showLaunchOptions = true,
}: ClipboardCommandsProps) {
  if (pathExists !== true) return null;

  return (
    <>
      {showLaunchOptions && launch.launchOptions ? (
        <SmartClipboardButton command={launch.launchOptions} buttonText="Copy launch options" />
      ) : null}
      {manualModeEnabled && launch.wrapper ? (
        <>
          <SmartClipboardButton command={launch.wrapper.patch} buttonText="Copy Patch Command" />
          <SmartClipboardButton command={launch.wrapper.unpatch} buttonText="Copy Unpatch Command" />
        </>
      ) : null}
    </>
  );
}
