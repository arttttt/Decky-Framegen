import { describe, expect, it } from "vitest";
import type { AvailableDevBuild, DevBuild } from "../api";
import { DeveloperSectionState, developerSectionView, selectedBuild } from "./developerSection";

const running: DevBuild = { is_dev_build: true, channel: "dev", commit: "9".repeat(40), short_commit: "9999999", title: "main @ 9999999" };

const build = (channel: string, state: "installed" | "available", title: string): AvailableDevBuild => ({
  channel,
  commit: "1".repeat(40),
  short_commit: "1111111",
  title,
  published_at: "2026-10-23T10:00:05Z",
  state,
});

const listed = [build("dev", "installed", "main @ 9999999"), build("pr-12", "available", "PR #12: Developer section")];

const state = (overrides: Partial<DeveloperSectionState> = {}): DeveloperSectionState => ({
  build: running,
  list: { status: "success", builds: listed },
  checking: false,
  selectedChannel: null,
  install: "idle",
  installError: null,
  deckyInstallerAvailable: true,
  ...overrides,
});

const visible = (s: DeveloperSectionState) => {
  const view = developerSectionView(s);
  if (!view.visible) throw new Error("expected the section to be visible");
  return view;
};

describe("developer section", () => {
  it("is hidden in a release build and before the backend answers", () => {
    expect(developerSectionView(state({ build: { is_dev_build: false } }))).toEqual({ visible: false });
    expect(developerSectionView(state({ build: null }))).toEqual({ visible: false });
  });

  it("names the running build and offers to look for others before the first check", () => {
    const view = visible(state({ list: null }));

    expect(view.running).toBe("Running main @ 9999999");
    expect(view.checkLabel).toBe("Check for builds");
    expect(view.pickerVisible).toBe(false);
    expect(view.installEnabled).toBe(false);
  });

  it("points the picker at the running channel and marks it running", () => {
    const view = visible(state());

    expect(view.options).toEqual([
      { data: "dev", label: "main @ 9999999 (running)" },
      { data: "pr-12", label: "PR #12: Developer section" },
    ]);
    expect(view.selectedChannel).toBe("dev");
    expect(view.installLabel).toBe("Already running");
    expect(view.installEnabled).toBe(false);
  });

  it("lets the user install another build and shows when it was published", () => {
    const view = visible(state({ selectedChannel: "pr-12" }));

    expect(view.details).toBe("Commit 1111111, published 2026-10-23 10:00 UTC");
    expect(view.installLabel).toBe("Install");
    expect(view.installEnabled).toBe(true);
    expect(selectedBuild(state({ selectedChannel: "pr-12" }))?.channel).toBe("pr-12");
  });

  it("starts on the running build's channel even when it is not listed first", () => {
    const onPr: DevBuild = { ...running, channel: "pr-12", title: "PR #12" };

    expect(selectedBuild(state({ build: onPr }))?.channel).toBe("pr-12");
  });

  it("falls back to the first build when the chosen or running channel is gone", () => {
    const onlyPr = { status: "success" as const, builds: [listed[1]] };

    expect(selectedBuild(state({ list: onlyPr }))?.channel).toBe("pr-12");
    expect(selectedBuild(state({ list: onlyPr, selectedChannel: "pr-99" }))?.channel).toBe("pr-12");
  });

  it("installs once while Decky asks; checking stays available", () => {
    const view = visible(state({ selectedChannel: "pr-12", install: "started" }));

    expect(view.installEnabled).toBe(false);
    expect(view.checkEnabled).toBe(true);
    expect(view.message).toBe("Decky asks to confirm, then reloads the plugin with the new build.");
  });

  it("offers to install again when the plugin is still running after the install (cancelled in Decky)", () => {
    const view = visible(state({ selectedChannel: "pr-12", install: "unconfirmed" }));

    expect(view.installEnabled).toBe(true);
    expect(view.checkEnabled).toBe(true);
    expect(view.message).toBe("The plugin was not replaced. If you cancelled in Decky, install again.");
  });

  it("says why an install could not start and lets the user try again", () => {
    const view = visible(state({ selectedChannel: "pr-12", installError: "The pr-12 build is no longer published. Check again." }));

    expect(view.message).toBe("The pr-12 build is no longer published. Check again.");
    expect(view.installEnabled).toBe(true);
  });

  it("blocks checking and installing while a check runs", () => {
    const view = visible(state({ selectedChannel: "pr-12", checking: true }));

    expect(view.checkLabel).toBe("Checking…");
    expect(view.checkEnabled).toBe(false);
    expect(view.installEnabled).toBe(false);
  });

  it("explains when Decky's installer cannot be reached and never offers to install", () => {
    const view = visible(state({ selectedChannel: "pr-12", deckyInstallerAvailable: false }));

    expect(view.installEnabled).toBe(false);
    expect(view.message).toBe("Decky's installer is not reachable from this plugin; install builds by URL instead.");
  });

  it("shows the backend's error and an empty listing in words", () => {
    expect(visible(state({ list: { status: "error", message: "GitHub answered 403" } })).message).toBe("GitHub answered 403");
    const empty = visible(state({ list: { status: "success", builds: [] } }));
    expect(empty.message).toBe("No development builds are published.");
    expect(empty.pickerVisible).toBe(false);
    expect(empty.checkLabel).toBe("Check again");
  });
});
