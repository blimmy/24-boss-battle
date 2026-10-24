# Checks and decisions

> This file records what I checked, what actually happened, and why I accepted or changed the work.

## Concrete checks

| Check / requirement | Given | When | Expected result | Actual result / pass or fail |
|---|---|---|---|---|
| C1 / R1–R2 — normal case | Tiles 2, 3, 4, 6; Slime has 20 HP | Make 3-2=1, 4÷1=4, 6×4=24 | One automatic hit of 20; Slime goes to 0 HP | PASS (puzzle and UI tests) |
| C2 / R1 — invalid case | A used tile, or divisor 0 | Reuse the tile or divide by 0 | Move rejected; no damage, no tiles lost | PASS (puzzle tests) |
| C3 / R1 — duplicate numbers | Tiles 3, 3, 8, 8 | Solve using tile IDs | Each tile used once; the 24 is exact | PASS (puzzle tests) |
| C4 / R2 — boss order | New run | Complete six valid puzzles | Slime 20→0, Unicorn 40→20→0, Dragon 60→40→20→0, then Victory | PASS (combat and UI tests) |
| C5 / R1 — controls | Partly solved puzzle | Use Undo, Clear, Skip | Undo restores the previous reduction; Clear restores the original tiles; Skip deals another puzzle, adds 1 skip, and preserves HP | PASS (puzzle, combat, UI tests) |
| C6 / R3 — timer | Run in progress | Skip, change stages, win, Play Again | Time keeps running through skips and stages, freezes at final impact when the dragon reaches zero HP, and resets and starts immediately on Play Again | PASS (combat and UI tests) |
| C7 / R2–R3 — screens | All PNGs present | Draw Start, 3 battle stages, Victory | Screens and HP bars load; buttons clickable | PASS (asset and UI tests) |

## Two review decisions

- Plan decision: I used a bank of puzzles that already have answers, so the player never gets an impossible puzzle and testing is easier.
- Code decision: in  game/puzzle.py  I kept  Fraction  and unique tile IDs.  Fraction  avoids rounding errors in division, and IDs stop a tile being used twice even when two tiles have the same number.

## Automated tests

The tests are in `tests/test_puzzle.py`, `tests/test_combat.py`, `tests/test_ui.py`, and `tests/test_assets.py`.

Command used during development:

```bash
python -m unittest discover -s tests -v
```

- Result on 24 October 2026: all 40 tests passed (15 puzzle, 8 combat, 14 UI, 3 asset). The result was the same after the last change.
- One issue found during development was that some puzzles had no solution. After replacing those entries and rerunning the tests, all 21 puzzles passed the solvability check.

An additional check with Codex ran the tests without opening a game window:

```bash
PYTHONDONTWRITEBYTECODE=1 SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m unittest discover -s tests -v
```

- Recorded result: all 40 tests passed in 8.161 seconds, using Python 3.14.8 and pygame-ce 2.5.8. All 21 puzzles had a solution.
- These tests simulate clicks through all three bosses, Victory, and Play Again, and check that each screen renders. They do not check how the game looks or feels during real play; that is covered by the manual playthrough below.

## Realistic use and final judgment

Manual playthrough:

- Task I tried: I played one full run from Start Game to victory, using the number and operator buttons, Undo, Clear and Skip.
- Outcome: I finished in 3:11 with 4 skips. The puzzles mix hard and easy ones, so I skipped some of the hard ones. The controls, boss order, timer and Victory screen worked as described in R1–R3.
- Judgment: Done, because all three requirements worked in my play and the tests pass.
- Remaining limitation: I tested it myself on one computer and one screen size only, so I don't know how it looks or feels on other setups.
