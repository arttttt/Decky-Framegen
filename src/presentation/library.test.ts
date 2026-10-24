import { describe, expect, it } from "vitest";
import type { InstalledLibrary, LibraryRemoval, LibraryVersion } from "../api";
import {
  DownloadState,
  ManageState,
  actionOutcome,
  downloadView,
  librarySummary,
  manageDone,
  MANAGE_MENU,
  manageView,
  removeConfirmation,
} from "./library";

const downloaded: LibraryVersion = {
  id: "nightly-20261023", version: "10.0.0-pre1", date: "20261023", family: "10",
  state: "installed", reason: null, size: 312_400_000,
};
const available: LibraryVersion = {
  id: "nightly-20261020", version: "10.0.0-pre1", date: "20261020", family: "10",
  state: "available", reason: null, size: 75_000_000,
};
const unsupported: LibraryVersion = {
  id: "nightly-20261001", version: "9.9.0", date: "20261001", family: null,
  state: "unsupported", reason: "a version this plugin does not support yet", size: 70_000_000,
};

const removal = (refused: string | null, games: string[]): LibraryRemoval => ({ status: "success", refused, games });

const LIBRARY: InstalledLibrary = {
  installed_bytes: 512_000_000,
  versions: [
    { id: "nightly-20261023", version: "10.0.0-pre1", channel: "nightly", date: "20261023", size: 312_000_000 },
    { id: "stable-0.9.4", version: "0.9.4", channel: "stable", date: "20260718", size: 200_000_000 },
  ],
};

describe("panel summary", () => {
  it("counts the downloaded versions and names the newest", () => {
    expect(librarySummary(LIBRARY)).toBe("2 versions downloaded. Newest: 10.0.0-pre1 · 2026-10-23.");
    expect(librarySummary({ ...LIBRARY, versions: LIBRARY.versions.slice(1) })).toBe(
      "1 version downloaded. Newest: 0.9.4 · 2026-07-18.",
    );
    expect(librarySummary({ versions: [], installed_bytes: 0 })).toBe("No version is downloaded yet.");
    expect(librarySummary(null)).toBe("Loading…");
  });
});

const downloadState = (overrides: Partial<DownloadState> = {}): DownloadState => ({
  channel: "nightly",
  listing: { status: "success", versions: [downloaded, available, unsupported], listing_error: null, installed_bytes: 1 },
  checking: false,
  busy: null,
  download: null,
  message: null,
  ...overrides,
});

describe("download dialog", () => {
  it("offers what is published, marks what is downloaded and says why the rest can't be", () => {
    const view = downloadView(downloadState());

    expect(view.rows).toEqual([
      { id: "nightly-20261023", label: "10.0.0-pre1 · 2026-10-23", description: "Downloaded", action: null },
      {
        id: "nightly-20261020", label: "10.0.0-pre1 · 2026-10-20", description: "75 MB download",
        action: { label: "Download", enabled: true },
      },
      {
        id: "nightly-20261001", label: "9.9.0 · 2026-10-01",
        description: "Can't be downloaded: a version this plugin does not support yet", action: null,
      },
    ]);
    expect(view).toMatchObject({ channelEnabled: true, checkEnabled: true, message: null, checkLabel: "Check for new versions" });
  });

  it("shows a download's progress on its row and holds everything else meanwhile", () => {
    const busy = downloadState({ busy: "nightly-20261020", download: { received: 29_900_000, total: 75_000_000 } });

    const view = downloadView(busy);

    expect(view.rows[1]).toMatchObject({ description: "Downloading: 39% of 75 MB", action: { enabled: false } });
    expect(view.rows[0].description).toBe("Downloaded");
    expect(view).toMatchObject({ channelEnabled: false, checkEnabled: false });
    expect(downloadView({ ...busy, download: null }).rows[1].description).toBe("Downloading…");
    expect(downloadView({ ...busy, download: { received: 5_000_000, total: null } }).rows[1].description).toBe(
      "Downloading: 5 MB",
    );
  });

  it("says when GitHub could not be reached, nothing is published, or how the last download went", () => {
    const listing = { status: "success" as const, versions: [], listing_error: "GitHub answered 403", installed_bytes: 0 };
    expect(downloadView(downloadState({ listing })).message).toBe("Could not list what OptiScaler publishes (GitHub answered 403).");
    expect(downloadView(downloadState({ listing: { ...listing, listing_error: null } })).message).toBe(
      "No nightly versions are published.",
    );
    expect(downloadView(downloadState({ listing: { status: "error", message: "Unknown channel: x" } })).message).toBe(
      "Unknown channel: x",
    );
    expect(downloadView(downloadState({ listing, message: "OptiScaler 10.0.0-pre1 is installed." })).message).toBe(
      "OptiScaler 10.0.0-pre1 is installed.",
    );
    expect(downloadView(downloadState({ checking: true }))).toMatchObject({ checkLabel: "Checking…", checkEnabled: false });
    expect(downloadView(downloadState({ listing: null })).rows).toEqual([]);
  });
});

