import unittest

from game.combat import GameSession


class FakeClock:
    def __init__(self):
        self.value = 100.0

    def __call__(self):
        return self.value


def solve_current(game: GameSession) -> None:
    game.puzzle = (2, 3, 4, 6)
    game.builder = __import__("game.puzzle", fromlist=["PairReduction"]).PairReduction(game.puzzle)
    for first, operator, second in ((1, "-", 0), (2, "÷", 4), (3, "×", 5)):
        game.builder.select_tile(first)
        game.builder.select_operator(operator)
        game.builder.select_tile(second)


class CombatTests(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.game = GameSession(self.clock)
        self.game.start()

    def test_invalid_and_valid_damage(self):
        self.assertFalse(self.game.attack())
        self.assertEqual(self.game.boss.hp, 20)
        solve_current(self.game)
        first_boss = self.game.boss
        self.assertTrue(self.game.attack())
        self.assertEqual(first_boss.hp, 0)
        self.assertEqual(self.game.stage, 1)

    def test_skip_changes_puzzle_and_preserves_hp(self):
        old = self.game.puzzle
        self.game.skip()
        self.assertNotEqual(old, self.game.puzzle)
        self.assertEqual(self.game.skips, 1)
        self.assertEqual(self.game.boss.hp, 20)
        self.assertEqual(len(self.game.builder.active_tiles), 4)

    def test_stage_progression_and_victory(self):
        for expected_stage, attacks in ((1, 1), (2, 2), (2, 3)):
            for _ in range(attacks):
                solve_current(self.game)
                self.assertTrue(self.game.attack())
            self.assertEqual(self.game.stage, expected_stage)
        self.assertTrue(self.game.victory)
        self.assertEqual(self.game.bosses_defeated, 3)
        self.assertEqual(self.game.boss.hp, 0)

    def test_timer_continues_and_freezes_on_victory(self):
        self.clock.value = 112.5
        self.assertAlmostEqual(self.game.elapsed, 12.5)
        for _ in range(6):
            solve_current(self.game)
            self.game.attack()
        frozen = self.game.elapsed
        self.clock.value = 999
        self.assertEqual(self.game.elapsed, frozen)

    def test_restart_restores_initial_state(self):
        self.game.skip()
        self.game.restart()
        self.assertEqual(self.game.stage, 0)
        self.assertEqual(self.game.successful_attacks, 0)
        self.assertEqual(self.game.skips, 0)
        self.assertIsNone(self.game.started_at)
        self.assertFalse(self.game.victory)
        self.assertEqual(self.game.boss.hp, 20)

    def test_exact_order_hp_and_six_attacks(self):
        self.assertEqual([(b.name, b.max_hp) for b in self.game.bosses],
                         [("Cloud Slime", 20), ("Cursed Unicorn", 40), ("Rainbow Dragon", 60)])
        for stage, before, after in ((0,20,0), (1,40,20), (1,20,0),
                                     (2,60,40), (2,40,20), (2,20,0)):
            boss = self.game.boss
            self.assertEqual((self.game.stage, boss.hp), (stage, before))
            solve_current(self.game)
            self.assertTrue(self.game.attack())
            self.assertEqual(boss.hp, after)
            self.assertFalse(self.game.attack())
        self.assertEqual(self.game.successful_attacks, 6)
        self.assertTrue(self.game.victory)
        self.game.skip()
        self.assertEqual(self.game.skips, 0)

    def test_actions_before_start_do_not_change_battle(self):
        self.game.restart()
        solve_current(self.game)
        self.assertFalse(self.game.attack())
        self.game.skip()
        self.assertEqual((self.game.skips, self.game.boss.hp), (0,20))

    def test_time_at_minute_boundary_and_repeated_start(self):
        self.clock.value = 159.999
        self.assertEqual(self.game.formatted_time(), "00:59.99")
        self.game.start()
        self.clock.value = 160
        self.assertEqual(self.game.formatted_time(), "01:00.00")
        self.game.skip()
        solve_current(self.game)
        self.game.attack()
        self.clock.value = 161.25
        self.assertEqual(self.game.formatted_time(), "01:01.25")


if __name__ == "__main__":
    unittest.main()
