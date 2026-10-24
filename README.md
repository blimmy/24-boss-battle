# 24 Boss Battle: Rainbow Princess

A pixel-art game where a princess solves Math 24 puzzles to beat three bosses.

## Purpose
For people who like quick math puzzles. The goal is to beat all three bosses as fast as possible.

## Requirements
- R1: Combine the four number tiles with + - × ÷, using each tile once, to make 24. Undo, Clear and Skip are available, and Skip gives another solvable puzzle and is counted.
- R2: A correct 24 automatically hits the boss for 20 damage (no Attack button). Bosses come in order: Cloud Slime (20 HP), Cursed Unicorn (40 HP), Rainbow Dragon (60 HP), so a full win takes six hits.
- R3: The timer starts at Start Game, keeps running through skips and stages, and stops when the last boss is defeated. The Victory screen shows time, attacks and skips, and Play Again resets everything.

## How to play
Click a number, an operator, then another number to make a new tile. Keep going until one tile is left.

Example: for 2, 3, 4, 6 → 3 - 2 = 1, 4 ÷ 1 = 4, 6 × 4 = 24. The princess attacks automatically.

## Setup and use
- Prerequisites: Python 3.11+, pip, and a desktop screen (Pygame).
- Setup (macOS / Linux):
     bash
  python3 -m venv .venv
  source .venv/bin/activate
  python3 -m pip install -r requirements.txt
     
- Setup (Windows PowerShell):
     powershell
  py -m venv .venv
  .venv\Scripts\Activate.ps1
  python -m pip install -r requirements.txt
     
- Run:  python3 main.py  (Windows:  python main.py ), then click Start Game.
- Run tests (with the virtual environment active):  python -m unittest discover -s tests -v 

The game uses PNG files in  asset/  (backgrounds, sprites, ui, effects) and works offline.

## Author and acknowledgements
- Name / student ID: Siriphanaphorn Sirikun / 6680085
- AI tools used: GitHub Copilot (planning, all code, debugging, tests). OpenAI Codex (image generation only, for the pixel-art PNGs; it wrote no code).
- External code/resources: None.
