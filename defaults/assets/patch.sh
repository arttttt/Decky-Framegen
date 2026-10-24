#!/usr/bin/env bash
# Launch wrapper: patches the game with OptiScaler, then starts it.
#   Steam launch options: ~/deckyscaler/patch %command%
#   Heroic: add ~/deckyscaler/patch as a wrapper
# Patching is done by the plugin's Python core (~/deckyscaler/deckyscaler); this script
# only launches the game.

set -x
exec > >(tee -i /tmp/deckyscaler-patch.log) 2>&1

error_exit() {
  echo " $1"
  if [[ -n $STEAM_ZENITY ]]; then
    $STEAM_ZENITY --error --text "$1"
  else
    zenity --error --text "$1" || echo "Zenity failed to display error"
  fi
  logger -t deckyscaler "ERROR: $1"
  exit 1
}

plugin_home="$HOME/deckyscaler"
python_bin="$(command -v python3 || command -v python || true)"

# The plugin's core, installed next to this script.
core() {
  PYTHONPATH="$plugin_home" "$python_bin" -m deckyscaler "$@"
}

[[ "$#" -lt 1 ]] && error_exit "Usage: $0 program [program_arguments...]"
[[ -z "$python_bin" ]] && error_exit "Python 3 is required to patch games but was not found."

dll_args=()
[[ -n "${DLL:-}" ]] && dll_args=(--dll "$DLL")
# DECKYSCALER_VERSION picks a library version (e.g. nightly-20261023); unset keeps the one the game is patched with, else the newest.
patch_args=(patch "${dll_args[@]}" --version "${DECKYSCALER_VERSION:-}")
[[ "${PRESERVE_INI:-true}" == "true" ]] || patch_args+=(--reset-ini)
if ! exe_folder_path="$(core "${patch_args[@]}" -- "$@")"; then
  error_exit "${exe_folder_path:-Patching failed. See /tmp/deckyscaler-patch.log.}"
fi
logger -t deckyscaler "Patched $exe_folder_path"

if [[ $# -gt 1 ]]; then
  export SteamDeck=0
  # Load the proxy DLL natively, keeping any overrides already set.
  WINEDLLOVERRIDES="$(core wine-overrides "${dll_args[@]}")"
  export WINEDLLOVERRIDES
  # Drop leading -- separators from Steam launch options.
  while [[ $# -gt 0 && "$1" == "--" ]]; do
    shift
  done
  exec >/dev/null 2>&1
  "$@"
fi
