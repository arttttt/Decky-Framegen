import { describe, expect, it } from "vitest";
import type { SettingInfo, SettingsAnswer } from "../api";
import {
  GLOBAL_SCOPE,
  INHERIT,
  changedValue,
  searchRows,
  settingsPageView,
  skippedMessage,
  type SettingRow,
} from "./settings";

const setting = (overrides: Partial<SettingInfo>): SettingInfo => ({
  key: "Key",
  kind: "text",
  description: "What it does.",
  help: "",
  default: null,
  choices: [],
  minimum: null,
  maximum: null,
  integer: false,
  value: "auto",
  source: "default",
  inherited: { value: "auto", source: "default" },
  ...overrides,
});

const MODEL = setting({
  key: "Fsr4Model",
  kind: "enum",
  default: "0",
  choices: [
    { value: "0", label: "FP8" },
    { value: "1", label: "INT8" },
  ],
});
const HQ_FONT = setting({ key: "UseHQFont", kind: "bool", default: "true" });
const SHARPNESS = setting({ key: "Sharpness", kind: "number", minimum: 0, maximum: 1.3 });

const answer = (settings: SettingInfo[], extra: Partial<SettingsAnswer> = {}): SettingsAnswer => ({
  status: "success",
  version: "nightly-20261024",
  sections: [{ name: "FSR", settings }],
  unsupported: [],
  ...extra,
});

const rowOf = (scope: string, info: SettingInfo, extra: Partial<SettingsAnswer> = {}): SettingRow => {
  const view = settingsPageView(scope, answer([info], extra));
  if (view.kind !== "ready") throw new Error(view.kind);
  return view.sections[0].rows[0];
};

describe("a setting's dropdown", () => {
  it("on the global page starts with auto and OptiScaler's default, then the setting's values", () => {
    const row = rowOf(GLOBAL_SCOPE, MODEL);
    expect(row.control).toEqual({
      kind: "dropdown",
      options: [
        { data: INHERIT, label: "Auto (FP8)" },
        { data: "0", label: "FP8" },
        { data: "1", label: "INT8" },
      ],
      selected: INHERIT,
    });
  });

  it("on a game's page offers the global value, then auto over it", () => {
    const row = rowOf("1", { ...HQ_FONT, value: "false", source: "global", inherited: { value: "false", source: "global" } });
    expect(row.control).toEqual({
      kind: "dropdown",
      options: [
        { data: INHERIT, label: "Same as global: Off" },
        { data: "auto", label: "Auto (On)" },
        { data: "true", label: "On" },
        { data: "false", label: "Off" },
      ],
      selected: INHERIT,
    });
  });

  it("on a game's page names the global value even while the game has its own", () => {
    const row = rowOf("1", { ...HQ_FONT, value: "true", source: "game", inherited: { value: "false", source: "global" } });
    if (row.control.kind !== "dropdown") throw new Error(row.control.kind);
    expect(row.control.options[0]).toEqual({ data: INHERIT, label: "Same as global: Off" });
    expect(row.control.selected).toBe("true");
  });

  it("selects the page's own value, auto included on a game's page, whatever its case", () => {
    const own = (scope: string, value: string, source: SettingInfo["source"]) =>
      rowOf(scope, { ...MODEL, value, source }).control;
    expect(own(GLOBAL_SCOPE, "1", "global")).toMatchObject({ selected: "1" });
    expect(own("1", "1", "global")).toMatchObject({ selected: INHERIT }); // global's, not the game's own
    expect(own("1", "auto", "game")).toMatchObject({ selected: "auto" });
    expect(rowOf(GLOBAL_SCOPE, { ...setting({ kind: "enum", choices: [{ value: "rcas", label: "rcas" }] }), value: "RCAS", source: "global" }).control).toMatchObject({ selected: "rcas" });
  });

  it("says just auto when OptiScaler states its default only in prose", () => {
    const row = rowOf(GLOBAL_SCOPE, { ...MODEL, default: null });
    expect(row.control).toMatchObject({ options: [{ data: INHERIT, label: "Auto" }, {}, {}] });
  });
});