const manageState = (overrides: Partial<ManageState> = {}): ManageState => ({
  library: LIBRARY,
  busy: null,
  download: null,
  message: null,
  ...overrides,
});

describe("manage dialog", () => {
  it("lists downloaded versions with channel and size, and the total", () => {
    const view = manageView(manageState());

    expect(view.rows).toEqual([
      { id: "nightly-20261023", label: "10.0.0-pre1 · 2026-10-23", description: "Nightly · 312 MB", action: { label: "Manage", enabled: true } },
      {
        id: "stable-0.9.4", label: "0.9.4 · 2026-07-18", description: "Stable · 200 MB",
        action: { label: "Manage", enabled: true },
      },
    ]);
    expect(view.usage).toBe("Downloaded versions take 512 MB.");
    expect(view.message).toBeNull();
  });

  it("shows what is happening to a version on its row and holds the others", () => {
    const reinstalling = manageView(
      manageState({ busy: { id: "nightly-20261023", action: "reinstall" }, download: { received: 10_000_000, total: 100_000_000 } }),
    );
    expect(reinstalling.rows[0].description).toBe("Downloading: 10% of 100 MB");
    expect(reinstalling.rows[1]).toMatchObject({ description: "Stable · 200 MB", action: { enabled: false } });
    expect(manageView(manageState({ busy: { id: "stable-0.9.4", action: "remove" } })).rows[1].description).toBe("Removing…");
  });

  it("says when nothing is downloaded, and how the last action went", () => {
    const empty = manageView(manageState({ library: { versions: [], installed_bytes: 0 } }));
    expect(empty).toEqual({ rows: [], usage: null, message: "No version is downloaded yet." });
    expect(manageView(manageState({ library: null }))).toEqual({ rows: [], usage: null, message: null });
    expect(manageView(manageState({ message: "Removing failed: busy" })).message).toBe("Removing failed: busy");
  });

  it("offers downloading a version again and removing it, the removal marked destructive", () => {
    expect(MANAGE_MENU).toEqual([
      { action: "reinstall", label: "Download again", destructive: false },
      { action: "remove", label: "Remove", destructive: true },
    ]);
  });

  it("names the games patched with a version before removing it", () => {
    expect(removeConfirmation(LIBRARY.versions[0], removal(null, ["Cyberpunk 2077", "/games/Manual"]))).toEqual({
      title: "Remove OptiScaler 10.0.0-pre1 · 2026-10-23?",
      lines: [
        "These stay patched with it and keep working; patching them again needs another version:",
        "Cyberpunk 2077",
        "/games/Manual",
      ],
      okLabel: "Remove",
      removes: true,
    });
    expect(removeConfirmation(LIBRARY.versions[0], removal(null, [])).lines).toEqual(["No game is patched with it."]);
  });

  it("says why a version can't be removed before asking, instead of the question", () => {
    expect(removeConfirmation(LIBRARY.versions[0], removal("Game use it through links. Unpatch them first.", ["Game"]))).toEqual({
      title: "Can't remove OptiScaler 10.0.0-pre1 · 2026-10-23",
      lines: ["Game use it through links. Unpatch them first."],
      okLabel: "OK",
      removes: false,
    });
    expect(removeConfirmation(LIBRARY.versions[0], null)).toMatchObject({
      lines: ["The plugin backend did not answer."],
      removes: false,
    });
  });

  it("reports the backend's words, or what the action did", () => {
    expect(actionOutcome({ status: "error", message: "Not enough free space" }, "Done.")).toBe("Not enough free space");
    expect(actionOutcome({ status: "success" }, manageDone("remove", "stable-0.9.4"))).toBe("stable-0.9.4 is removed.");
    expect(manageDone("reinstall", "x")).toBe("x is downloaded again.");
    expect(manageDone("remove", "x")).toBe("x is removed.");
    expect(actionOutcome(null, "Done.")).toBe("The plugin backend did not answer.");
  });
});
