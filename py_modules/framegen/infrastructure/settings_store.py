"""~/fgmod/settings: the user's global OptiScaler settings and each game's own, as JSON layers."""

from __future__ import annotations

from pathlib import Path

from framegen.domain import settings_layers
from framegen.domain.settings_layers import Layer
from framegen.infrastructure.files import read_json, write_json


class SettingsStore:
    def __init__(self, root: Path):
        self.root = root
        self.global_path = root / "global.json"
        self.games_dir = root / "games"

    def global_layer(self) -> Layer:
        """The global settings; before the user ever saves any, what they start as."""
        if not self.global_path.exists():
            return dict(settings_layers.INITIAL_GLOBAL)
        return settings_layers.parse_layer(read_json(self.global_path))

    def save_global(self, layer: Layer) -> None:
        self._write(self.global_path, layer)

    def game_layer(self, appid: str) -> Layer:
        return settings_layers.parse_layer(read_json(self._game_path(appid)))

    def save_game(self, appid: str, layer: Layer) -> None:
        self._write(self._game_path(appid), layer)

    def _game_path(self, appid: str) -> Path:
        if not appid.isdigit():
            raise ValueError(f"Not a Steam app id: {appid!r}")
        return self.games_dir / f"{appid}.json"

    @staticmethod
    def _write(path: Path, layer: Layer) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        staged = path.with_name(path.name + ".new")
        write_json(staged, settings_layers.layer_json(layer))
        staged.replace(path)
