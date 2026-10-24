import { describe, expect, it } from "vitest";
import { staleActivePlugin } from "./pluginReload";

describe("stale active plugin", () => {
  const old = { name: "DeckyScaler" };
  const reloaded = { name: "DeckyScaler" };
  const other = { name: "Other" };

  it("names the open plugin when a reload replaced its object in the list", () => {
    expect(staleActivePlugin(old, [other, reloaded])).toBe("DeckyScaler");
  });

  it("leaves a current, closed, or uninstalled plugin alone", () => {
    expect(staleActivePlugin(reloaded, [other, reloaded])).toBeNull();
    expect(staleActivePlugin(null, [reloaded])).toBeNull();
    expect(staleActivePlugin(undefined, [reloaded])).toBeNull();
    expect(staleActivePlugin(old, [other])).toBeNull();
  });
});
