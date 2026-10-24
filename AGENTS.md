# Instructions for this repository

> This file tells the coding agent how to work on this project. It does not replace the requirements or plan.

- Read README.md, PLAN.md and the checks in EVIDENCE.md before implementing.
- Keep changes within R1–R3 in README.md.
- Use Python 3.11+ and Pygame. Keep math in  game/puzzle.py , battles and timing in  game/combat.py , and drawing/mouse controls in  game/ui.py .
- Use  fractions.Fraction  for exact math. Never use  eval()  or  exec() . Give each tile a unique ID and use all four starting tiles exactly once.
- Reject reused or inactive tiles, the same tile picked twice, and division by zero. Only a final 24 attacks, never an unfinished puzzle or an intermediate 24.
- Skip picks another solvable puzzle when possible, resets the move, adds one skip, and does not change HP.
- Boss order is Cloud Slime (20 HP), Cursed Unicorn (40 HP), Rainbow Dragon (60 HP). A final 24 gives exactly one automatic 20-damage hit.
- The timer is monotonic, runs from Start Game to the final hit, and is not reset by Skip or stage changes. Play Again starts a fresh run.
- Load PNGs from the root  asset/  folders. Number tiles are blank images with numbers drawn in Pygame. A missing asset must report its exact path.
- Keep animations non-blocking.
- Make small, clear commits. Do not rewrite Git history.
- Run tests with:  python -m unittest discover -s tests -v 
- Do not change an expected result merely to make a test pass. Raise any disagreement for review.
- Leave requirements, expected results, decision notes and the final judgment for the me to write.