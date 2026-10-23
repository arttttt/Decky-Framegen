import { callable } from "@decky/api";

export const checkFGModPath = callable<[], { exists: boolean; version: string | null }>("check_fgmod_path");

export const listInstalledGames = callable<
  [],
  { status: string; message?: string; games: { appid: string; name: string; install_found?: boolean }[] }
>("list_installed_games");

export const logError = callable<[string], void>("log_error");

export const getPathDefaults = callable<
  [],
  { home: string; steam_common?: string }
>("get_path_defaults");

export const runManualPatch = callable<
  [string, string, string],
  {
    status: string;
    message?: string;
    output?: string;
    fsr4_variant?: string;
    fsr4_variant_label?: string;
    optiscaler_version?: string | null;
  }
>("manual_patch_directory");

export const runManualUnpatch = callable<
  [string],
  { status: string; message?: string; output?: string }
>("manual_unpatch_directory");

export const getGameStatus = callable<
  [appid: string],
  {
    status: string;
    message?: string;
    appid?: string;
    name?: string;
    install_found?: boolean;
    patched?: boolean;
    dll_name?: string | null;
    target_dir?: string | null;
    patched_at?: string | null;
    optiscaler_version?: string | null;
    fsr4_variant?: string | null;
    fsr4_variant_label?: string | null;
  }
>("get_game_status");

export const patchGame = callable<
  [appid: string, dll_name: string, current_launch_options: string, fsr4_variant: string],
  {
    status: string;
    message?: string;
    appid?: string;
    name?: string;
    dll_name?: string;
    target_dir?: string;
    launch_options?: string;
    original_launch_options?: string;
    optiscaler_version?: string | null;
    fsr4_variant?: string;
    fsr4_variant_label?: string;
  }
>("patch_game");

export const unpatchGame = callable<
  [appid: string],
  {
    status: string;
    message?: string;
    appid?: string;
    name?: string;
    launch_options?: string;
  }
>("unpatch_game");

// ── Development builds ───────────────────────────────────────────────────────

/** The arguments of Decky Loader's `utilities/install_plugin`, prepared by the backend. */
export type DeckyInstallRequest = [artifact: string, name: string, version: string, hash: string, installType: number];

export type DevBuild =
  | { is_dev_build: false }
  | { is_dev_build: true; channel: string; commit: string; short_commit: string; title: string };

export type AvailableDevBuild = {
  channel: string;
  commit: string;
  short_commit: string;
  title: string;
  published_at: string;
  state: "installed" | "available";
};

export type DevBuildList =
  | { status: "success"; builds: AvailableDevBuild[] }
  | { status: "error"; message: string };

export const getDevBuild = callable<[], DevBuild>("get_dev_build");

export const listDevBuilds = callable<[], DevBuildList>("list_dev_builds");

/** Asked at install time: a channel's build is replaced on every push and the old download is gone. */
export const devInstallRequest = callable<
  [channel: string],
  { status: "success"; install_request: DeckyInstallRequest } | { status: "error"; message: string }
>("dev_install_request");

// ── Reset to stock ───────────────────────────────────────────────────────────

export type ResetPreview =
  | {
      status: "success";
      target_dir: string;
      evidence: "marker" | "backups" | "leftovers";
      remove: string[];
      restore: string[];
      unrecoverable: string[];
      /** The launch options to set afterwards; null leaves them as they are. */
      launch_options: string | null;
      name?: string;
      message?: string;
    }
  | { status: "error"; message: string };

export const previewResetGame = callable<[appid: string, current_launch_options: string], ResetPreview>(
  "preview_reset_game"
);
export const resetGame = callable<[appid: string, current_launch_options: string], ResetPreview>("reset_game");
export const previewResetDirectory = callable<[directory: string], ResetPreview>("preview_reset_directory");
export const resetDirectory = callable<[directory: string], ResetPreview>("reset_directory");
