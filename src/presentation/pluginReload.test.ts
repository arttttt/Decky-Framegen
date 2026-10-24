import { describe, expect, it } from "vitest";
import { staleActivePlugin } from "./pluginReload";

describe("stale active plugin", () => {
  const old = { name: "Decky-Framegen" };
  const reloaded = { name: "Decky-Framegen" };
  const other = { name: "Other" };

  it("names the open plugin when a reload replaced its object in the list", () => {
    expect(staleActivePlugin(old, [other, reloaded])).toBe("Decky-Framegen");
  });

  it("leaves a current, closed, or uninstalled plugin alone", () => {
    expect(staleActivePlugin(reloaded, [other, reloaded])).toBeNull();
    expect(staleActivePlugin(null, [reloaded])).toBeNull();
    expect(staleActivePlugin(undefined, [reloaded])).toBeNull();
    expect(staleActivePlugin(old, [other])).toBeNull();
  });
});
