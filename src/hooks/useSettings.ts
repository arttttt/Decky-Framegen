import { useCallback, useEffect, useState } from "react";
import { notify } from "../utils/notify";
import { SettingsAnswer, gameSettings, globalSettings, resetGameSettings, setSetting } from "../api";
import { GLOBAL_SCOPE, changedValue, settingsPageView, skippedMessage } from "../presentation/settings";

const failure = (err: unknown): SettingsAnswer => ({
  status: "error",
  message: err instanceof Error ? err.message : "Couldn't read the settings.",
});

/** A settings page's data, changing a setting and resetting a game's own; scope is "global" or an appid.
 *  After every change the page is read again, so it shows what the backend stored. */
export const useSettings = (scope: string) => {
  const [answer, setAnswer] = useState<SettingsAnswer | null>(null);
  const [query, setQuery] = useState("");

  const load = useCallback(async () => {
    try {
      setAnswer(await (scope === GLOBAL_SCOPE ? globalSettings() : gameSettings(scope)));
    } catch (err) {
      setAnswer(failure(err));
    }
  }, [scope]);

  useEffect(() => {
    setAnswer(null);
    void load();
  }, [load]);

  const onChange = useCallback(
    async (section: string, key: string, picked: string) => {
      try {
        const result = await setSetting(scope, section, key, changedValue(picked));
        const message = result.status === "success" ? skippedMessage(result.skipped ?? []) : result.message || "Couldn't save the setting.";
        if (message) notify(message);
      } catch (err) {
        notify(err instanceof Error ? err.message : "Couldn't save the setting.");
      }
      await load();
    },
    [scope, load],
  );

  const onReset = useCallback(async () => {
    try {
      const result = await resetGameSettings(scope);
      if (result.status !== "success") notify(result.message || "Couldn't reset the settings.");
    } catch (err) {
      notify(err instanceof Error ? err.message : "Couldn't reset the settings.");
    }
    await load();
  }, [scope, load]);

  return { view: settingsPageView(scope, answer), query, setQuery, onChange, onReset };
};

export type SettingsPage = ReturnType<typeof useSettings>;
