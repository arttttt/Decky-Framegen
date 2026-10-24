import { useEffect, useRef } from "react";
import { addEventListener, removeEventListener } from "@decky/api";

/** Progress of the library download the backend is running ("library_download": id, received, total). */
export const useLibraryDownloadEvents = (onProgress: (id: string, received: number, total: number | null) => void) => {
  const handler = useRef(onProgress);
  handler.current = onProgress;
  useEffect(() => {
    const listener = addEventListener<[string, number, number | null]>("library_download", (id, received, total) =>
      handler.current(id, received, total),
    );
    return () => removeEventListener("library_download", listener);
  }, []);
};
