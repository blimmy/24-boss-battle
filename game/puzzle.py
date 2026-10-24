"""Exact, click-driven pair reduction rules for the 24 game."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import random
from typing import Sequence

PUZZLE_BANK: tuple[tuple[int, int, int, int], ...] = (
    (2, 3, 4, 6), (1, 5, 5, 5), (3, 3, 8, 8), (1, 4, 5, 6),
    (2, 2, 6, 6), (1, 2, 2, 6), (1, 2, 7, 7), (2, 3, 5, 9),
    (1, 3, 4, 6), (2, 4, 5, 8), (3, 5, 7, 9), (1, 2, 3, 8),
    (2, 5, 6, 9), (1, 4, 6, 8), (3, 3, 7, 9), (2, 4, 7, 8),
    (1, 5, 6, 8), (2, 3, 7, 8), (3, 4, 5, 6), (1, 2, 2, 7),
    (2, 5, 7, 8),
)
OPERATORS = ("+", "-", "×", "÷")


def _combine(values: Sequence[Fraction]) -> set[Fraction]:
    if len(values) == 1:
        return {values[0]}
    results: set[Fraction] = set()
    for index, left in enumerate(values):
        rest = values[:index] + values[index + 1:]
        for other_index, right in enumerate(rest):
            remaining = rest[:other_index] + rest[other_index + 1:]
            candidates = (left + right, left - right, right - left, left * right)
            if right:
                candidates += (left / right,)
            if left:
                candidates += (right / left,)
            for result in candidates:
                results.update(_combine(remaining + (result,)))
    return results


def has_24_solution(numbers: Sequence[int]) -> bool:
    """Return whether pairwise arithmetic can make 24."""
    return Fraction(24) in _combine(tuple(Fraction(number) for number in numbers))


def format_value(value: Fraction) -> str:
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


@dataclass(frozen=True)
class Tile:
    id: int
    value: Fraction
    active: bool
    origin_ids: frozenset[int]
    result: bool = False


@dataclass(frozen=True)
class _Snapshot:
    tiles: tuple[Tile, ...]
    next_id: int


class PairReduction:
    """Manage tile identity, provenance, selection, and undoable reductions."""

    def __init__(self, numbers: Sequence[int]):
        if len(numbers) != 4:
            raise ValueError("a puzzle must contain four numbers")
        self._originals = tuple(Fraction(number) for number in numbers)
        self._next_id = 4
        self._history: list[_Snapshot] = []
        self._selected_id: int | None = None
        self._operator: str | None = None
        self.feedback = "Select a tile."
        self.tiles: tuple[Tile, ...] = tuple(
            Tile(index, value, True, frozenset((index,)))
            for index, value in enumerate(self._originals)
        )

    @property
    def active_tiles(self) -> tuple[Tile, ...]:
        return tuple(tile for tile in self.tiles if tile.active)

    @property
    def selected_id(self) -> int | None:
        return self._selected_id

    @property
    def operator(self) -> str | None:
        return self._operator

    @property
    def complete(self) -> bool:
        return (
            len(self._history) == 3
            and len(self.active_tiles) == 1
            and self.active_tiles[0].value == 24
            and self.active_tiles[0].origin_ids == frozenset(range(4))
        )

    @property
    def final_result(self) -> Fraction | None:
        if len(self.active_tiles) != 1:
            return None
        return self.active_tiles[0].value

    @property
    def final_result_is_wrong(self) -> bool:
        return self.final_result is not None and not self.complete

    def select_tile(self, tile_id: int) -> bool:
        tile = next((item for item in self.tiles if item.id == tile_id), None)
        if tile is None or not tile.active:
            self.feedback = "That tile has already been used."
            return False
        if self._selected_id is None:
            self._selected_id = tile_id
            self.feedback = "Choose an operator."
            return True
        if self._operator is None:
            if tile_id == self._selected_id:
                self.feedback = "Choose a different active tile."
                return False
            self._selected_id = tile_id
            self.feedback = "Choose an operator."
            return True
        if tile_id == self._selected_id:
            self.feedback = "Choose a different active tile."
            return False
        return self._combine_selected(tile_id)

    def select_operator(self, operator: str) -> bool:
        if operator not in OPERATORS or self._selected_id is None:
            self.feedback = "Choose a tile first."
            return False
        self._operator = operator
        self.feedback = "Choose the second tile."
        return True

    def _combine_selected(self, second_id: int) -> bool:
        first = next(tile for tile in self.tiles if tile.id == self._selected_id)
        second = next(tile for tile in self.tiles if tile.id == second_id)
        if self._operator == "÷" and second.value == 0:
            self.feedback = "Division by zero is not allowed."
            return False
        self._history.append(_Snapshot(self.tiles, self._next_id))
        if self._operator == "+":
            value = first.value + second.value
        elif self._operator == "-":
            value = first.value - second.value
        elif self._operator == "×":
            value = first.value * second.value
        else:
            value = first.value / second.value
        consumed = {first.id, second.id}
        result = Tile(
            self._next_id, value, True,
            first.origin_ids | second.origin_ids, True,
        )
        self._next_id += 1
        self.tiles = tuple(
            tile if tile.id not in consumed else Tile(
                tile.id, tile.value, False, tile.origin_ids, tile.result
            )
            for tile in self.tiles
        ) + (result,)
        self._selected_id = None
        self._operator = None
        if self.complete:
            self.feedback = "Great! Auto attack!"
        elif len(self.active_tiles) == 1:
            self.feedback = "Not 24 - Undo, Clear, or Skip."
        else:
            self.feedback = f"Created {format_value(value)}."
        return True

    def undo(self) -> bool:
        if not self._history:
            self._selected_id = None
            self._operator = None
            self.feedback = "Nothing to undo."
            return False
        snapshot = self._history.pop()
        self.tiles, self._next_id = snapshot.tiles, snapshot.next_id
        self._selected_id = None
        self._operator = None
        self.feedback = "Last combination undone."
        return True

    def clear(self) -> None:
        self.tiles = tuple(
            Tile(index, value, True, frozenset((index,)))
            for index, value in enumerate(self._originals)
        )
        self._next_id = 4
        self._history.clear()
        self._selected_id = None
        self._operator = None
        self.feedback = "Puzzle restored."


class PuzzleDealer:
    def __init__(self, rng: random.Random | None = None):
        self.rng = rng or random.Random()
        self.current_index = -1
        self.skips = 0

    def next_puzzle(self) -> tuple[int, int, int, int]:
        choices = [i for i in range(len(PUZZLE_BANK)) if i != self.current_index]
        if not choices:
            choices = list(range(len(PUZZLE_BANK)))
        if not choices:
            raise ValueError("The puzzle bank is empty")
        self.current_index = self.rng.choice(choices)
        return PUZZLE_BANK[self.current_index]

    def skip(self) -> tuple[int, int, int, int]:
        self.skips += 1
        return self.next_puzzle()
