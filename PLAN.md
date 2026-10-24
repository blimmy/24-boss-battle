# Implementation plan

> This file records my project-specific steps reviewed before coding. Requirements are in README.md (R1–R3).

## Steps
1. Setup (R1–R3): write the requirements, two expected checks and AGENTS.md; set up Python, Pygame and Git.
2. Math 24 (R1): in  game/puzzle.py , build tiles with unique IDs, pairwise operations with  Fraction , Undo, Clear, Skip, and a bank of solvable puzzles.
3. Boss battles (R2): in  game/combat.py , add the three bosses, their HP, stage changes, and one automatic 20-damage hit after a valid final 24.
4. Interface and timer (R2–R3): in  game/ui.py  and  main.py , add the Start, Battle and Victory screens, mouse controls, animations, the timer and Play Again, loading PNGs from  asset/ .
5. Test and review (R1–R3): turn the expected checks into automated tests, test bad input and state changes, then play a full round and record the result and one limitation in EVIDENCE.md.

## Later changes
- Changed from 10 damage with 20/30/40 HP to 20 damage with 20/40/60 HP. Reason: I want the game to finish quickly and be easy to play.
- Changed input to clicking number pairs; the princess now attacks automatically when the last tile is 24. Reason: this is a timed game, so clicking an Attack button wastes time. When the player gets 24, the attack should happen right away.
- Added PNG sprites, HP bars and effects in  asset/ .