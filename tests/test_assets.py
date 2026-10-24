import unittest
import json
from pathlib import Path

from game.ui import GameUI
from game.combat import GameSession


class AssetTests(unittest.TestCase):
    def test_required_png_assets_exist(self):
        root = Path(__file__).parents[1] / "asset"
        manifest_path = root / "docs" / "READY_ASSETS.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assets = []

        def collect(value):
            if isinstance(value, str) and value.endswith(".png"):
                assets.append(value)
            elif isinstance(value, (list, tuple)):
                for item in value:
                    collect(item)
            elif isinstance(value, dict):
                for item in value.values():
                    collect(item)

        collect(manifest)
        assets = tuple(path.removeprefix("asset/") for path in assets
                       if isinstance(path, str) and path.endswith(".png"))
        self.assertEqual(len(assets), 53)
        missing = [str(root / name) for name in assets
                   if not (root / name).is_file()]
        self.assertEqual(missing, [])

    def test_digit_and_operator_tiles_exist(self):
        root = Path(__file__).parents[1] / "asset"
        tile_root = root / "ui" / "tiles"
        digits = [tile_root / f"tile_number_{value}.png" for value in range(10)]
        operators = [
            tile_root / "tile_operator_plus.png",
            tile_root / "tile_operator_minus.png",
            tile_root / "tile_operator_multiply.png",
            tile_root / "tile_operator_divide.png",
        ]
        self.assertTrue(all(path.is_file() for path in digits + operators))

    def test_runtime_assets_and_exact_hp_mappings(self):
        root = Path(__file__).parents[1] / "asset"
        for name in GameUI.REQUIRED_ASSETS:
            self.assertTrue((root / name).is_file(), str(root / name))
        hp_map = json.loads((root / "docs/HP_BAR_MAP.json").read_text())
        for spec in GameSession.BOSSES:
            for hp, path in hp_map[spec.sprite].items():
                self.assertEqual("asset/" + spec.hp_asset(int(hp)), path)
            with self.assertRaises(ValueError):
                spec.hp_asset(-20)


if __name__ == "__main__":
    unittest.main()
