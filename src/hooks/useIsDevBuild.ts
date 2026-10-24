import { useEffect, useState } from "react";
import { getDevBuild } from "../api";
import { safeAsyncOperation } from "../utils";

/** Whether this is a development build, which has the Developer page. */
export const useIsDevBuild = (): boolean => {
  const [devBuild, setDevBuild] = useState(false);
  useEffect(() => {
    void safeAsyncOperation(getDevBuild, "useIsDevBuild -> getDevBuild").then((build) =>
      setDevBuild(build?.is_dev_build === true),
    );
  }, []);
  return devBuild;
};
