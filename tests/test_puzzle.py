import unittest
from unittest.mock import patch
from fractions import Fraction

from game.puzzle import (
    OPERATORS, PUZZLE_BANK, PairReduction, PuzzleDealer, format_value, has_24_solution,
)


class PuzzleTests(unittest.TestCase):
    def reduce(self, puzzle: PairReduction, first: int, operator: str, second: int) -> None:
        self.assertTrue(puzzle.select_tile(first))
        self.assertTrue(puzzle.select_operator(operator))
        self.assertTrue(puzzle.select_tile(second))

    def test_pair_reduction_consumes_tiles_and_creates_result(self):
        puzzle = PairReduction((5, 3, 8, 8))
        self.reduce(puzzle, 0, "-", 1)
        result = next(tile for tile in puzzle.tiles if tile.result)
        self.assertEqual(result.value, Fraction(2))
        self.assertEqual(result.origin_ids, frozenset((0, 1)))
        self.assertFalse(puzzle.tiles[0].active)
        self.assertFalse(puzzle.tiles[1].active)

    def test_duplicate_values_have_distinct_ids_and_self_selection_is_rejected(self):
        puzzle = PairReduction((5, 3, 8, 8))
        self.assertNotEqual(puzzle.tiles[2].id, puzzle.tiles[3].id)
        self.assertTrue(puzzle.select_tile(2))
        self.assertFalse(puzzle.select_tile(2))
        self.assertEqual(len(puzzle.active_tiles), 4)

    def test_order_fraction_and_negative_results(self):
        puzzle = PairReduction((5, 3, 8, 8))
        self.reduce(puzzle, 1, "-", 0)
        self.assertEqual(puzzle.active_tiles[-1].value, Fraction(-2))
        puzzle.clear()
        self.reduce(puzzle, 0, "÷", 1)
        self.assertEqual(puzzle.active_tiles[-1].value, Fraction(5, 3))
        self.assertEqual(format_value(Fraction(5, 3)), "5/3")

    def test_division_by_zero_does_not_consume_tiles(self):
        puzzle = PairReduction((5, 0, 8, 8))
        self.assertTrue(puzzle.select_tile(0))
        self.assertTrue(puzzle.select_operator("÷"))
        self.assertFalse(puzzle.select_tile(1))
        self.assertEqual(len(puzzle.active_tiles), 4)

    def test_undo_and_clear_restore_original_tiles(self):
        puzzle = PairReduction((5, 3, 8, 8))
        self.reduce(puzzle, 0, "-", 1)
        self.assertTrue(puzzle.undo())
        self.assertEqual(len(puzzle.active_tiles), 4)
        self.reduce(puzzle, 0, "-", 1)
        puzzle.clear()
        self.assertEqual(tuple(tile.value for tile in puzzle.active_tiles),
                         (Fraction(5), Fraction(3), Fraction(8), Fraction(8)))

    def test_all_bank_puzzles_are_pairwise_solvable(self):
        self.assertTrue(all(has_24_solution(puzzle) for puzzle in PUZZLE_BANK))
        self.assertEqual(OPERATORS, ("+", "-", "×", "÷"))

    def test_attack_completion_requires_all_provenance(self):
        puzzle = PairReduction((2, 3, 4, 6))
        self.reduce(puzzle, 1, "-", 0)
        self.reduce(puzzle, 2, "÷", 4)
        self.reduce(puzzle, 3, "×", 5)
        self.assertTrue(puzzle.complete)

    def test_intermediate_24_is_not_complete(self):
        puzzle = PairReduction((2, 3, 4, 6))
        self.reduce(puzzle, 0, "×", 1)
        self.reduce(puzzle, 2, "×", 3)
        self.assertEqual(puzzle.active_tiles[0].value, Fraction(6))
        self.assertFalse(puzzle.complete)

    def test_wrong_final_result_does_not_complete(self):
        puzzle = PairReduction((2, 3, 4, 6))
        self.reduce(puzzle, 0, "+", 1)
        self.reduce(puzzle, 2, "+", 3)
        self.reduce(puzzle, 4, "+", 5)
        self.assertEqual(puzzle.final_result, Fraction(15))
        self.assertTrue(puzzle.final_result_is_wrong)

    def test_fraction_solution_with_duplicate_numbers(self):
        puzzle = PairReduction((3,3,8,8))
        self.reduce(puzzle, 2, "÷", 0)
        self.reduce(puzzle, 1, "-", 4)
        self.assertEqual(puzzle.active_tiles[-1].value, Fraction(1,3))
        self.reduce(puzzle, 3, "÷", 5)
        self.assertTrue(puzzle.complete)

    def test_inactive_missing_and_duplicate_ids_are_rejected(self):
        puzzle = PairReduction((2,3,4,6))
        self.reduce(puzzle, 0, "+", 1)
        before = puzzle.tiles
        for tile_id in (0,1,99,-1):
            self.assertFalse(puzzle.select_tile(tile_id))
            self.assertEqual(before, puzzle.tiles)
        puzzle.select_tile(2)
        puzzle.select_operator("×")
        self.assertFalse(puzzle.select_tile(2))
        self.assertEqual(before, puzzle.tiles)

    def test_invalid_operator_and_incomplete_solution(self):
        puzzle = PairReduction((2,3,4,6))
        self.assertFalse(puzzle.select_operator("+"))
        puzzle.select_tile(0)
        for operator in ("**", "eval", "", "("):
            self.assertFalse(puzzle.select_operator(operator))
        self.assertIsNone(puzzle.operator)
        self.assertFalse(puzzle.complete)

    def test_undo_restores_provenance_and_clears_pending_selection(self):
        puzzle = PairReduction((2,3,4,6))
        puzzle.select_tile(0)
        puzzle.select_operator("+")
        self.assertFalse(puzzle.undo())
        self.assertIsNone(puzzle.selected_id)
        self.reduce(puzzle, 1, "-", 0)
        before = puzzle.tiles
        self.reduce(puzzle, 2, "÷", 4)
        puzzle.select_tile(3)
        puzzle.select_operator("×")
        puzzle.undo()
        self.assertEqual(puzzle.tiles, before)
        self.assertIsNone(puzzle.selected_id)
        self.assertIsNone(puzzle.operator)
        self.reduce(puzzle, 2, "÷", 4)
        self.reduce(puzzle, 3, "×", 5)
        self.assertTrue(puzzle.complete)
        puzzle.clear()
        self.assertFalse(puzzle.undo())
        self.assertFalse(puzzle.complete)

    def test_single_puzzle_bank_can_still_skip(self):
        with patch("game.puzzle.PUZZLE_BANK", ((2,3,4,6),)):
            dealer = PuzzleDealer()
            self.assertEqual(dealer.next_puzzle(), dealer.skip())
            self.assertEqual(dealer.skips, 1)

    def test_zero_and_unsolvable_inputs(self):
        self.assertFalse(has_24_solution((1,1,1,1)))
        puzzle = PairReduction((0,2,3,4))
        self.reduce(puzzle, 0, "+", 1)
        self.reduce(puzzle, 2, "×", 3)
        self.reduce(puzzle, 4, "×", 5)
        self.assertTrue(puzzle.complete)


if __name__ == "__main__":
    unittest.main()
