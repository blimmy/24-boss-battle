"""Battle state and monotonic timing, independent of the Pygame UI."""

from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Callable

from .puzzle import PairReduction, PuzzleDealer


@dataclass
class Boss:
    name: str
    max_hp: int
    hp: int
    setting: str


@dataclass(frozen=True)
class BossConfig:
    name: str
    max_hp: int
    setting: str
    sprite: str
    bar_prefix: str
    background: str

    def hp_asset(self, hp: int) -> str:
        if hp not in range(0, self.max_hp + 1, GameSession.DAMAGE_PER_SUCCESS):
            raise ValueError(f"Invalid HP for {self.name}: {hp}")
        return f"ui/bars/{self.bar_prefix}_hp_{hp}.png"


class GameSession:
    BOSSES = (
        BossConfig("Cloud Slime", 20, "Cotton Candy Meadow", "cloud_slime", "slime",
                   "backgrounds/stage1_cloud_slime_bg.png"),
        BossConfig("Cursed Unicorn", 40, "Lavender Dream Forest", "cursed_unicorn", "unicorn",
                   "backgrounds/stage2_cursed_unicorn_bg.png"),
        BossConfig("Rainbow Dragon", 60, "Rainbow Castle", "rainbow_dragon", "dragon",
                   "backgrounds/stage3_rainbow_dragon_bg.png"),
    )
    DAMAGE_PER_SUCCESS = 20

    def __init__(self, clock: Callable[[], float] | None = None):
        self._clock = clock or time.monotonic
        self.dealer = PuzzleDealer()
        self.reset()

    def reset(self) -> None:
        self.stage = 0
        self.bosses_defeated = 0
        self.successful_attacks = 0
        self.skips = 0
        self.started_at: float | None = None
        self.finished_at: float | None = None
        self.victory = False
        self.feedback = "Combine the tiles to make 24."
        self.bosses = [Boss(spec.name, spec.max_hp, spec.max_hp, spec.setting)
                       for spec in self.BOSSES]
        self.dealer = PuzzleDealer()
        self.puzzle = self.dealer.next_puzzle()
        self.builder = PairReduction(self.puzzle)

    @property
    def boss(self) -> Boss:
        return self.bosses[self.stage]

    @property
    def elapsed(self) -> float:
        if self.started_at is None:
            return 0.0
        end = self.finished_at if self.finished_at is not None else self._clock()
        return max(0.0, end - self.started_at)

    def start(self) -> None:
        if self.started_at is None:
            self.started_at = self._clock()

    def skip(self) -> None:
        if self.victory or self.started_at is None:
            return
        self.puzzle = self.dealer.skip()
        self.skips = self.dealer.skips
        self.builder = PairReduction(self.puzzle)
        self.feedback = "A new puzzle appeared."

    def attack(self) -> bool:
        if self.victory or self.started_at is None:
            return False
        if not self.builder.complete:
            self.feedback = "Reduce every tile to exactly 24 first."
            return False
        self.boss.hp = max(0, self.boss.hp - self.DAMAGE_PER_SUCCESS)
        self.successful_attacks += 1
        self.feedback = "Rainbow magic hit!"
        if self.boss.hp == 0:
            self.bosses_defeated += 1
            if self.stage == len(self.bosses) - 1:
                self.victory = True
                self.finished_at = self._clock()
                self.feedback = "Rainbow Kingdom saved!"
            else:
                self.stage += 1
                self.feedback = f"{self.bosses[self.stage - 1].name} defeated!"
        if not self.victory:
            self.puzzle = self.dealer.next_puzzle()
            self.builder = PairReduction(self.puzzle)
        return True

    def restart(self) -> None:
        self.reset()

    def formatted_time(self) -> str:
        centiseconds = int(self.elapsed * 100)
        minutes, rest = divmod(centiseconds, 6000)
        seconds, fraction = divmod(rest, 100)
        return f"{minutes:02d}:{seconds:02d}.{fraction:02d}"
