"""Asset-backed Pygame presentation; arithmetic and battle rules live separately."""

from __future__ import annotations

import json
import math
from pathlib import Path
import time

import pygame

from .combat import GameSession
from .puzzle import OPERATORS, PairReduction, format_value

LOGICAL_SIZE = (480, 270)
WINDOW_SIZE = (960, 540)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
ROOT = PROJECT_ROOT / "asset"
READY_MANIFEST = ROOT / "docs" / "READY_ASSETS.json"
INK = (72, 45, 100)
MUTED = (126, 100, 147)
RAINBOW = ("#ff9bc9", "#ffe9a8", "#a8efdc", "#a6d5ff", "#c4a5f5")


class GameUI:
    """Mouse hitboxes share layout with drawing; animation never blocks input events."""

    START_RECT = pygame.Rect(165, 221, 150, 32)
    RESTART_RECT = pygame.Rect(165, 221, 150, 32)
    ACTION_RECTS = {name: pygame.Rect(x, 222, 60, 24)
                    for name, x in (("UNDO", 270), ("CLEAR", 334), ("SKIP", 398))}
    OPERATOR_RECTS = {op: pygame.Rect(24 + i * 48, 222, 41, 26)
                      for i, op in enumerate(OPERATORS)}
    OPERATOR_ASSETS = dict(zip(OPERATORS, (
        "ui/tiles/tile_operator_plus.png", "ui/tiles/tile_operator_minus.png",
        "ui/tiles/tile_operator_multiply.png", "ui/tiles/tile_operator_divide.png")))
    CAST_DURATION = 0.40
    FLIGHT_DURATION = 0.48
    HIT_DURATION = 0.60
    TRANSITION_DURATION = 0.35
    IMPACT_AT = CAST_DURATION + FLIGHT_DURATION
    ATTACK_DURATION = IMPACT_AT + HIT_DURATION
    REQUIRED_ASSETS = (
        "backgrounds/start_screen_bg.png", "backgrounds/victory_bg.png",
        "ui/panels/hud.png", "ui/panels/puzzle.png", "ui/panels/welcome.png",
        "ui/panels/results.png", "ui/panels/instructions.png", "ui/buttons/button_start_game.png",
        "ui/buttons/button_play_again.png", "ui/buttons/button_skip.png",
        "ui/buttons/button_undo.png", "ui/buttons/button_clear.png",
        "ui/tiles/tile_number.png", "ui/tiles/tile_result.png",
        "ui/icons/icon_clock.png", "ui/icons/icon_crown.png",
        "effects/star.png", "effects/rainbow_projectile.png",
        "effects/hit_burst.png", "effects/rainbow_magic.png",
    ) + tuple(OPERATOR_ASSETS.values()) + tuple(
        f"sprites/princess/{state}_{frame}.png"
        for state in ("idle", "attack", "victory") for frame in range(1, 4)
    ) + tuple(spec.background for spec in GameSession.BOSSES) + tuple(
        f"sprites/{spec.sprite}/{state}_{frame}.png"
        for spec in GameSession.BOSSES for state in ("idle", "hit") for frame in range(1, 4)
    ) + tuple(spec.hp_asset(hp) for spec in GameSession.BOSSES
              for hp in range(0, spec.max_hp + 1, GameSession.DAMAGE_PER_SUCCESS))

    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.canvas = pygame.Surface(LOGICAL_SIZE)
        self.font = pygame.font.Font(None, 16)
        self.small_font = pygame.font.Font(None, 14)
        self.tile_font = pygame.font.Font(None, 24)
        self.title_font = pygame.font.Font(None, 30)
        self.session = GameSession()
        self.screen_name = "start"
        self.animation_time = 0.0
        self.attack_phase: str | None = None
        self.attack_elapsed = 0.0
        self.attack_stage = 0
        self.attack_old_hp = 0
        self.attack_builder: PairReduction | None = None
        self.attack_damage_applied = False
        self.transition_remaining = 0.0
        self.victory_time = 0.0
        self.hover_point = (-1, -1)
        self.images: dict[str, pygame.Surface] = {}
        self._scaled: dict[tuple[str, tuple[int, int]], pygame.Surface] = {}
        self.last_loaded_paths: tuple[str, ...] = ()
        self._load_images()

    @property
    def input_locked(self) -> bool:
        return self.attack_phase is not None or self.transition_remaining > 0

    @property
    def display_stage(self) -> int:
        # Keep the defeated boss/background on screen through its hit reaction.
        return self.attack_stage if self.attack_phase else self.session.stage

    def _load_images(self) -> None:
        if not READY_MANIFEST.is_file():
            raise FileNotFoundError(f"Missing asset manifest: {READY_MANIFEST}")
        manifest = json.loads(READY_MANIFEST.read_text(encoding="utf-8"))
        required = dict.fromkeys((*self.REQUIRED_ASSETS, *(
            path.removeprefix("asset/") for path in self._manifest_paths(manifest))))
        for relative in required:
            path = ROOT / relative
            if not path.is_file():
                raise FileNotFoundError(f"Missing required asset: {path}")
            try:
                self.images[relative] = pygame.image.load(str(path)).convert_alpha()
            except pygame.error as error:
                raise RuntimeError(f"Unable to load asset {path}: {error}") from error
        self.last_loaded_paths = tuple(str(ROOT / path) for path in required)

    @staticmethod
    def _manifest_paths(value: object) -> list[str]:
        if isinstance(value, str):
            return [value] if value.endswith(".png") else []
        if isinstance(value, dict):
            value = list(value.values())
        if isinstance(value, (list, tuple)):
            return [path for item in value for path in GameUI._manifest_paths(item)]
        return []

    def image(self, name: str, size: tuple[int, int] | None = None) -> pygame.Surface:
        image = self.images[name]
        if size is None or size == image.get_size():
            return image
        key = (name, size)
        if key not in self._scaled:
            self._scaled[key] = pygame.transform.scale(image, size)
        return self._scaled[key]

    def update(self, dt: float) -> None:
        dt = max(0.0, dt)
        self.animation_time += dt
        self.transition_remaining = max(0.0, self.transition_remaining - dt)
        if self.screen_name == "victory":
            self.victory_time += dt
        if self.attack_phase is None:
            return
        self.attack_elapsed += dt
        if self.attack_elapsed >= self.IMPACT_AT and not self.attack_damage_applied:
            self.session.attack()
            self.attack_damage_applied = True
        if self.attack_elapsed >= self.ATTACK_DURATION:
            leftover = self.attack_elapsed - self.ATTACK_DURATION
            self.attack_phase = None
            self.attack_builder = None
            if self.session.victory:
                self.screen_name = "victory"
                self.victory_time = leftover
            elif self.session.stage != self.attack_stage:
                self.transition_remaining = max(0.0, self.TRANSITION_DURATION - leftover)
        elif self.attack_elapsed >= self.IMPACT_AT:
            self.attack_phase = "hit"
        elif self.attack_elapsed >= self.CAST_DURATION:
            self.attack_phase = "projectile"
        else:
            self.attack_phase = "casting"

    def run(self) -> None:
        pacing = pygame.time.Clock()
        last_time = time.monotonic()
        running = True
        while running:
            now = time.monotonic()
            self.update(now - last_time)
            last_time = now
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEMOTION:
                    self.hover_point = self.logical_point(event.pos)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.click(self.logical_point(event.pos))
            self.draw()
            pygame.transform.scale(self.canvas, self.screen.get_size(), self.screen)
            pygame.display.flip()
            pacing.tick(60)

    def logical_point(self, point: tuple[int, int]) -> tuple[int, int]:
        return (point[0] * LOGICAL_SIZE[0] // self.screen.get_width(),
                point[1] * LOGICAL_SIZE[1] // self.screen.get_height())

    def click(self, point: tuple[int, int]) -> None:
        if self.screen_name == "start":
            if self.START_RECT.collidepoint(point):
                self.session.start()
                self.screen_name = "battle"
            return
        if self.screen_name == "victory":
            if self.RESTART_RECT.collidepoint(point):
                self.session.restart()
                self.session.start()
                self.attack_phase = None
                self.attack_elapsed = self.transition_remaining = self.victory_time = 0.0
                self.attack_stage = self.attack_old_hp = 0
                self.attack_damage_applied = False
                self.attack_builder = None
                self.screen_name = "battle"
            return
        if self.input_locked or self.session.victory:
            return
        builder = self.session.builder
        for tile_id, rect in self._tile_rects(builder).items():
            if rect.collidepoint(point):
                if builder.select_tile(tile_id) and builder.complete:
                    self._start_auto_attack()
                return
        for operator, rect in self.OPERATOR_RECTS.items():
            if rect.collidepoint(point):
                builder.select_operator(operator)
                return
        for action, rect in self.ACTION_RECTS.items():
            if rect.collidepoint(point):
                self._action(action)
                return

    def _action(self, action: str) -> None:
        if self.input_locked or self.session.victory:
            return
        if action == "SKIP":
            self.session.skip()
        elif action == "UNDO":
            self.session.builder.undo()
        elif action == "CLEAR":
            self.session.builder.clear()

    def _start_auto_attack(self) -> None:
        if (self.input_locked or self.session.victory or not self.session.builder.complete
                or self.session.started_at is None):
            return
        self.attack_phase = "casting"
        self.attack_elapsed = 0.0
        self.attack_stage = self.session.stage
        self.attack_old_hp = self.session.boss.hp
        self.attack_builder = self.session.builder
        self.attack_damage_applied = False

    def _tile_rects(self, builder: PairReduction) -> dict[int, pygame.Rect]:
        return {tile.id: pygame.Rect(24 + tile.id * 52 if not tile.result else
                                    270 + (tile.id - 4) * 56, 186, 44, 29)
                for tile in builder.tiles}

    def draw(self) -> None:
        if self.screen_name == "start":
            self.draw_start()
        elif self.screen_name == "battle":
            self.draw_battle()
        else:
            self.draw_victory()

    def text(self, value: str, position: tuple[int, int], large: bool = False,
             *, color=INK, center: bool = False, small: bool = False) -> None:
        font = self.title_font if large else self.small_font if small else self.font
        rendered = font.render(value, False, color)
        rect = rendered.get_rect(midtop=position) if center else rendered.get_rect(topleft=position)
        self.canvas.blit(rendered, rect)

    def background(self, name: str) -> None:
        # Source backgrounds are effectively 16:9; fit and crop the subpixel excess.
        self.blit_asset(name, (0, 0), LOGICAL_SIZE)

    def draw_start(self) -> None:
        self.background("backgrounds/start_screen_bg.png")
        self.blit_asset("ui/panels/welcome.png", (94, 14))
        self.text("24 BOSS BATTLE", (240, 23), True, center=True)
        self.text("R A I N B O W   P R I N C E S S", (240, 51), center=True)
        bob = round(math.sin(self.animation_time * 2.5) * 2)
        self.character("princess", "idle", (240, 174 + bob), (88, 91))
        self.blit_asset("ui/panels/instructions.png", (94, 177))
        self.text("Tile  >  operator  >  tile. Use all four to make 24!",
                  (240, 185), center=True)
        self.text("Six rainbow spells. Three bosses. One kingdom to save.",
                  (240, 200), center=True, small=True, color=MUTED)
        self.button(self.START_RECT, "START GAME", "start_game")

    def draw_battle(self) -> None:
        stage = self.display_stage
        spec = self.session.BOSSES[stage]
        boss = self.session.bosses[stage]
        self.background(spec.background)
        self.blit_asset("ui/panels/hud.png", (10, 5))
        self.text(f"{stage + 1:02d}  /  {boss.name.upper()}", (21, 12))
        self.hp_bar(stage)
        self.blit_asset("ui/icons/icon_clock.png", (330, 12), (10, 10))
        self.text(self.session.formatted_time(), (345, 12))
        self.text(f"SKIPS {self.session.skips}    SPELLS {self.session.successful_attacks}/6",
                  (330, 29), small=True, color=MUTED)
        self.text(spec.setting, (240, 53), center=True, small=True)
        bob = round(math.sin(self.animation_time * 2.5) * 2)
        self.character("princess", "attack" if self.attack_phase in ("casting", "projectile")
                       else "idle", (90, 161 + bob), (86, 90))
        shake = round(math.sin(self.attack_elapsed * 85) * 3 *
                      (1 - self.hit_progress)) if self.attack_phase == "hit" else 0
        self.character(spec.sprite, "hit" if self.attack_phase == "hit" else "idle",
                       (383 + shake, 161 + (0 if self.attack_phase == "hit" else bob)),
                       (100, 94))
        self.draw_effects()
        if self.transition_remaining:
            self.text("STAGE CLEAR!", (240, 101), center=True)
        elif self.attack_phase == "casting":
            self.text("24! RAINBOW MAGIC", (240, 88), center=True)
        self.blit_asset("ui/panels/puzzle.png", (10, 168))
        self.text("YOUR FOUR NUMBERS", (24, 175), small=True, color=MUTED)
        self.text("COMBINED TILES", (270, 175), small=True, color=MUTED)
        builder = self.attack_builder if self.attack_phase else self.session.builder
        rects = self._tile_rects(builder)
        for tile in builder.tiles:
            self.tile(rects[tile.id], format_value(tile.value), result=tile.result,
                      active=tile.active, selected=tile.id == builder.selected_id)
        for op, rect in self.OPERATOR_RECTS.items():
            self.canvas.blit(self.image(self.OPERATOR_ASSETS[op], rect.size), rect)
            self.highlight(rect, builder.operator == op, not self.input_locked)
        for action, rect in self.ACTION_RECTS.items():
            self.button(rect, action, action.lower(), enabled=not self.input_locked)
        feedback = "Rainbow spell in flight..." if self.attack_phase else builder.feedback
        self.text(feedback, (240, 253), center=True, small=True)

    def draw_victory(self) -> None:
        self.background("backgrounds/victory_bg.png")
        self.draw_celebration()
        self.blit_asset("ui/panels/welcome.png", (94, 14))
        self.text("KINGDOM SAVED!", (240, 25), True, center=True)
        self.text("Every color has found its way home.", (240, 57), center=True)
        self.character("princess", "victory", (100, 199), (104, 110))
        self.blit_asset("ui/panels/results.png", (213, 96))
        self.text("YOUR ROYAL RESULTS", (330, 106), center=True)
        self.text(self.session.formatted_time(), (330, 126), True, center=True)
        self.text(f"Successful spells     {self.session.successful_attacks}", (233, 158))
        self.text(f"Puzzles skipped       {self.session.skips}", (233, 175))
        self.text("THREE BOSSES / ALL COLORS RESTORED", (330, 193), center=True,
                  small=True, color=MUTED)
        self.button(self.RESTART_RECT, "PLAY AGAIN", "play_again")

    def tile(self, rect: pygame.Rect, label: str, *, result: bool = False,
             active: bool = True, selected: bool = False) -> None:
        key = "ui/tiles/tile_result.png" if result else "ui/tiles/tile_number.png"
        surface = self.image(key, rect.size).copy()
        rendered = self.tile_font.render(label, False, INK)
        # Large integers and fractions fit the same tile without clipping.
        limit = pygame.Rect(0, 0, rect.width - 10, rect.height - 10)
        if rendered.get_width() > limit.width or rendered.get_height() > limit.height:
            rendered = pygame.transform.scale(rendered, rendered.get_rect().fit(limit).size)
        surface.blit(rendered, rendered.get_rect(center=(rect.width//2-1, rect.height//2-1)))
        if not active:
            surface.fill((255, 255, 255, 85), special_flags=pygame.BLEND_RGBA_MULT)
        self.canvas.blit(surface, rect)
        if active:
            self.highlight(rect, selected, not self.input_locked)

    def highlight(self, rect: pygame.Rect, selected: bool, enabled: bool = True) -> None:
        if selected:
            pygame.draw.rect(self.canvas, "#8e4cba", rect.inflate(4, 4), 2, border_radius=3)
            pygame.draw.rect(self.canvas, "#fffbe2", rect.inflate(2, 2), 1, border_radius=2)
        elif enabled and rect.collidepoint(self.hover_point):
            pygame.draw.rect(self.canvas, "#bd7dd0", rect.inflate(2, 2), 1, border_radius=3)

    def button(self, rect: pygame.Rect, label: str, asset: str, *, enabled: bool = True) -> None:
        surface = self.image(f"ui/buttons/button_{asset}.png", rect.size).copy()
        rendered = self.font.render(label, False, INK if enabled else MUTED)
        surface.blit(rendered, rendered.get_rect(center=(rect.width//2-1, rect.height//2-1)))
        if not enabled:
            surface.fill((255, 255, 255, 140), special_flags=pygame.BLEND_RGBA_MULT)
        self.canvas.blit(surface, rect)
        self.highlight(rect, False, enabled)

    @property
    def hit_progress(self) -> float:
        return min(1.0, max(0.0, (self.attack_elapsed - self.IMPACT_AT) / self.HIT_DURATION))

    def hp_bar(self, stage: int) -> None:
        spec, boss = self.session.BOSSES[stage], self.session.bosses[stage]
        size, position = (180, 14), (21, 28)
        target = self.image(spec.hp_asset(boss.hp), size)
        if self.attack_phase == "hit":
            # Wipe between the exact PNG endpoints as the filled portion shrinks.
            old = self.image(spec.hp_asset(self.attack_old_hp), size)
            self.canvas.blit(old, position)
            progress = min(1.0, self.hit_progress * 1.7)
            hp = boss.hp + (self.attack_old_hp - boss.hp) * (1 - progress) ** 2
            boundary = round(3 + 174 * hp / boss.max_hp) if progress < 1 else 0
            self.canvas.blit(target, (position[0] + boundary, position[1]),
                             pygame.Rect(boundary, 0, size[0] - boundary, size[1]))
        else:
            self.canvas.blit(target, position)
        self.text(f"{boss.hp} / {boss.max_hp} HP", (210, 30), small=True)

    def draw_effects(self) -> None:
        phase = self.attack_phase
        if phase is None:
            return
        if phase == "casting":
            p = self.attack_elapsed / self.CAST_DURATION
            self.blit_asset("effects/rainbow_magic.png", (107, 94))
            for i in range(8):
                angle = i * math.tau / 8 + p * 3
                radius = 24 * (1 - p) + 5
                self.blit_asset("effects/star.png", (int(119 + math.cos(angle)*radius),
                                                     int(108 + math.sin(angle)*radius)))
        elif phase == "projectile":
            p = (self.attack_elapsed - self.CAST_DURATION) / self.FLIGHT_DURATION
            x, y = int(120 + p * 242), int(111 - math.sin(p*math.pi)*15)
            for i, color in enumerate(RAINBOW):
                pygame.draw.line(self.canvas, color, (max(120, x-65), y+4+i*2),
                                 (x+9, y+4+i*2), 2)
            self.blit_asset("effects/rainbow_projectile.png", (x, y))
            for i in range(5):
                self.blit_asset("effects/star.png", (x - i*12, y + (i%2)*15-5), (5,5))
        elif phase == "hit":
            p = self.hit_progress
            burst = self.image("effects/hit_burst.png").copy()
            burst.fill((255, 255, 255, round(255 * (1 - p))),
                       special_flags=pygame.BLEND_RGBA_MULT)
            self.canvas.blit(burst, (365, 103))
            for i in range(16):
                angle = i * math.tau / 16
                radius = 6 + p * 36
                star = self.image("effects/star.png", (5,5)).copy()
                star.fill((255, 255, 255, round(255*(1-p))),
                          special_flags=pygame.BLEND_RGBA_MULT)
                self.canvas.blit(star, (int(383+math.cos(angle)*radius),
                                        int(120+math.sin(angle)*radius)))
            self.text(f"-{self.session.DAMAGE_PER_SUCCESS} HP", (300, int(112-p*20)), center=True,
                      color=(127, 43, 115))

    def draw_celebration(self) -> None:
        # A finite celebration, separate from battle's temporary attack effects.
        if self.victory_time > 4:
            return
        for i in range(42):
            x = (i*71 + int(math.sin(self.victory_time+i)*8)) % 480
            y = int(-60 + (i*19)%160 + self.victory_time*(28+i%12))
            pygame.draw.rect(self.canvas, RAINBOW[i%5], (x, y, 3, 5))

    def character(self, name: str, state: str, foot: tuple[int, int],
                  bounds: tuple[int, int]) -> None:
        phase_time = (self.attack_elapsed - self.IMPACT_AT if state == "hit" else
                      self.attack_elapsed if state == "attack" else self.animation_time)
        index = (min(2, int(max(0, phase_time) * (3 / self.HIT_DURATION))) if state == "hit"
                 else min(2, int(phase_time * 7)) if state == "attack"
                 else int(phase_time * 4) % 3) + 1
        key = f"sprites/{name}/{state}_{index}.png"
        image = self.images[key]
        size = image.get_rect().fit(pygame.Rect((0, 0), bounds)).size
        sprite = self.image(key, size)
        self.canvas.blit(sprite, sprite.get_rect(midbottom=foot))

    def blit_asset(self, name: str, position: tuple[int, int],
                   size: tuple[int, int] | None = None) -> None:
        self.canvas.blit(self.image(name, size), position)
