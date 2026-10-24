import { describe, expect, it } from "vitest";
import type { AvailableDevBuild, PluginBuild } from "../api";
import { DeveloperSectionState, developerSectionView, selectedBuild } from "./developerSection";
import { NO_INSTALL } from "./install";

const running: PluginBuild = {
  known: true,
  channel: "dev",
  commit: "9".repeat(40),
  short_commit: "9999999",
  title: "main @ 9999999",
  version: "2026.10.24-dev.9999999",
  is_dev_build: true,
  developer_mode: true,
};
const release: PluginBuild = { ...running, channel: "stable", title: "Decky Framegen 2026.10.24", version: "2026.10.24", is_dev_build: false };

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
  install: NO_INSTALL,
  deckyInstallerAvailable: true,
  ...overrides,
});

const visible = (s: DeveloperSectionState) => {
  const view = developerSectionView(s);
  if (!view.visible) throw new Error("expected the section to be visible");
  return view;
};

describe("developer section", () => {
  it("is hidden without Developer mode, in a build that can't update itself, and before the backend answers", () => {
    expect(developerSectionView(state({ build: { ...release, developer_mode: false } }))).toEqual({ visible: false });
    expect(developerSectionView(state({ build: { known: false, version: "", message: "" } }))).toEqual({ visible: false });
    expect(developerSectionView(state({ build: null }))).toEqual({ visible: false });
  });

  it("in a release with Developer mode on offers the development builds, the first picked", () => {
    const view = visible(state({ build: release, list: { status: "success", builds: [build("dev", "available", "main @ 9999999")] } }));

    expect(view.running).toBe("Running Decky Framegen 2026.10.24");
    expect(view.selectedChannel).toBe("dev");
    expect(view.installEnabled).toBe(true);
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
    const onPr: PluginBuild = { ...running, channel: "pr-12", title: "PR #12" };

    expect(selectedBuild(state({ build: onPr }))?.channel).toBe("pr-12");
  });

  it("falls back to the first build when the chosen or running channel is gone", () => {
    const onlyPr = { status: "success" as const, builds: [listed[1]] };

    expect(selectedBuild(state({ list: onlyPr }))?.channel).toBe("pr-12");
    expect(selectedBuild(state({ list: onlyPr, selectedChannel: "pr-99" }))?.channel).toBe("pr-12");
  });

  it("installs once while Decky asks; checking stays available", () => {
    const view = visible(state({ selectedChannel: "pr-12", install: { ...NO_INSTALL, phase: "started" } }));

    expect(view.installEnabled).toBe(false);
    expect(view.checkEnabled).toBe(true);
    expect(view.message).toBe("Downloaded. Decky asks to confirm, then reloads the plugin with the new build.");
  });

  it("shows the download of the build being installed and blocks starting another", () => {
    const waiting = visible(state({ selectedChannel: "pr-12", install: { ...NO_INSTALL, phase: "downloading" } }));
    const halfway = visible(
      state({ selectedChannel: "pr-12", install: { phase: "downloading", download: { received: 525_000, total: 1_050_000 }, error: null } }),
    );
    const unknownSize = visible(
      state({ selectedChannel: "pr-12", install: { phase: "downloading", download: { received: 300_000, total: null }, error: null } }),
    );

    expect(waiting.message).toBe("Downloading PR #12: Developer section…");
    expect(halfway.message).toBe("Downloading PR #12: Developer section: 50% (0.5 of 1.1 MB)");
    expect(unknownSize.message).toBe("Downloading PR #12: Developer section: 0.3 MB");
    expect(halfway.installEnabled).toBe(false);
    expect(halfway.checkEnabled).toBe(false);
  });

  it("offers to install again when the plugin is still running after the install (cancelled in Decky)", () => {
    const view = visible(state({ selectedChannel: "pr-12", install: { ...NO_INSTALL, phase: "unconfirmed" } }));

    expect(view.installEnabled).toBe(true);
    expect(view.checkEnabled).toBe(true);
    expect(view.message).toBe("The plugin was not replaced. If you cancelled in Decky, install again.");
  });

  it("says why an install could not start and lets the user try again", () => {
    const view = visible(state({ selectedChannel: "pr-12", install: { ...NO_INSTALL, error: "The pr-12 build is no longer published. Check again." } }));

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
