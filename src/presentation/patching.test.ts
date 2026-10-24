import { describe, expect, it } from "vitest";
import { libraryLine, patchButton } from "./patching";

describe("patch button", () => {
  it("patches with an installed OptiScaler and says why not without one", () => {
    expect(patchButton(true, "Patch with dxgi.dll")).toEqual({ label: "Patch with dxgi.dll", enabled: true });
    expect(patchButton(false, "Patch with dxgi.dll")).toEqual({
      label: "Patch: no OptiScaler version installed",
      enabled: false,
    });
  });
});

describe("library line", () => {
  it("names the default version, or says none is installed", () => {
    expect(libraryLine({ exists: true, version: "stable-0.9.4" })).toBe("Patches use stable-0.9.4, the default version in the library.");
    expect(libraryLine({ exists: false, version: null })).toMatch(/^No OptiScaler version is installed yet/);
    expect(libraryLine(null)).toMatch(/^No OptiScaler version is installed yet/);
  });
});
