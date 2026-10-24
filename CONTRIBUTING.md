# Contributing

## Workflow

- `main` is protected and always releasable. Work happens on a short-lived branch per change (`feat/…`, `fix/…`, `ci/…`, `docs/…`, `refactor/…`).
- Every change lands through a pull request into `main`, merged with a merge commit once CI is green and review findings are resolved.
- Releases are tags on `main` (`vX.Y`).
- Commits are atomic and say what changed and why; the pull request description says the same for the whole change and how it was tested.

## Tests

CI runs everything below on every pull request and on `main`.

| What | Command |
|---|---|
| Backend (pytest) | `.venv/bin/python -m pytest` |
| Frontend type-check and unit tests (vitest) | `pnpm run typecheck && pnpm test` |
| Frontend build | `pnpm run build` |
| Launch scripts | `shellcheck defaults/assets/*.sh` |
| Plugin package | built with Decky CLI and checked by `tests/test_package.py` (CI only) |

Backend setup (Python 3.10+; Decky Loader ships 3.14):

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest
```

The backend tests use a fake `~/fgmod`, fake game directories, a fake Steam library and a local stand-in for the GitHub API, all in temporary directories; no device or Decky Loader is needed.

The tests for the bash launch wrappers (`tests/test_wrapper_scripts.py`) run on Linux only (bash 5, GNU coreutils). On macOS, run them in a container:

```bash
docker run --rm -v "$PWD":/src -w /src python:3.14-slim \
  bash -c "apt-get update -qq && apt-get install -qq -y procps >/dev/null && pip install -q -r requirements-dev.txt && python -m pytest tests/test_wrapper_scripts.py"
```

## Testing on a device

CI publishes a development build of the plugin for `main` and for every open pull request from this repository:

| Build | Release | Updated |
|---|---|---|
| Latest `main` | [`dev`](../../releases/tag/dev) | on every merge |
| Pull request #N | `pr-N` | on every push to it; deleted when it closes |

Development builds carry a **Developer** section in the plugin; release builds never show it.

### First install

1. In Decky: **Settings → General → Developer mode** on.
2. **Settings → Developer → Install Plugin from URL**, paste the zip URL of the `dev` release (Releases page → `dev` → right-click the `Decky-Framegen-<commit>.zip` asset → copy link).
3. Confirm. The plugin appears with a **Developer** section showing `Running main @ <commit>`.

### Switching builds

1. Open the plugin → **Developer** → **Check for builds**.
2. Pick a build (main or a pull request) → **Install**. The plugin downloads it (progress shows in the section), then Decky asks to confirm.
3. Decky replaces the plugin and reloads it; the section then shows the new build as running.

If you cancel Decky's confirmation, the section offers to install again after a few seconds.

Switching back to `main` works the same way.

### What to know

- Installing replaces the plugin directory only. `~/fgmod`, patched games and their markers are untouched; the plugin must never define an `_uninstall` hook, because Decky runs it on every update (a test enforces this).
- Development builds contain no OptiScaler. Until OptiScaler versions can be downloaded from the plugin, an existing `~/fgmod` keeps working for patching.
- After each install Decky puts the plugin back at the end of the Quick Access menu.
- Installing from a URL makes Decky send an install-count request to its store; it does nothing for a plugin that is not in the store.
- Logs: Decky's plugin log at `~/homebrew/logs/Decky-Framegen/`, the launch wrappers at `/tmp/fgmod-install.log` and `/tmp/fgmod-uninstaller.log`.

### Device checklist for a pull request

Run on the device before merging anything that changes what the device sees:

1. Install the pull request's build from the Developer section; it shows as running after the reload.
2. Exercise the change itself.
3. `~/fgmod`, patched games and their `FRAMEGEN_PATCH` markers are unchanged by the install.
4. Switch back to `main` from the Developer section.
5. Gamepad only: every row of the changed sections can be reached and used.

## Releasing

Run **Actions → Release → Run workflow** on `main`. Nothing to type: the release is named after the
day, as a calendar version (`2026.10.24`; a second release that day is `2026.10.24.1`). The workflow
stamps that version into the build (`scripts/stamp_release.py`, `framegen.domain.release_version`),
builds a release build (no Developer section), checks the package, and publishes `Decky-Framegen.zip`
as the GitHub Release `v<version>` on main's current commit, with generated notes.

`package.json`'s `version` stays `0.0.0`: every published build gets its version stamped. Development
builds carry the build day too, then their channel and commit (`2026.10.24-dev.1a2b3c4`).
