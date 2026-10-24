import { describe, expect, it } from "vitest";
import { appIdFromLibraryPath, isSteamGame } from "./steamGamePage";

describe("Steam game page", () => {
  it("reads the game from a library page's path, and nothing from other pages", () => {
    expect(appIdFromLibraryPath("/routes/library/app/1091500")).toBe("1091500");
    expect(appIdFromLibraryPath("/library/app/730/achievements")).toBe("730");
    expect(appIdFromLibraryPath("/library/home")).toBeNull();
    expect(appIdFromLibraryPath("/library/app/not-a-number")).toBeNull();
  });
});

describe("game context menu", () => {
  it("is offered for Steam games, not for non-Steam shortcuts", () => {
    expect(isSteamGame(1091500)).toBe(true);
    expect(isSteamGame(0x80000000 + 12345)).toBe(false);
    expect(isSteamGame(0)).toBe(false);
  });
});
