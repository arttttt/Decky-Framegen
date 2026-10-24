import type { LatestStable, PluginBuild } from "../api";
import { DECKY_INSTALLER_UNREACHABLE, InstallState, canStartInstall, installMessage } from "./install";

/** The running build and the last check for a release, shared by the Quick Access panel and the page. */
export type UpdatesCheck = { build: PluginBuild | null; checking: boolean; latest: LatestStable | null };

export type UpdatesState = UpdatesCheck & { install: InstallState; deckyInstallerAvailable: boolean };

export type UpdatesView = {
  running: string;
  checkLabel: string;
  checkEnabled: boolean;
  /** What the last check found; null before the first. */
  releaseLine: string | null;
  install: { visible: boolean; label: string; enabled: boolean };
  developerMode: { visible: boolean; on: boolean; enabled: boolean; description: string };
  message: string | null;
};

const releaseLine = (latest: LatestStable | null): string | null => {
  if (latest === null) return null;
  if (latest.status === "error") return latest.message;
  if (latest.release === null) return "No release is published yet.";
  if (latest.offer === "update") return `${latest.release.title} is available.`;
  if (latest.offer === "switch") return `The newest release is ${latest.release.title}.`;
  return "Up to date.";
};

const installLabel = (latest: Extract<LatestStable, { status: "success" }>): string =>
  latest.offer === "switch" ? `Switch to ${latest.release?.title}` : `Install ${latest.release?.title}`;

/** What the Updates section shows: the running build, the newest release with an update or a switch
 *  to it, and Developer mode. */
export const updatesView = (state: UpdatesState): UpdatesView => {
  const { build, checking, latest, install } = state;
  const known = build?.known === true;
  const offer = latest?.status === "success" && latest.offer !== "none" ? latest : null;
  const downloading = install.phase === "downloading";
  return {
    running: build === null ? "Loading…" : build.known ? `Running ${build.title}` : build.message,
    checkLabel: checking ? "Checking…" : "Check for updates",
    checkEnabled: known && !checking && !downloading,
    releaseLine: releaseLine(latest),
    install: {
      visible: offer !== null,
      label: offer ? installLabel(offer) : "",
      enabled: offer !== null && state.deckyInstallerAvailable && canStartInstall(install) && !checking,
    },
    developerMode: {
      visible: known,
      on: build?.known === true && build.developer_mode,
      enabled: build?.known === true && !build.is_dev_build,
      description:
        build?.known === true && build.is_dev_build
          ? "On in a development build. Switch to a release to turn it off."
          : "Offers development builds: unreviewed, and they may break things.",
    },
    message:
      installMessage(install, offer?.release?.title ?? "the release") ??
      (offer && !state.deckyInstallerAvailable ? DECKY_INSTALLER_UNREACHABLE : null),
  };
};

/** The Quick Access panel's line when a newer release is out; nothing for a switch from a development build. */
export const updateAvailableLine = (check: UpdatesCheck): string | null =>
  check.latest?.status === "success" && check.latest.offer === "update" && check.latest.release
    ? `${check.latest.release.title} is available.`
    : null;

/** Asked before Developer mode turns on, as Decky's own developer options warn. */
export const DEVELOPER_MODE_CONFIRMATION = {
  title: "Turn on Developer mode?",
  lines: [
    "Developer mode offers development builds of the plugin: builds of main and of pull requests, not reviewed and not released.",
    "They may not work, and may break patched games. You take that on yourself.",
    "Switching back to a release is one press under Updates.",
  ],
  okLabel: "Turn on",
};
