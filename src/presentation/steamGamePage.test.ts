import { describe, expect, it } from "vitest";
import { appIdFromLibraryPath } from "./steamGamePage";

describe("Steam game page", () => {
  it("reads the game from a library page's path, and nothing from other pages", () => {
    expect(appIdFromLibraryPath("/routes/library/app/1091500")).toBe("1091500");
    expect(appIdFromLibraryPath("/library/app/730/achievements")).toBe("730");
    expect(appIdFromLibraryPath("/library/home")).toBeNull();
    expect(appIdFromLibraryPath("/library/app/not-a-number")).toBeNull();
  });
});
