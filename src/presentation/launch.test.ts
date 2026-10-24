import { describe, expect, it } from "vitest";
import type { LaunchSetup } from "../api";
import { patchReady, proxyDllView } from "./launch";

const SETUP: LaunchSetup = {
  default: "dxgi.dll",
  proxies: [
    { name: "dxgi.dll", hint: "Works for most DX12 games.", launch_options: "WINEDLLOVERRIDES=dxgi=n,b SteamDeck=0 %command%" },
    { name: "OptiScaler.asi", hint: "For ASI loaders.", launch_options: "SteamDeck=0 %command%" },
  ],
  wrapper: { patch: "~/fgmod/fgmod %command%", unpatch: "~/fgmod/fgmod-uninstaller.sh %command%" },
};

describe("proxy DLL picker", () => {
  it("starts on the backend's default and marks it in the list", () => {
    const view = proxyDllView(SETUP, null);

    expect(view.selected).toBe("dxgi.dll");
    expect(view.options).toEqual([
      { data: "dxgi.dll", label: "dxgi.dll (default)" },
      { data: "OptiScaler.asi", label: "OptiScaler.asi" },
    ]);
    expect(view.hint).toBe("Works for most DX12 games.");
    expect(view.launchOptions).toBe("WINEDLLOVERRIDES=dxgi=n,b SteamDeck=0 %command%");
    expect(view.wrapper).toEqual(SETUP.wrapper);
  });

  it("follows the picked proxy, and falls back to the default for one no longer offered", () => {
    expect(proxyDllView(SETUP, "OptiScaler.asi")).toMatchObject({ selected: "OptiScaler.asi", launchOptions: "SteamDeck=0 %command%" });
    expect(proxyDllView(SETUP, "gone.dll").selected).toBe("dxgi.dll");
  });

  it("offers nothing until the backend answers, and patching waits for it", () => {
    const empty = proxyDllView(null, "dxgi.dll");

    expect(empty).toEqual({ options: [], selected: null, hint: null, launchOptions: null, wrapper: null });
    expect(patchReady(true, empty)).toBe(false);
    expect(patchReady(true, proxyDllView(SETUP, null))).toBe(true);
    expect(patchReady(false, proxyDllView(SETUP, null))).toBe(false);
  });
});
