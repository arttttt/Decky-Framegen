import { useEffect, useState } from "react";
import { getDevBuild } from "../api";
import { safeAsyncOperation } from "../utils";

/** Whether this is a development build (experiments are offered only there). */
export const useIsDevBuild = (): boolean => {
  const [devBuild, setDevBuild] = useState(false);
  useEffect(() => {
    void safeAsyncOperation(getDevBuild, "useIsDevBuild -> getDevBuild").then((build) =>
      setDevBuild(build?.is_dev_build === true),
    );
  }, []);
  return devBuild;
};
