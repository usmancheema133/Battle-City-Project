# tanks/basic_tank.py — TANK TYPE 1: Basic Tank
# Agent Type  : Simple Reflex Agent (no memory, pure IF-THEN rules)
# Search Algo : BFS (Breadth-First Search) — finds shortest-hop path to Eagle
#
# Behaviour (from manual):
#   - Follows the shortest open path to Eagle using BFS
#   - Shoots if player is in same row/column with no wall between
#   - Shoots brick walls that block its path, then resumes
#   - Re-runs BFS: at spawn, every 5 seconds, when path is blocked
#   - Has NO memory — decisions made purely from current percept (IF-THEN)

from collections import deque
import random
from constants import *
from tank_base import TankBase

class BasicTank(TankBase):
    def __init__(self):
        super().__init__(
            x         = 0,
            y         = 0,
            color     = BASIC_TANK_COLOR,
            hp        = BASIC_HP,           # 1 hit to destroy
            speed     = SPEED_SLOW,         # Moves every 4 ticks
            fire_rate = 90,                 # Shoots every 3 seconds (90 ticks at 30fps)
            is_enemy  = True
        )
        self.path        = []    # Current BFS path (list of (x,y) steps)
        self.bfs_timer   = 0    # Counts up — re-run BFS every 5 seconds (150 ticks)
        self.BFS_INTERVAL = 150  # 5 seconds * 30 fps

    # ------------------------------------------------------------------ #
    #  BFS PATHFINDING                                                     #
    # ------------------------------------------------------------------ #
    def run_bfs(self, grid):
        """
        Standard queue-based BFS from current position to Eagle.
        Treats EMPTY and FOREST as passable (cost = 1 each).
        Does NOT consider shooting through brick — that is handled separately.
        Returns a list of (x, y) tiles to follow, or empty list if no path.
        """
        start = (self.x, self.y)
        goal  = EAGLE_POS

        # BFS queue stores (position, path_so_far)
        queue   = deque()
        visited = set()
        queue.append((start, []))
        visited.add(start)

        while queue:
            (cx, cy), path = queue.popleft()

            # Check all 4 neighbours
            for dx, dy in DIRECTIONS:
                nx, ny = cx + dx, cy + dy

                if (nx, ny) in visited:
                    continue
                if not (0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE):
                    continue

                new_path = path + [(nx, ny)]
                tile     = grid.get(nx, ny)

                # Reached Eagle — return the path
                if tile == EAGLE:
                    return new_path

                # Passable tiles: EMPTY and FOREST only
                # BFS ignores brick (it will shoot it when it gets there)
                if tile in (EMPTY, FOREST):
                    visited.add((nx, ny))
                    queue.append(((nx, ny), new_path))

        return []   # No path found

    # ------------------------------------------------------------------ #
    #  LINE-OF-SIGHT CHECK                                                 #
    # ------------------------------------------------------------------ #
    def has_line_of_sight(self, grid, player):
        """
        Simple Reflex Rule: IF player is in same row OR column
        AND no wall between them THEN return True (shoot).
        """
        if not player or not player.alive:
            return False

        px, py = player.x, player.y

        # Same row — scan horizontally between self and player
        if self.y == py:
            step = 1 if px > self.x else -1
            for x in range(self.x + step, px, step):
                if grid.get(x, self.y) in (BRICK, STEEL, WATER):
                    return False
            return True

        # Same column — scan vertically between self and player
        if self.x == px:
            step = 1 if py > self.y else -1
            for y in range(self.y + step, py, step):
                if grid.get(self.x, y) in (BRICK, STEEL, WATER):
                    return False
            return True

        return False

    def face_player(self, player):
        """Turn to face the player for shooting."""
        if player.x > self.x:
            self.direction = RIGHT
        elif player.x < self.x:
            self.direction = LEFT
        elif player.y > self.y:
            self.direction = DOWN
        else:
            self.direction = UP

    # ------------------------------------------------------------------ #
    #  MAIN UPDATE — called every game tick                               #
    # ------------------------------------------------------------------ #
    def update(self, grid, all_tanks, player, bullets):
        """
        Simple Reflex Agent decision logic — pure IF-THEN rules, no memory.
        Order of rules matches the manual specification exactly.
        """
        self.tick_move_timer()
        self.tick_fire_timer()
        self.bfs_timer += 1

        # --- Re-run BFS if: no path, timer expired, or path tile is now blocked ---
        path_blocked = (
            len(self.path) > 0 and
            not grid.is_passable(self.path[0][0], self.path[0][1]) and
            grid.get(self.path[0][0], self.path[0][1]) != BRICK
        )

        if not self.path or self.bfs_timer >= self.BFS_INTERVAL or path_blocked:
            self.path      = self.run_bfs(grid)
            self.bfs_timer = 0

        # ---- RULE 1: IF player in line-of-sight THEN shoot ----
        if self.has_line_of_sight(grid, player) and self.can_shoot():
            self.face_player(player)
            bullet = self.shoot()
            if bullet:
                bullets.append(bullet)
            return   # Simple reflex: react and stop (no memory to continue with)

        # ---- RULE 2: IF next path tile is Brick THEN shoot it ----
        if self.path:
            nx, ny = self.path[0]
            if grid.get(nx, ny) == BRICK:
                # Face the brick and shoot
                self.direction = (nx - self.x, ny - self.y)
                if self.can_shoot():
                    bullet = self.shoot()
                    if bullet:
                        bullets.append(bullet)
                return   # Wait for brick to be destroyed before moving

        # ---- RULE 3: IF path exists THEN follow next BFS step ----
        if self.path and self.can_move():
            nx, ny  = self.path[0]
            dx, dy  = nx - self.x, ny - self.y
            moved   = self.try_move(dx, dy, grid, all_tanks)
            if moved:
                self.path.pop(0)   # Remove step we just completed
                self.reset_move_timer()
            else:
                # Path is blocked by another tank — re-plan next tick
                self.path = []

        # ---- RULE 4: ELSE turn to a random free direction ----
        elif not self.path and self.can_move():
            random.shuffle(list(DIRECTIONS))
            for dx, dy in DIRECTIONS:
                if self.try_move(dx, dy, grid, all_tanks):
                    self.reset_move_timer()
                    break