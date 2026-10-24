import pygame

from game.ui import GameUI, WINDOW_SIZE


def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode(WINDOW_SIZE)
    pygame.display.set_caption("24 Boss Battle: Rainbow Princess")
    try:
        GameUI(screen).run()
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
