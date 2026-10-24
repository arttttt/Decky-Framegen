import { useEffect, useState } from "react";
import { LaunchSetup, launchSetup } from "../api";
import { safeAsyncOperation } from "../utils";

/** The proxy DLLs and launch strings the backend offers; null until it answers. */
export const useLaunchSetup = (): LaunchSetup | null => {
  const [setup, setSetup] = useState<LaunchSetup | null>(null);
  useEffect(() => {
    void safeAsyncOperation(launchSetup, "useLaunchSetup -> launchSetup").then((answer) => {
      if (answer) setSetup(answer);
    });
  }, []);
  return setup;
};
