# tanks/fast_tank.py — TANK TYPE 2: Fast Tank
# Agent Type  : Goal-Based Agent (single goal: destroy Eagle, ignores player)
# Search Algo : Greedy Best-First Search — uses Manhattan distance heuristic only
#
# Behaviour (from manual):
#   - ONLY goal is to reach and destroy the Eagle — ignores the player completely
#   - Every tick picks the neighbour tile with lowest Manhattan distance to Eagle
#   - If next tile is Brick — shoot it immediately, do NOT detour
#   - CAN get stuck in local minima (intentional — shows Greedy's weakness)
#   - No path caching — single-step decision every tick

from constants import *
from tank_base import TankBase

class FastTank(TankBase):
    def __init__(self):
        super().__init__(
            x         = 0,
            y         = 0,
            color     = FAST_TANK_COLOR,
            hp        = FAST_HP,            # 1 hit to destroy
            speed     = SPEED_FAST,         # Moves every 2 ticks (2x Basic Tank)
            fire_rate = 45,                 # Shoots every 1.5 seconds (45 ticks at 30fps)
            is_enemy  = True
        )

    # ------------------------------------------------------------------ #
    #  GREEDY HEURISTIC                                                    #
    # ------------------------------------------------------------------ #
    def heuristic(self, x, y):
        """
        h(n) = Manhattan distance from tile (x,y) to Eagle.
        This is the ONLY factor Greedy Best-First uses — no path cost.
        """
        ex, ey = EAGLE_POS
        return abs(x - ex) + abs(y - ey)

    def greedy_next_step(self, grid, all_tanks):
        """
        Greedy Best-First: pick the neighbouring tile with the lowest h(n).
        Does NOT compute a full path — just one step per tick.
        This is what causes local minima — it can get trapped.
        Returns (dx, dy) direction to move, or None if all neighbours blocked.
        """
        best_dir   = None
        best_score = float('inf')

        for dx, dy in DIRECTIONS:
            nx, ny = self.x + dx, self.y + dy

            # Skip out-of-bounds
            if not (0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE):
                continue

            tile = grid.get(nx, ny)

            # Skip steel and water — hard blockers, never enter
            if tile in (STEEL, WATER):
                continue

            # Skip tiles occupied by other tanks
            blocked_by_tank = any(
                t.alive and t is not self and t.x == nx and t.y == ny
                for t in all_tanks
            )
            if blocked_by_tank:
                continue

            # Score this neighbour using Manhattan distance heuristic only
            score = self.heuristic(nx, ny)
            if score < best_score:
                best_score = score
                best_dir   = (dx, dy)

        return best_dir

    # ------------------------------------------------------------------ #
    #  MAIN UPDATE — called every game tick                               #
    # ------------------------------------------------------------------ #
    def update(self, grid, all_tanks, player, bullets):
        """
        Goal-Based Agent: every action serves one goal — destroy the Eagle.
        Player is completely ignored (no line-of-sight check, no shooting at player).
        """
        self.tick_move_timer()
        self.tick_fire_timer()

        # Get greedy next direction toward Eagle
        direction = self.greedy_next_step(grid, all_tanks)

        if direction is None:
            # Completely stuck — local minima reached (intentional Greedy failure)
            return

        dx, dy = direction
        nx, ny = self.x + dx, self.y + dy
        tile   = grid.get(nx, ny)

        # ---- RULE: IF next tile is Brick THEN shoot it — do NOT detour ----
        # This is the key Goal-Based behaviour: push straight through, never go around
        if tile == BRICK:
            self.direction = (dx, dy)
            if self.can_shoot():
                bullet = self.shoot()
                if bullet:
                    bullets.append(bullet)
            return   # Wait for brick to be destroyed, then continue

        # ---- RULE: IF Eagle tile ahead THEN we've reached the goal ----
        if tile == EAGLE:
            self.direction = (dx, dy)
            if self.can_shoot():
                bullet = self.shoot()
                if bullet:
                    bullets.append(bullet)
            return

        # ---- RULE: Move toward Eagle (greedy step) ----
        if self.can_move():
            moved = self.try_move(dx, dy, grid, all_tanks)
            if moved:
                self.reset_move_timer()