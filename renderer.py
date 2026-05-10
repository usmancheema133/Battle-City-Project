# renderer.py — Draws everything to the screen
# Draws: grid tiles, tanks, bullets, HUD (lives, enemy count, level)

import pygame
from constants import *

class Renderer:
    def __init__(self, screen, font):
        self.screen = screen
        self.font   = font
        self.big_font = pygame.font.SysFont(None, 48)

    def draw_grid(self, grid):
        """Draw all 26x26 tiles using their terrain color."""
        for y in range(GRID_SIZE):
            for x in range(GRID_SIZE):
                terrain = grid.get(x, y)
                color   = TERRAIN_COLORS.get(terrain, BLACK)
                rect    = (x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                pygame.draw.rect(self.screen, color, rect)

                # Draw a subtle grid line so tiles are distinguishable
                pygame.draw.rect(self.screen, (20, 20, 20), rect, 1)

                # Extra detail for Eagle tile — draw a star/symbol
                if terrain == EAGLE:
                    cx = x * TILE_SIZE + TILE_SIZE // 2
                    cy = y * TILE_SIZE + TILE_SIZE // 2
                    pygame.draw.circle(self.screen, BLACK, (cx, cy), 5)

    def draw_tanks(self, player, enemy_tanks):
        """Draw the player and all living enemy tanks."""
        if player and player.alive:
            player.draw(self.screen)

        for tank in enemy_tanks:
            if tank.alive:
                tank.draw(self.screen)

    def draw_bullets(self, bullets):
        """Draw all active bullets."""
        for bullet in bullets:
            if bullet.alive:
                bullet.draw(self.screen)

    def draw_hud(self, player, enemy_pool_remaining, level_num):
        """
        Draw the HUD panel on the right side of the screen.
        Shows: lives, enemies left, current level.
        """
        hud_x = GRID_SIZE * TILE_SIZE + 10   # Start of HUD area
        hud_w = 180
        hud_h = SCREEN_HEIGHT

        # HUD background
        pygame.draw.rect(self.screen, (20, 20, 20), (hud_x - 5, 0, hud_w + 10, hud_h))

        # Level number
        self._text(f"LEVEL {level_num}", hud_x, 20, YELLOW)

        # Player lives
        self._text("LIVES:", hud_x, 60, WHITE)
        for i in range(player.lives if player else 0):
            lx = hud_x + i * 20
            pygame.draw.rect(self.screen, PLAYER_COLOR, (lx, 80, 14, 14))

        # Enemies remaining in pool
        self._text("ENEMIES:", hud_x, 120, WHITE)
        self._text(str(enemy_pool_remaining), hud_x, 145, RED)

        # Controls reminder
        self._text("MOVE: WASD", hud_x, 200, GRAY)
        self._text("SHOOT: SPACE", hud_x, 220, GRAY)

    def draw_message(self, msg, color=WHITE):
        """Draw a big centered message (WIN / LOSE / NEXT LEVEL)."""
        text = self.big_font.render(msg, True, color)
        x = (GRID_SIZE * TILE_SIZE) // 2 - text.get_width() // 2
        y = (SCREEN_HEIGHT)          // 2 - text.get_height() // 2
        # Dark background behind text
        pygame.draw.rect(self.screen, BLACK, (x - 10, y - 10,
                                               text.get_width() + 20,
                                               text.get_height() + 20))
        self.screen.blit(text, (x, y))

    def _text(self, msg, x, y, color):
        """Helper: render a small text label."""
        surf = self.font.render(msg, True, color)
        self.screen.blit(surf, (x, y))
