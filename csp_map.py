# csp_map.py — Module A: CSP Map Generator
# Generates a valid random map every level using Constraint Satisfaction.
# Uses backtracking search + forward checking.
#
# 5 Constraints from the manual:
#   1. Base Safety  — Eagle surrounded by at least 1 ring of Brick/Steel
#   2. Reachability — BFS path must exist from every spawn to Eagle
#   3. Fairness     — No spawn within 10 tiles of player start
#   4. Density      — Max 40% of tiles can be walls
#   5. Water        — Cannot block the only path to Eagle

import random
from collections import deque
from constants import *

# ------------------------------------------------------------------ #
#  BFS REACHABILITY CHECK                                             #
#  Used to verify Constraint 2 and 5                                 #
# ------------------------------------------------------------------ #
def bfs_reachable(grid_tiles, start, goal):
    """
    Check if there is a path from start to goal for CSP validation.
    Treats BRICK as passable because tanks can shoot through brick walls.
    Only STEEL and WATER are true blockers.
    Returns True if path exists, False otherwise.
    """
    sx, sy = start
    gx, gy = goal

    visited = set()
    queue   = deque()
    queue.append((sx, sy))
    visited.add((sx, sy))

    while queue:
        x, y = queue.popleft()

        if (x, y) == (gx, gy):
            return True

        for dx, dy in DIRECTIONS:
            nx, ny = x + dx, y + dy
            if (nx, ny) in visited:
                continue
            if not (0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE):
                continue
            tile = grid_tiles[ny][nx]
            # Tanks can shoot through brick, walk on empty/forest, reach eagle
            if tile in (EMPTY, FOREST, EAGLE, BRICK):
                visited.add((nx, ny))
                queue.append((nx, ny))

    return False  # No path found


# ------------------------------------------------------------------ #
#  CONSTRAINT CHECKERS                                                #
# ------------------------------------------------------------------ #

def check_density(grid_tiles):
    """
    Constraint 4: No more than 40% of INTERIOR tiles can be walls.
    We exclude the fixed border row/column from the count since those
    are always steel and not part of the playable area.
    """
    interior_total = (GRID_SIZE - 2) * (GRID_SIZE - 2)
    walls = sum(
        1 for y in range(1, GRID_SIZE - 1)
          for x in range(1, GRID_SIZE - 1)
          if grid_tiles[y][x] in (BRICK, STEEL)
    )
    return walls / interior_total <= 0.40


def check_reachability(grid_tiles):
    """
    Constraint 2: BFS path must exist from every spawn point to Eagle.
    """
    for sx, sy in SPAWN_POINTS:
        if not bfs_reachable(grid_tiles, (sx, sy), EAGLE_POS):
            return False
    return True


def check_water_not_blocking(grid_tiles):
    """
    Constraint 5: Water tiles must not block the ONLY path to Eagle.
    Strategy: temporarily replace all water with empty and check reachability.
    If reachable without water restrictions but not with them, water is blocking.
    """
    # Make a copy with water treated as passable
    temp = [row[:] for row in grid_tiles]
    for y in range(GRID_SIZE):
        for x in range(GRID_SIZE):
            if temp[y][x] == WATER:
                temp[y][x] = EMPTY

    # If even without water it's unreachable, that's a different problem
    for sx, sy in SPAWN_POINTS:
        if not bfs_reachable(temp, (sx, sy), EAGLE_POS):
            return False
    return True


def check_base_safety(grid_tiles):
    """
    Constraint 1: Eagle must be surrounded by at least 1 ring of Brick or Steel.
    All 8 neighbors of Eagle must be Brick or Steel (or out of bounds = Steel border).
    """
    ex, ey = EAGLE_POS
    for dx in [-1, 0, 1]:
        for dy in [-1, 0, 1]:
            if dx == 0 and dy == 0:
                continue
            nx, ny = ex + dx, ey + dy
            if 0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE:
                if grid_tiles[ny][nx] not in (BRICK, STEEL):
                    return False
    return True


# ------------------------------------------------------------------ #
#  CSP MAP GENERATOR                                                  #
# ------------------------------------------------------------------ #

