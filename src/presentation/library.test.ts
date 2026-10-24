import { describe, expect, it } from "vitest";
import type { LibraryVersion } from "../api";
import { LibraryState, actionOutcome, libraryMenu, libraryView, removeConfirmation } from "./library";

const installed: LibraryVersion = {
  id: "nightly-20261023", version: "10.0.0-pre1", date: "20261023", family: "10",
  state: "installed", reason: null, size: 312_400_000, default: true,
};
const available: LibraryVersion = {
  id: "nightly-20261020", version: "10.0.0-pre1", date: "20261020", family: "10",
  state: "available", reason: null, size: 75_000_000, default: false,
};
const unsupported: LibraryVersion = {
  id: "nightly-20261001", version: "9.9.0", date: "20261001", family: null,
  state: "unsupported", reason: "a version this plugin does not support yet", size: 70_000_000, default: false,
};

const state = (overrides: Partial<LibraryState> = {}): LibraryState => ({
  channel: "nightly",
  listing: { status: "success", versions: [installed, available, unsupported], listing_error: null, installed_bytes: 312_400_000 },
  checking: false,
  busy: null,
  download: null,
  message: null,
  ...overrides,
});

describe("library view", () => {
  it("lists installed versions to manage, available ones to download and unsupported ones with the reason", () => {
    const view = libraryView(state());

    expect(view.rows).toEqual([
      {
        id: "nightly-20261023", label: "10.0.0-pre1 · 2026-10-23",
        description: "Installed · 312 MB · default for new patches",
        action: { intent: "manage", label: "Manage", enabled: true },
      },
      {
        id: "nightly-20261020", label: "10.0.0-pre1 · 2026-10-20", description: "75 MB download",
        action: { intent: "download", label: "Download", enabled: true },
      },
      {
        id: "nightly-20261001", label: "9.9.0 · 2026-10-01",
        description: "Can't be installed: a version this plugin does not support yet", action: null,
      },
    ]);
    expect(view.usage).toBe("The library takes 312 MB.");
    expect(view.message).toBeNull();
    expect(view.checkEnabled).toBe(true);
    expect(view.channelEnabled).toBe(true);
  });

  it("shows a download's progress on its row and holds every other action meanwhile", () => {
    const busy = state({ busy: { id: "nightly-20261020", action: "download" }, download: { received: 29_900_000, total: 75_000_000 } });

    const view = libraryView(busy);

    expect(view.rows[1].description).toBe("Downloading: 39% of 75 MB"); // never 100% before it ends
    expect(view.rows[0].description).toBe("Installed · 312 MB · default for new patches");
    expect(view.rows.map((row) => row.action?.enabled)).toEqual([false, false, undefined]);
    expect(view.checkEnabled).toBe(false);
    expect(view.channelEnabled).toBe(false);
    expect(libraryView({ ...busy, download: null }).rows[1].description).toBe("Downloading…");
    expect(libraryView({ ...busy, download: { received: 5_000_000, total: null } }).rows[1].description).toBe(
      "Downloading: 5 MB",
    );
    expect(libraryView(state({ busy: { id: "nightly-20261023", action: "remove" } })).rows[0].description).toBe("Removing…");
  });

  it("says when GitHub could not be reached, nothing is published, or the last action's outcome", () => {
    const listing = { status: "success" as const, versions: [installed], listing_error: "GitHub answered 403", installed_bytes: 1 };
    expect(libraryView(state({ listing })).message).toBe(
      "Could not list what OptiScaler publishes (GitHub answered 403). Installed versions are shown.",
    );
    expect(libraryView(state({ listing: { ...listing, versions: [], listing_error: null } })).message).toBe(
      "No nightly versions are published.",
    );
    expect(libraryView(state({ listing: { status: "error", message: "Unknown channel: x" } })).message).toBe("Unknown channel: x");
    expect(libraryView(state({ listing, message: "OptiScaler 10.0.0-pre1 is installed." })).message).toBe(
      "OptiScaler 10.0.0-pre1 is installed.",
    );
    expect(libraryView(state({ checking: true })).checkLabel).toBe("Checking…");
    expect(libraryView(state({ listing: null })).rows).toEqual([]);
    expect(libraryView(state({ listing: { ...listing, installed_bytes: 0 } })).usage).toBeNull();
  });
});

describe("managing an installed version", () => {
  it("offers making it the default unless it is, and removing it", () => {
    expect(libraryMenu(installed)).toEqual([{ intent: "remove", label: "Remove", destructive: true }]);
    expect(libraryMenu({ ...installed, default: false })).toEqual([
      { intent: "default", label: "Use for new patches", destructive: false },
      { intent: "remove", label: "Remove", destructive: true },
    ]);
  });

  it("names the games patched with a version before removing it", () => {
    expect(removeConfirmation(installed, ["Cyberpunk 2077", "/games/Manual"])).toEqual({
      title: "Remove OptiScaler 10.0.0-pre1 · 2026-10-23?",
      lines: [
        "These stay patched with it and keep working; patching them again needs another version:",
        "Cyberpunk 2077",
        "/games/Manual",
      ],
      okLabel: "Remove",
    });
    expect(removeConfirmation(installed, []).lines).toEqual(["No game is patched with it."]);
  });

  it("reports the backend's words, or a fallback", () => {
    expect(actionOutcome({ status: "error", message: "Not enough free space" }, "Done.")).toBe("Not enough free space");
    expect(actionOutcome({ status: "success" }, "Done.")).toBe("Done.");
    expect(actionOutcome(null, "Done.")).toBe("The plugin backend did not answer.");
  });
});