describe("a setting's text field", () => {
  it("holds only the page's own value and says what empty means and the range", () => {
    expect(rowOf(GLOBAL_SCOPE, { ...SHARPNESS, value: "0.5", source: "global" })).toMatchObject({
      control: { kind: "text", value: "0.5" },
      description: "What it does.\nFrom 0 to 1.3.\nEmpty: auto.",
    });
    expect(
      rowOf("1", { ...SHARPNESS, value: "0.5", source: "global", inherited: { value: "0.5", source: "global" } }),
    ).toMatchObject({ control: { kind: "text", value: "" }, description: "What it does.\nFrom 0 to 1.3.\nEmpty: same as global: 0.5." });
  });

  it("states an open range or the kind of number", () => {
    expect(rowOf(GLOBAL_SCOPE, { ...SHARPNESS, maximum: null }).description).toContain("0 or more.");
    expect(rowOf(GLOBAL_SCOPE, { ...SHARPNESS, minimum: null, maximum: null, integer: true }).description).toContain("A whole number.");
    expect(rowOf(GLOBAL_SCOPE, setting({ kind: "text" })).description).toBe("What it does.\nEmpty: auto.");
  });
});

describe("a change", () => {
  it("clears the page's own value with the inherit option or empty text", () => {
    expect(changedValue(INHERIT)).toBeNull();
    expect(changedValue("  ")).toBeNull();
    expect(changedValue(" 0.5 ")).toBe("0.5");
    expect(changedValue("auto")).toBe("auto");
  });

  it("names the running games a global change didn't reach", () => {
    expect(skippedMessage([])).toBeNull();
    expect(skippedMessage(["Cyberpunk 2077"])).toBe("Cyberpunk 2077 is running and gets the change at the next start.");
    expect(skippedMessage(["A", "B"])).toBe("A, B are running and get the change at the next start.");
  });
});

describe("a settings page", () => {
  it("is loading, then an error with the backend's words", () => {
    expect(settingsPageView(GLOBAL_SCOPE, null)).toEqual({ kind: "loading", title: "Global settings" });
    expect(settingsPageView("1", { status: "error", message: "No OptiScaler version." })).toEqual({
      kind: "error",
      title: "Game settings",
      message: "No OptiScaler version.",
    });
  });

  it("for a game is titled with its name, says what isn't patched or supported, and locks while it runs", () => {
    const view = settingsPageView("1", answer([MODEL], { name: "Game", patched: false, running: true, unsupported: ["FrameGen.FGInput"] }));
    expect(view).toMatchObject({ kind: "ready", title: "Game settings", locked: "Close the game to change its settings." });
    if (view.kind !== "ready") return;
    expect(view.notices).toContain("The game isn't patched yet: it gets these settings when it is.");
    expect(view.notices).toContain("Kept for other versions, as this one doesn't take them: FrameGen.FGInput.");
    expect(view.notices.some((n) => n.includes("in-game menu"))).toBe(true);
  });

  it("for the global settings says every game gets them, and nothing of being patched", () => {
    const view = settingsPageView(GLOBAL_SCOPE, answer([MODEL]));
    if (view.kind !== "ready") throw new Error(view.kind);
    expect(view.notices[0]).toBe("Every game gets these settings; a game's own settings stay over them.");
    expect(view.notices.some((n) => n.includes("patched"))).toBe(false);
  });

  it("offers a game's reset only while it has settings of its own; the global page is never locked", () => {
    expect(settingsPageView("1", answer([MODEL], { name: "G", patched: true }))).toMatchObject({ resetVisible: false, title: "G settings" });
    expect(settingsPageView("1", answer([{ ...MODEL, source: "global" }], { patched: true }))).toMatchObject({ resetVisible: false });
    expect(settingsPageView("1", answer([{ ...MODEL, source: "game" }], { patched: true }))).toMatchObject({ resetVisible: true });
    expect(settingsPageView(GLOBAL_SCOPE, answer([{ ...MODEL, source: "global" }], { running: true }))).toMatchObject({
      resetVisible: false,
      locked: null,
    });
  });
});

describe("search", () => {
  const view = settingsPageView(GLOBAL_SCOPE, answer([MODEL, HQ_FONT, SHARPNESS]));
  const sections = view.kind === "ready" ? view.sections : [];

  it("finds settings by key, section or description, named with their section", () => {
    expect(searchRows(sections, "hqfont").map((r) => r.label)).toEqual(["FSR · UseHQFont"]);
    expect(searchRows(sections, " fsr ")).toHaveLength(3);
    expect(searchRows(sections, "what it DOES")).toHaveLength(3);
  });

  it("finds nothing for an empty query", () => {
    expect(searchRows(sections, "  ")).toEqual([]);
  });
});
