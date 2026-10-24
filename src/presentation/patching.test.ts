import { describe, expect, it } from "vitest";
import type { InstalledLibrary } from "../api";
import { gameVersionLine, libraryReady, patchButton, patchChoice } from "./patching";

const LIBRARY: InstalledLibrary = {
  default: "stable-0.9.4",
  versions: [
    {
      id: "nightly-20261023",
      version: "10.0.0-pre1",
      channel: "nightly",
      date: "20261023",
      variants: [
        { id: "auto", label: "Automatic" },
        { id: "int8", label: "INT8" },
      ],
    },
    {
      id: "stable-0.9.4",
      version: "0.9.4",
      channel: "stable",
      date: "20260718",
      variants: [
        { id: "sdk", label: "SDK" },
        { id: "sdk-int8", label: "SDK, INT8 forced" },
      ],
    },
  ],
};

describe("patch button", () => {
  it("patches with an installed OptiScaler and says why not without one", () => {
    expect(patchButton(true, "Patch with dxgi.dll")).toEqual({ label: "Patch with dxgi.dll", enabled: true });
    expect(patchButton(false, "Patch with dxgi.dll")).toEqual({
      label: "Patch: no OptiScaler version installed",
      enabled: false,
    });
  });
});

describe("library readiness", () => {
  it("is unknown until the library answers, then whether any version is installed", () => {
    expect(libraryReady(null)).toBeNull();
    expect(libraryReady({ default: null, versions: [] })).toBe(false);
    expect(libraryReady(LIBRARY)).toBe(true);
  });
});

describe("patch choice", () => {
  it("starts on the default version and its family's default variant", () => {
    const view = patchChoice(LIBRARY, { versionId: null, variant: null });

    expect(view.versionId).toBe("stable-0.9.4");
    expect(view.variant).toBe("sdk");
    expect(view.variantOptions).toEqual([
      { data: "sdk", label: "SDK" },
      { data: "sdk-int8", label: "SDK, INT8 forced" },
    ]);
    expect(view.versionOptions).toEqual([
      { data: "nightly-20261023", label: "10.0.0-pre1 · 2026-10-23 (nightly)" },
      { data: "stable-0.9.4", label: "0.9.4 · 2026-07-18 (stable), default" },
    ]);
    expect(view.ready).toBe(true);
    expect(view.versionHint).toBeNull();
    expect(view.patchWith).toEqual({ versionId: "stable-0.9.4", variant: "sdk" });
  });

  it("keeps a picked variant only while the picked version's family has it", () => {
    expect(patchChoice(LIBRARY, { versionId: "nightly-20261023", variant: "int8" }).variant).toBe("int8");
    expect(patchChoice(LIBRARY, { versionId: "nightly-20261023", variant: "sdk-int8" }).variant).toBe("auto");
  });

  it("falls back to the default when the picked version is gone, and to the newest without a default", () => {
    expect(patchChoice(LIBRARY, { versionId: "nightly-20250101", variant: null }).versionId).toBe("stable-0.9.4");
    expect(patchChoice({ ...LIBRARY, default: null }, { versionId: null, variant: null }).versionId).toBe(
      "nightly-20261023",
    );
  });

  it("offers nothing and says where to get a version when the library is empty", () => {
    for (const library of [null, { default: null, versions: [] }]) {
      const view = patchChoice(library, { versionId: "stable-0.9.4", variant: "sdk" });
      expect(view).toMatchObject({
        versionId: null, variant: null, ready: false, versionOptions: [], variantOptions: [],
        patchWith: { versionId: "", variant: "" },
      });
      expect(view.versionHint).toMatch(/OptiScaler library section/);
    }
  });
});

describe("game version line", () => {
  it("names what a patched game runs and a newer build of its channel", () => {
    const patched = { patched: true, optiscaler_version: "nightly-20261023", fsr4_variant_label: "INT8" };

    expect(gameVersionLine(patched)).toBe("nightly-20261023: INT8");
    expect(gameVersionLine({ ...patched, newer_version: "nightly-20261101" })).toBe(
      "nightly-20261023: INT8. nightly-20261101 is in the library; choose it and patch again to update.",
    );
    expect(gameVersionLine({ patched: false })).toBeNull();
    expect(gameVersionLine(null)).toBeNull();
  });
});
