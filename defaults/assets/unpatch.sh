#!/usr/bin/env bash
# Launch wrapper: removes OptiScaler from the game, then starts it.
#   Steam launch options: ~/deckyscaler/unpatch %command%
# Unpatching is done by the plugin's Python core (~/deckyscaler/deckyscaler); this script
# only launches the game. Running the game once is enough; the launch option can
# be removed afterwards.

set -x
exec > >(tee -i /tmp/deckyscaler-unpatch.log) 2>&1

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

[[ "$#" -lt 1 ]] && error_exit "Usage: $0 program [program_arguments...]"
[[ -z "$python_bin" ]] && error_exit "Python 3 is required to unpatch games but was not found."

if ! exe_folder_path="$(PYTHONPATH="$plugin_home" "$python_bin" -m deckyscaler unpatch -- "$@")"; then
  error_exit "${exe_folder_path:-Unpatching failed. See /tmp/deckyscaler-unpatch.log.}"
fi
echo " OptiScaler removed from this game."
logger -t deckyscaler "OptiScaler removed from $exe_folder_path"

# The game no longer carries a proxy DLL, so it starts without any override of ours.
if [[ $# -gt 1 ]]; then
  export SteamDeck=0
  exec >/dev/null 2>&1
  exec "$@"
fi
