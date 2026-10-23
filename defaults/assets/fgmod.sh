#!/usr/bin/env bash
# Launch wrapper: patches the game with OptiScaler, then starts it.
#   Steam launch options: ~/fgmod/fgmod %command%
#   Heroic: add ~/fgmod/fgmod as a wrapper
# Patching is done by the plugin's Python core (~/fgmod/framegen); this script
# only launches the game.

set -x
exec > >(tee -i /tmp/fgmod-install.log) 2>&1

error_exit() {
  echo " $1"
  if [[ -n $STEAM_ZENITY ]]; then
    $STEAM_ZENITY --error --text "$1"
  else
    zenity --error --text "$1" || echo "Zenity failed to display error"
  fi
  logger -t fgmod "ERROR: $1"
  exit 1
}

fgmod_path="$HOME/fgmod"
dll_name="${DLL:-dxgi.dll}"
python_bin="$(command -v python3 || command -v python || true)"

[[ "$#" -lt 1 ]] && error_exit "Usage: $0 program [program_arguments...]"
[[ -z "$python_bin" ]] && error_exit "Python 3 is required to patch games but was not found."

core_args=(patch --dll "$dll_name" --variant "${FGMOD_FSR4_VARIANT:-}")
[[ "${PRESERVE_INI:-true}" == "true" ]] || core_args+=(--reset-ini)
if ! exe_folder_path="$(PYTHONPATH="$fgmod_path" "$python_bin" -m framegen "${core_args[@]}" -- "$@")"; then
  error_exit "${exe_folder_path:-Patching failed. See /tmp/fgmod-install.log.}"
fi
logger -t fgmod "Patched $exe_folder_path with $dll_name"

# OptiScaler settings from environment variables override OptiScaler.ini on every launch.
if [[ -f "$fgmod_path/update-optiscaler-config.py" ]]; then
  "$python_bin" "$fgmod_path/update-optiscaler-config.py" "$exe_folder_path/OptiScaler.ini"
fi

if [[ $# -gt 1 ]]; then
  export SteamDeck=0
  # Load the proxy DLL natively; an .asi is loaded by the game's ASI loader instead.
  if [[ "$dll_name" == *.dll ]]; then
    export WINEDLLOVERRIDES="$WINEDLLOVERRIDES,${dll_name%.dll}=n,b"
  fi
  # Drop leading -- separators from Steam launch options.
  while [[ $# -gt 0 && "$1" == "--" ]]; do
    shift
  done
  exec >/dev/null 2>&1
  "$@"
fi
