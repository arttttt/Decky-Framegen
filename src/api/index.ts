import { callable } from "@decky/api";

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
  [directory: string, dll_name: string, fsr4_variant: string, version_id: string],
  {
    status: string;
    message?: string;
    output?: string;
    fsr4_variant?: string;
    fsr4_variant_label?: string;
    optiscaler_version?: string | null;
  }
>("manual_patch_directory");

export const runManualUnpatch = callable<[directory: string, confirmed_reset: boolean], UnpatchResult>(
  "manual_unpatch_directory"
);

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
    /** A later build of the game's version channel that is in the library. */
    newer_version?: string | null;
  }
>("get_game_status");

export const patchGame = callable<
  [appid: string, dll_name: string, current_launch_options: string, fsr4_variant: string, version_id: string],
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
  [appid: string, current_launch_options: string, confirmed_reset: boolean],
  UnpatchResult
>("unpatch_game");

// ── OptiScaler library ───────────────────────────────────────────────────────

export type LibraryChannel = "stable" | "nightly";

/** An installed version as patching offers it; its family's FSR 4 variants, the default first. */
export type InstalledVersion = {
  id: string;
  version: string;
  channel: LibraryChannel;
  date: string;
  variants: { id: string; label: string }[];
};

export type InstalledLibrary = { default: string | null; versions: InstalledVersion[] };

export type LibraryVersion = {
  id: string;
  version: string;
  date: string;
  family: string | null;
  state: "installed" | "available" | "unsupported";
  /** Why an unsupported version can't be installed. */
  reason: string | null;
  /** Bytes on disk for an installed version, the download size otherwise. */
  size: number;
  default: boolean;
};

export type LibraryListing =
  | { status: "success"; versions: LibraryVersion[]; listing_error: string | null; installed_bytes: number }
  | { status: "error"; message: string };

type LibraryResult = { status: "success"; message?: string } | { status: "error"; message: string };

export const libraryInstalled = callable<[], InstalledLibrary>("library_installed");
export const libraryVersions = callable<[channel: LibraryChannel], LibraryListing>("library_versions");
/** Download progress arrives as "library_download" events: version id, bytes received, total bytes or null. */
export const libraryInstall = callable<[channel: LibraryChannel, version_id: string], LibraryResult>("library_install");
export const libraryRemove = callable<[version_id: string], LibraryResult>("library_remove");
export const librarySetDefault = callable<[version_id: string], LibraryResult>("library_set_default");
export const libraryGamesUsing = callable<[version_id: string], { status: "success"; games: string[] }>(
  "library_games_using"
);

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

// ── Unpatching ───────────────────────────────────────────────────────────────

/** What Unpatch will do: undo the patch record (nothing to confirm), or, for an older plugin
 *  version's patch, a reset the user confirms after seeing what it changes. */
export type UnpatchPreview =
  | { status: "success"; mode: "record"; target_dir: string; name?: string }
  | {
      status: "success";
      mode: "reset";
      target_dir: string;
      evidence: "marker" | "backups" | "leftovers";
      remove: string[];
      restore: string[];
      unrecoverable: string[];
      /** The launch options to set afterwards; null leaves them as they are. */
      launch_options: string | null;
      name?: string;
    }
  | { status: "error"; message: string };

export type UnpatchResult =
  | { status: "success"; message?: string; launch_options?: string | null }
  | { status: "error"; message: string };

export const previewUnpatchGame = callable<[appid: string, current_launch_options: string], UnpatchPreview>(
  "preview_unpatch_game"
);
export const previewUnpatchDirectory = callable<[directory: string], UnpatchPreview>("preview_unpatch_directory");