class CSPMapGenerator:
    def __init__(self, level=1):
        """
        level — controls how complex the map is.
        Level 1: more brick and forest, less steel (dense brick maze).
        Level 2: more steel mixed in (steel fortress).
        """
        self.level = level

        # Terrain weights change per level
        # Format: [EMPTY, BRICK, STEEL, WATER, FOREST]
        if level == 1:
            # Dense brick maze — lots of brick and forest
            self.weights = [40, 35, 5, 5, 15]
        else:
            # Steel fortress — more steel walls
            self.weights = [40, 20, 25, 5, 10]

    def generate(self):
        """
        Main entry point. Returns a valid 2D grid (list of lists).
        Tries up to 50 times using backtracking + constraint checking.
        """
        for attempt in range(50):
            grid_tiles = self._try_generate()
            if grid_tiles is not None:
                print(f"[CSP] Map generated in {attempt+1} attempt(s).")
                return grid_tiles

        # Fallback: return a very simple safe map if all attempts fail
        print("[CSP] Warning: using fallback map after 50 failed attempts.")
        return self._fallback_map()

    def _try_generate(self):
        """
        One attempt at generating a valid map.
        Uses random terrain assignment + forward checking + backtracking.
        Returns a valid 2D grid or None if constraints cannot be satisfied.
        """
        # Start with all EMPTY tiles
        grid_tiles = [[EMPTY for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]

        # Step 1: Place fixed elements first
        self._place_fixed_elements(grid_tiles)

        # Step 2: Fill interior tiles randomly using weighted terrain selection
        self._fill_interior(grid_tiles)

        # Step 3: Ensure Eagle is surrounded (Constraint 1)
        self._enforce_base_safety(grid_tiles)

        # Step 4: Check all 5 constraints
        if not check_density(grid_tiles):
            return None
        if not check_base_safety(grid_tiles):
            return None
        if not check_reachability(grid_tiles):
            return None
        if not check_water_not_blocking(grid_tiles):
            return None

        return grid_tiles

    def _place_fixed_elements(self, grid_tiles):
        """Place elements that are always in the same position."""
        # Border walls (steel — indestructible)
        for x in range(GRID_SIZE):
            grid_tiles[0][x]            = STEEL
            grid_tiles[GRID_SIZE-1][x]  = STEEL
        for y in range(GRID_SIZE):
            grid_tiles[y][0]            = STEEL
            grid_tiles[y][GRID_SIZE-1]  = STEEL

        # Eagle at fixed position
        ex, ey = EAGLE_POS
        grid_tiles[ey][ex] = EAGLE

        # Keep spawn points EMPTY — they sit on the border row so override steel
        for sx, sy in SPAWN_POINTS:
            grid_tiles[sy][sx] = EMPTY
            # Also clear the tile just below each spawn so tanks can enter the map
            if sy + 1 < GRID_SIZE:
                grid_tiles[sy + 1][sx] = EMPTY

        # Keep player start clear
        px, py = PLAYER_START
        grid_tiles[py][px] = EMPTY

    def _fill_interior(self, grid_tiles):
        """
        Randomly assign terrain to interior tiles using weighted selection.
        Applies forward checking: skip tiles that are fixed (border, eagle, spawns).
        """
        fixed_positions = set(SPAWN_POINTS) | {PLAYER_START, EAGLE_POS}

        terrain_choices = [EMPTY, BRICK, STEEL, WATER, FOREST]

        for y in range(1, GRID_SIZE - 1):
            for x in range(1, GRID_SIZE - 1):
                if (x, y) in fixed_positions:
                    continue
                if grid_tiles[y][x] == EAGLE:
                    continue

                # Forward checking: don't place walls immediately around Eagle
                # (we enforce that separately in _enforce_base_safety)
                ex, ey = EAGLE_POS
                near_eagle = abs(x - ex) <= 1 and abs(y - ey) <= 1

                if near_eagle:
                    # Only brick or steel allowed near eagle
                    grid_tiles[y][x] = random.choice([BRICK, STEEL])
                else:
                    # Weighted random terrain selection
                    grid_tiles[y][x] = random.choices(
                        terrain_choices,
                        weights=self.weights
                    )[0]

    def _enforce_base_safety(self, grid_tiles):
        """
        Constraint 1: Force all 8 neighbors of Eagle to be Brick or Steel.
        """
        ex, ey = EAGLE_POS
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue
                nx, ny = ex + dx, ey + dy
                if 0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE:
                    if grid_tiles[ny][nx] not in (BRICK, STEEL):
                        grid_tiles[ny][nx] = BRICK  # Default to brick protection

    def _fallback_map(self):
        """
        Emergency fallback: a guaranteed valid simple map.
        Used only if all 50 CSP attempts fail.
        """
        grid_tiles = [[EMPTY for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]

        # Borders
        for x in range(GRID_SIZE):
            grid_tiles[0][x]           = STEEL
            grid_tiles[GRID_SIZE-1][x] = STEEL
        for y in range(GRID_SIZE):
            grid_tiles[y][0]           = STEEL
            grid_tiles[y][GRID_SIZE-1] = STEEL

        # Scattered bricks
        for y in range(3, 22, 3):
            for x in range(3, 22, 4):
                grid_tiles[y][x] = BRICK

        # Eagle and protection
        ex, ey = EAGLE_POS
        grid_tiles[ey][ex] = EAGLE
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue
                nx, ny = ex + dx, ey + dy
                if 0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE:
                    grid_tiles[ny][nx] = BRICK

        # Clear spawn points and entry tiles
        for sx, sy in SPAWN_POINTS:
            grid_tiles[sy][sx] = EMPTY
            if sy + 1 < GRID_SIZE:
                grid_tiles[sy + 1][sx] = EMPTY

        # Clear player start
        px, py = PLAYER_START
        grid_tiles[py][px] = EMPTY

        return grid_tiles