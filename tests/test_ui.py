"""Real Pygame rendering and mouse-controller regression tests, without a display."""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import unittest
from fractions import Fraction
from pathlib import Path
from unittest.mock import patch

import pygame

from game.combat import GameSession
from game.puzzle import PairReduction
from game.ui import GameUI, ROOT, WINDOW_SIZE
from tests.test_combat import FakeClock


class UITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.screen = pygame.display.set_mode(WINDOW_SIZE)

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        self.ui = GameUI(self.screen)
        self.clock = FakeClock()
        self.ui.session = GameSession(self.clock)
        self.ui.click(self.ui.START_RECT.center)

    def combine(self, first, op, second):
        ui = self.ui
        ui.click(ui._tile_rects(ui.session.builder)[first].center)
        ui.click(ui.OPERATOR_RECTS[op].center)
        ui.click(ui._tile_rects(ui.session.builder)[second].center)

    def solve(self):
        self.ui.session.builder = PairReduction((2, 3, 4, 6))
        for first, op, second in ((1, "-", 0), (2, "÷", 4), (3, "×", 5)):
            self.combine(first, op, second)

    def test_auto_attack_only_after_final_24_and_once(self):
        ui = self.ui
        ui.session.builder = PairReduction((2, 3, 4, 6))
        self.combine(2, "×", 3)
        self.assertIsNone(ui.attack_phase)  # Intermediate 24 is not enough.
        self.assertEqual(ui.session.boss.hp, 20)
        self.solve()
        self.assertEqual(ui.attack_phase, "casting")
        self.assertEqual(ui.session.successful_attacks, 0)
        for _ in range(10):
            ui.click(ui._tile_rects(ui.session.builder)[6].center)
            ui._start_auto_attack()
        ui.update(ui.IMPACT_AT)
        self.assertEqual(ui.session.successful_attacks, 1)
        self.assertEqual(ui.session.bosses[0].hp, 0)
        for _ in range(10):
            ui.update(0.01)
        self.assertEqual(ui.session.successful_attacks, 1)

    def test_skip_clear_and_undo_are_locked_during_every_attack_phase(self):
        ui = self.ui
        self.solve()
        builder, puzzle = ui.session.builder, ui.session.puzzle
        for dt in (0, ui.CAST_DURATION, ui.FLIGHT_DURATION, ui.HIT_DURATION):
            ui.update(dt)
            self.assertTrue(ui.input_locked)
            before = (ui.session.builder, ui.session.puzzle, ui.session.successful_attacks)
            for action, rect in ui.ACTION_RECTS.items():
                ui.click(rect.center)
                ui._action(action)
            self.assertEqual(before, (ui.session.builder, ui.session.puzzle,
                                      ui.session.successful_attacks))
            self.assertEqual(ui.session.skips, 0)
        self.assertTrue(builder.complete)
        ui.update(ui.TRANSITION_DURATION + 0.01)
        ui.click(ui.ACTION_RECTS["SKIP"].center)
        self.assertEqual(ui.session.skips, 1)
        self.assertFalse(ui.input_locked)

    def test_defeated_boss_stays_visible_until_hit_animation_finishes(self):
        self.solve()
        ui = self.ui
        ui.update(ui.IMPACT_AT)
        self.assertEqual(ui.attack_phase, "hit")
        self.assertEqual(ui.display_stage, 0)
        self.assertEqual(ui.session.stage, 1)
        self.assertEqual(ui.session.bosses[ui.display_stage].hp, 0)
        ui.draw()
        ui.update(ui.HIT_DURATION + 0.01)
        self.assertEqual(ui.display_stage, 1)
        self.assertIsNone(ui.attack_phase)

    def test_attack_duration_is_independent_of_frame_rate(self):
        for steps in ([2.0], [0.01]*200, [0.4, 0.48, 0.6, 0.52]):
            with self.subTest(steps=len(steps)):
                self.ui.session.restart()
                self.ui.session.start()
                self.solve()
                for dt in steps:
                    self.ui.update(dt)
                self.assertEqual(self.ui.session.successful_attacks, 1)
                self.assertEqual(self.ui.display_stage, 1)
                self.assertFalse(self.ui.input_locked)

    def test_effects_draw_only_during_attack(self):
        ui = self.ui
        ui.canvas.fill("#123456")
        before = pygame.image.tobytes(ui.canvas, "RGB")
        ui.draw_effects()
        self.assertEqual(before, pygame.image.tobytes(ui.canvas, "RGB"))
        self.solve()
        for dt in (0.1, 0.4, 0.5):
            ui.update(dt)
            ui.canvas.fill("#123456")
            ui.draw_effects()
            self.assertNotEqual(before, pygame.image.tobytes(ui.canvas, "RGB"))
        ui.update(2)
        ui.canvas.fill("#123456")
        ui.draw_effects()
        self.assertEqual(before, pygame.image.tobytes(ui.canvas, "RGB"))

    def test_complete_mouse_playthrough_and_restart_timer(self):
        ui = self.ui
        expected = ((0,20), (1,40), (1,20), (2,60), (2,40), (2,20))
        for stage, hp in expected:
            self.assertEqual((ui.session.stage, ui.session.boss.hp), (stage, hp))
            self.solve()
            self.clock.value += 10
            ui.update(ui.IMPACT_AT)
            ui.draw()
            ui.update(1)
        self.assertEqual(ui.screen_name, "victory")
        self.assertEqual(ui.session.successful_attacks, 6)
        self.assertEqual(ui.session.bosses_defeated, 3)
        frozen = ui.session.elapsed
        self.clock.value += 100
        ui.update(10)
        ui.draw()
        self.assertEqual(ui.session.elapsed, frozen)
        ui.click(ui.ACTION_RECTS["SKIP"].center)
        self.assertEqual(ui.session.skips, 0)
        ui.click(ui.RESTART_RECT.center)
        self.assertEqual(ui.screen_name, "battle")
        self.assertEqual(ui.session.successful_attacks, 0)
        self.assertFalse(ui.input_locked)
        self.clock.value += 1.25
        self.assertEqual(ui.session.formatted_time(), "00:01.25")

    def test_skip_clears_partial_selection_without_damage(self):
        ui = self.ui
        ui.click(ui._tile_rects(ui.session.builder)[0].center)
        ui.click(ui.OPERATOR_RECTS["÷"].center)
        old = ui.session.puzzle
        self.clock.value += 5
        ui.click(ui.ACTION_RECTS["SKIP"].center)
        self.assertNotEqual(old, ui.session.puzzle)
        self.assertIsNone(ui.session.builder.selected_id)
        self.assertIsNone(ui.session.builder.operator)
        self.assertEqual((ui.session.boss.hp, ui.session.successful_attacks, ui.session.skips),
                         (20, 0, 1))
        self.assertEqual(ui.session.elapsed, 5)

    def test_invalid_final_can_be_undone_cleared_and_repaired(self):
        ui = self.ui
        ui.session.builder = PairReduction((2,3,4,6))
        self.combine(0, "+", 1)
        self.combine(2, "+", 3)
        self.combine(4, "+", 5)
        self.assertIsNone(ui.attack_phase)
        ui.click(ui.ACTION_RECTS["UNDO"].center)
        self.assertEqual(len(ui.session.builder.active_tiles), 2)
        ui.click(ui.ACTION_RECTS["CLEAR"].center)
        self.assertEqual(len(ui.session.builder.active_tiles), 4)
        self.assertEqual(ui.session.successful_attacks, 0)
        self.solve()
        self.assertEqual(ui.attack_phase, "casting")

    def test_layout_hitboxes_do_not_overlap_and_match_window_coordinates(self):
        ui = self.ui
        self.solve()
        rects = list(ui._tile_rects(ui.session.builder).values())
        rects += list(ui.ACTION_RECTS.values()) + list(ui.OPERATOR_RECTS.values())
        for i, rect in enumerate(rects):
            self.assertTrue(pygame.Rect(10,168,460,99).contains(rect))
            self.assertEqual(ui.logical_point((rect.centerx*2,rect.centery*2)), rect.center)
            for other in rects[i+1:]:
                self.assertFalse(rect.colliderect(other))

    def test_tiles_use_blank_images_and_values_fit(self):
        ui = self.ui
        rect = pygame.Rect(20,20,44,29)
        for value in (Fraction(0), Fraction(-123456), Fraction(123456,78901), Fraction(24)):
            with patch.object(ui, "image", wraps=ui.image) as image:
                ui.tile(rect, str(value))
                self.assertEqual(image.call_args.args[0], "ui/tiles/tile_number.png")
        ui.canvas.fill("#123456")
        ui.tile(rect, "-123456789/98765")
        for point in ((19,30),(64,30),(30,19),(30,49)):
            self.assertEqual(ui.canvas.get_at(point)[:3], (18,52,86))

    def test_faded_assets_preserve_transparent_corners(self):
        ui = self.ui
        ui.canvas.fill("#123456")
        ui.tile(pygame.Rect(20,20,44,29), "3", active=False)
        ui.button(pygame.Rect(80,20,60,24), "SKIP", "skip", enabled=False)
        self.solve()
        ui.update(ui.IMPACT_AT + 0.1)
        ui.draw_effects()
        for point in ((20,20), (80,20), (365,103)):
            self.assertEqual(ui.canvas.get_at(point)[:3], (18,52,86))

    def test_missing_sprite_and_hp_asset_fail_with_exact_path(self):
        original = Path.is_file
        for relative in ("sprites/rainbow_dragon/hit_3.png", "ui/bars/unicorn_hp_20.png"):
            missing = ROOT / relative
            with patch.object(Path, "is_file", lambda path: False if path == missing else original(path)):
                with self.assertRaises(FileNotFoundError) as raised:
                    GameUI(self.screen)
                self.assertIn(str(missing), str(raised.exception))

    def test_corrupt_asset_error_includes_exact_path(self):
        load = pygame.image.load
        corrupt = ROOT / "sprites/princess/idle_1.png"
        def fail_one(path):
            if Path(path) == corrupt:
                raise pygame.error("unsupported image")
            return load(path)
        with patch.object(pygame.image, "load", side_effect=fail_one):
            with self.assertRaises(RuntimeError) as raised:
                GameUI(self.screen)
            self.assertIn(str(corrupt), str(raised.exception))

    def test_all_five_screens_render(self):
        ui = self.ui
        ui.screen_name = "start"
        ui.draw()
        ui.screen_name = "battle"
        for stage in range(3):
            ui.session.stage = stage
            ui.draw()
        ui.screen_name = "victory"
        ui.draw()
