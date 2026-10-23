import { describe, expect, it } from "vitest";
import { patchButton } from "./patching";

describe("patch button", () => {
  it("patches with an installed OptiScaler and says why not without one", () => {
    expect(patchButton(true, "Patch with dxgi.dll")).toEqual({ label: "Patch with dxgi.dll", enabled: true });
    expect(patchButton(false, "Patch with dxgi.dll")).toEqual({
      label: "Patch: OptiScaler is not installed",
      enabled: false,
    });
  });
});
