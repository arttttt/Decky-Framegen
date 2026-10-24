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
  [directory: string, dll_name: string, version_id: string],
  {
    status: string;
    message?: string;
    output?: string;
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
    /** A later build of the game's version channel that is in the library. */
    newer_version?: string | null;
  }
>("get_game_status");

/** What the panel offers for starting a game; the backend builds every launch string. */
export type LaunchSetup = {
  default: string;
  proxies: { name: string; hint: string; launch_options: string }[];
  wrapper: { patch: string; unpatch: string };
};
export const launchSetup = callable<[], LaunchSetup>("launch_setup");

export const patchGame = callable<
  /** current_launch_options is null when Steam didn't say what they are. */
  [appid: string, dll_name: string, current_launch_options: string | null, version_id: string],
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
  }
>("patch_game");

export const unpatchGame = callable<
  [appid: string, current_launch_options: string, confirmed_reset: boolean],
  UnpatchResult
>("unpatch_game");

// ── OptiScaler library ───────────────────────────────────────────────────────

export type LibraryChannel = "stable" | "nightly";

/** An installed version as patching offers it. */
export type InstalledVersion = {
  id: string;
  version: string;
  channel: LibraryChannel;
  date: string;
  /** Bytes on disk. */
  size: number;
};

/** The downloaded versions, newest first, and what they take on disk. */
export type InstalledLibrary = { versions: InstalledVersion[]; installed_bytes: number };

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
};

export type LibraryListing =
  | { status: "success"; versions: LibraryVersion[]; listing_error: string | null; installed_bytes: number }
  | { status: "error"; message: string };

type LibraryResult = { status: "success"; message?: string } | { status: "error"; message: string };

export const libraryInstalled = callable<[], InstalledLibrary>("library_installed");
export const libraryVersions = callable<[channel: LibraryChannel], LibraryListing>("library_versions");
/** Download progress arrives as "library_download" events: version id, bytes received, total bytes or null. */
export const libraryInstall = callable<[channel: LibraryChannel, version_id: string], LibraryResult>("library_install");
export const libraryReinstall = callable<[version_id: string], LibraryResult>("library_reinstall");
export const libraryRemove = callable<[version_id: string], LibraryResult>("library_remove");
/** What removing a version would come to: why it can't be removed (or null) and the games patched with it. */
export type LibraryRemoval = { status: "success"; refused: string | null };
export const libraryRemoval = callable<[version_id: string], LibraryRemoval>("library_removal");

// ── Development builds ───────────────────────────────────────────────────────

/** The arguments of Decky Loader's `utilities/install_plugin`, prepared by the backend. */
export type DeckyInstallRequest = [artifact: string, name: string, version: string, hash: string, installType: number];

/** The running build: known when its package says where it came from, so it can update itself. */
export type PluginBuild =
  | { known: false; version: string; message: string }
  | {
      known: true;
      channel: string;
      commit: string;
      short_commit: string;
      title: string;
      version: string;
      is_dev_build: boolean;
      /** Development builds are offered; always on in a development build. */
      developer_mode: boolean;
    };

/** The newest release and what it means for the running build: an update, a switch from a development
 *  build, or nothing. */
export type LatestStable =
  | {
      status: "success";
      release: { version: string; title: string; published_at: string } | null;
      offer: "update" | "switch" | "none";
    }
  | { status: "error"; message: string };

export type InstallRequestAnswer =
  | { status: "success"; install_request: DeckyInstallRequest }
  | { status: "error"; message: string };

export const pluginBuild = callable<[], PluginBuild>("plugin_build");

export const setDeveloperMode = callable<[on: boolean], { status: "success"; developer_mode: boolean } | { status: "error"; message: string }>(
  "set_developer_mode",
);

export const latestStable = callable<[], LatestStable>("latest_stable");

/** Asked at install time, in case a newer release came out since the check. */
export const stableInstallRequest = callable<[], InstallRequestAnswer>("stable_install_request");

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

export const listDevBuilds = callable<[], DevBuildList>("list_dev_builds");

/** Asked at install time: a channel's build is replaced on every push and the old download is gone. */
export const devInstallRequest = callable<[channel: string], InstallRequestAnswer>("dev_install_request");

/** The backend's event for a build's download: channel, bytes received, total bytes if known. */
export const PLUGIN_DOWNLOAD_EVENT = "plugin_download";

// ── Unpatching ───────────────────────────────────────────────────────────────

/** What Unpatch will do: undo the patch record (nothing to confirm), or, for a Decky Framegen
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

// ── OptiScaler settings ──────────────────────────────────────────────────────

/** Where a setting's value comes from: OptiScaler's default ("auto"), the global settings or the game's own. */
export type SettingSource = "default" | "global" | "game";

/** A setting as a version's OptiScaler.ini describes it, with its value for the page asked for. */
export type SettingInfo = {
  key: string;
  kind: "bool" | "enum" | "number" | "text";
  description: string;
  help: string;
  /** OptiScaler's default as an ini value; null when its comment states it only in prose. */
  default: string | null;
  choices: { value: string; label: string }[];
  minimum: number | null;
  maximum: number | null;
  integer: boolean;
  value: string;
  source: SettingSource;
  /** The value without the page's own: global for a game's page, auto for the global page. */
  inherited: { value: string; source: SettingSource };
};

export type SettingsSection = { name: string; settings: SettingInfo[] };

export type SettingsAnswer = {
  status: string;
  message?: string;
  version?: string;
  sections?: SettingsSection[];
  /** "Section.Key" the layer sets that this version doesn't have or doesn't take the value of. */
  unsupported?: string[];
  /** Only for a game. */
  name?: string;
  patched?: boolean;
  running?: boolean;
};

export const globalSettings = callable<[], SettingsAnswer>("global_settings");

export const gameSettings = callable<[appid: string], SettingsAnswer>("game_settings");

/** scope is "global" or an appid; a null value clears it, so the layer below shows through. */
export const setSetting = callable<
  [scope: string, section: string, key: string, value: string | null],
  { status: string; message?: string; skipped?: string[] }
>("set_setting");

export const resetGameSettings = callable<[appid: string], { status: string; message?: string }>("reset_game_settings");

/** Writes a game's settings once it has closed; applied is false when it isn't patched or still runs. */
export const gameClosed = callable<[appid: string], { status: string; applied?: boolean }>("game_closed");

// ── Patched games ────────────────────────────────────────────────────────────

/** A game or directory the plugin patched; appid is "" for a directory patched by path. */
export type PatchedGame = {
  directory: string;
  name: string;
  appid: string;
  dll_name: string;
  dll_present: boolean;
  version_id: string | null;
  /** A later build of the game's version channel that is in the library. */
  newer_version: string | null;
  patched_at: string | null;
  record: "ok" | "incomplete" | "upstream";
  own_settings: boolean;
};

export const patchedGames = callable<[], { status: string; message?: string; games?: PatchedGame[] }>("patched_games");
