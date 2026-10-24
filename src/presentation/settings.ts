import type { SettingInfo, SettingsAnswer } from "../api";

/** The scope of the global settings; any other scope is a game's appid. */
export const GLOBAL_SCOPE = "global";

const AUTO = "auto";
/** The dropdown option that clears the page's own value, so the one below shows through. */
export const INHERIT = "\u0000inherit";

export type SettingControl =
  | { kind: "dropdown"; options: { data: string; label: string }[]; selected: string }
  /** Empty text clears the page's own value. */
  | { kind: "text"; value: string };

export type SettingRow = {
  section: string;
  key: string;
  label: string;
  description: string;
  control: SettingControl;
};

export type SettingsSectionView = { name: string; rows: SettingRow[] };

export type SettingsPageView =
  | { kind: "loading"; title: string; message: string }
  | { kind: "error"; title: string; message: string }
  | {
      kind: "ready";
      title: string;
      /** Lines the first page shows above the search. */
      notices: string[];
      /** Why nothing can be changed now; null when it can. */
      locked: string | null;
      sections: SettingsSectionView[];
      resetVisible: boolean;
    };

const isGlobal = (scope: string): boolean => scope === GLOBAL_SCOPE;

/** A value as the page shows it: On/Off, a numbered choice's name, or the value itself. */
const valueLabel = (setting: SettingInfo, value: string): string => {
  if (value === AUTO) return autoLabel(setting);
  if (setting.kind === "bool") return value === "true" ? "On" : value === "false" ? "Off" : value;
  const choice = setting.choices.find((c) => c.value.toLowerCase() === value.toLowerCase());
  return choice ? choice.label : value;
};

/** "Auto", with OptiScaler's default when its comment states one. */
const autoLabel = (setting: SettingInfo): string =>
  setting.default === null ? "Auto" : `Auto (${valueLabel(setting, setting.default)})`;

/** What the setting is without the page's own value: auto on the global page, global on a game's. */
const inheritLabel = (scope: string, setting: SettingInfo): string =>
  isGlobal(scope) ? autoLabel(setting) : `Same as global: ${valueLabel(setting, setting.inherited.value)}`;

/** Whether the value is the page's own: set in the global settings, or in the game's. */
const ownValue = (scope: string, setting: SettingInfo): boolean =>
  setting.source === (isGlobal(scope) ? "global" : "game");

const valueOptions = (setting: SettingInfo): string[] =>
  setting.kind === "bool" ? ["true", "false"] : setting.choices.map((c) => c.value);

const rangeLine = (setting: SettingInfo): string | null => {
  if (setting.kind !== "number") return null;
  const { minimum, maximum } = setting;
  if (minimum !== null && maximum !== null) return `From ${minimum} to ${maximum}.`;
  if (minimum !== null) return `${minimum} or more.`;
  if (maximum !== null) return `Up to ${maximum}.`;
  return setting.integer ? "A whole number." : "A number.";
};

/** A setting's control: a dropdown when its values are a list, else a text field. The first option
 *  (or empty text) is the value below the page's; a game's page also offers auto over global. */
const control = (scope: string, setting: SettingInfo): SettingControl => {
  const own = ownValue(scope, setting);
  if (setting.kind !== "bool" && setting.kind !== "enum") {
    return { kind: "text", value: own ? setting.value : "" };
  }
  const values = valueOptions(setting);
  const options = [
    { data: INHERIT, label: inheritLabel(scope, setting) },
    ...(isGlobal(scope) ? [] : [{ data: AUTO, label: autoLabel(setting) }]),
    ...values.map((value) => ({ data: value, label: valueLabel(setting, value) })),
  ];
  const matched = values.find((value) => value.toLowerCase() === setting.value.toLowerCase());
  const selected = !own ? INHERIT : matched ?? (setting.value === AUTO && !isGlobal(scope) ? AUTO : INHERIT);
  return { kind: "dropdown", options, selected };
};

const row = (scope: string, section: string, setting: SettingInfo): SettingRow => {
  const textHint =
    setting.kind === "bool" || setting.kind === "enum"
      ? null
      : `Empty: ${isGlobal(scope) ? autoLabel(setting).toLowerCase() : inheritLabel(scope, setting).toLowerCase()}.`;
  return {
    section,
    key: setting.key,
    label: setting.key,
    description: [setting.description, rangeLine(setting), textHint].filter(Boolean).join("\n"),
    control: control(scope, setting),
  };
};

/** The value a change sends: the inherit option and empty text clear the page's own value. */
export const changedValue = (picked: string): string | null => {
  const value = picked.trim();
  return value === "" || picked === INHERIT ? null : value;
};

const OVERLAY_NOTICE =
  "A setting set here replaces a change to it in OptiScaler's in-game menu once the game closes.";

/** What a settings page shows: global settings, or a game's own over them. */
export const settingsPageView = (scope: string, answer: SettingsAnswer | null): SettingsPageView => {
  const global = isGlobal(scope);
  const title = global ? "Global settings" : answer?.name ? `${answer.name} settings` : "Game settings";
  if (answer === null) return { kind: "loading", title, message: "Loading…" };
  if (answer.status !== "success" || !answer.sections) {
    return { kind: "error", title, message: answer.message || "Couldn't read the settings." };
  }
  const sections = answer.sections.map((section) => ({
    name: section.name,
    rows: section.settings.map((setting) => row(scope, section.name, setting)),
  }));
  const unsupported = answer.unsupported ?? [];
  const notices = [
    global
      ? "Every game gets these settings; a game's own settings stay over them."
      : "This game's own settings; anything left as global follows the global settings.",
    `The settings OptiScaler ${answer.version} offers.`,
    ...(!global && !answer.patched ? ["The game isn't patched yet: it gets these settings when it is."] : []),
    ...(unsupported.length ? [`Kept for other versions, as this one doesn't take them: ${unsupported.join(", ")}.`] : []),
    OVERLAY_NOTICE,
  ];
  return {
    kind: "ready",
    title,
    notices,
    locked: !global && answer.running ? "Close the game to change its settings." : null,
    sections,
    resetVisible: !global && answer.sections.some((s) => s.settings.some((setting) => setting.source === "game")),
  };
};

/** The rows whose key, section or description holds the query, named with their section; none for an
 *  empty query. */
export const searchRows = (sections: SettingsSectionView[], query: string): SettingRow[] => {
  const words = query.trim().toLowerCase();
  if (!words) return [];
  return sections.flatMap((section) =>
    section.rows
      .filter((r) => `${r.section} ${r.key} ${r.description}`.toLowerCase().includes(words))
      .map((r) => ({ ...r, label: `${r.section} · ${r.key}` })),
  );
};

/** What a global change says about the running games it didn't reach. */
export const skippedMessage = (skipped: string[]): string | null =>
  skipped.length === 0
    ? null
    : `${skipped.join(", ")} ${skipped.length === 1 ? "is" : "are"} running and ${skipped.length === 1 ? "gets" : "get"} the change once closed.`;

export const RESET_GAME_LABEL = "Reset to global settings";
export const RESET_GAME_CONFIRMATION = {
  title: "Reset to global settings?",
  body: "The game's own settings are removed, and it follows the global settings again.",
};
