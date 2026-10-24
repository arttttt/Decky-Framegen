import { describe, expect, it } from "vitest";
import { appIdFromLibraryPath, chipTop } from "./steamGamePage";

describe("Steam game page", () => {
  it("reads the game from a library page's path, and nothing from other pages", () => {
    expect(appIdFromLibraryPath("/routes/library/app/1091500")).toBe("1091500");
    expect(appIdFromLibraryPath("/library/app/730/achievements")).toBe("730");
    expect(appIdFromLibraryPath("/library/home")).toBeNull();
    expect(appIdFromLibraryPath("/library/app/not-a-number")).toBeNull();
  });
});

describe("game page chip", () => {
  it("stacks under other plugins' badges in the header's left half, else takes their usual place", () => {
    expect(chipTop([], 1280)).toBe(40);
    expect(chipTop([{ left: 20, top: 40, bottom: 76 }], 1280)).toBe(84);
    expect(chipTop([{ left: 20, top: 40, bottom: 76 }, { left: 20, top: 84, bottom: 110 }], 1280)).toBe(118);
    expect(chipTop([{ left: 1100, top: 60, bottom: 96 }], 1280)).toBe(40); // a badge on the right doesn't count
    expect(chipTop([{ left: 20, top: 40, bottom: 40 }], 1280)).toBe(40); // nor one with nothing in it yet
  });
});
