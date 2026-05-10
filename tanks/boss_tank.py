# tanks/boss_tank.py — TANK TYPE 4: Boss Tank (Tank Commander)
# Agent Type  : Adversarial Agent
# Search Algo : Minimax + Alpha-Beta Pruning
#
# Behaviour:
#   - 10 HP, 3 phases based on remaining HP
#   - Phase 1 (10-7 HP): Aggressive, Minimax depth 2
#   - Phase 2 (6-3 HP) : Balanced + seek cover, Minimax depth 3
#   - Phase 3 (2-1 HP) : Desperate rush, Minimax depth 4
#   - Alpha-Beta pruning makes depth 4 feasible in real-time
#   - Reports node counts (with/without pruning) to console

from constants import *
from tank_base import TankBase

BOSS_HP = 10

class BossTank(TankBase):
    def __init__(self):
        super().__init__(
            x         = 6,
            y         = 2,
            color     = BOSS_TANK_COLOR,
            hp        = BOSS_HP,
            speed     = SPEED_SLOW,
            fire_rate = 60,
            is_enemy  = True
        )
        self.phase             = 1
        self.nodes_no_pruning  = 0   # For report: nodes without Alpha-Beta
        self.nodes_with_pruning= 0   # For report: nodes with Alpha-Beta
        self.action_timer      = 0   # Ticks between Minimax decisions
        self.DECISION_INTERVAL = 20  # Run Minimax every 20 ticks

    # ──────────────────────────────────────────
    # PHASE SYSTEM
    # ──────────────────────────────────────────
    def update_phase(self):
        if self.hp >= 7:
            self.phase = 1
            self.speed     = SPEED_SLOW
            self.fire_rate = 60
        elif self.hp >= 3:
            self.phase = 2
            self.speed     = SPEED_MEDIUM
            self.fire_rate = 45
        else:
            self.phase = 3
            self.speed     = SPEED_FAST
            self.fire_rate = 24

    def get_depth(self):
        return {1: 2, 2: 3, 3: 4}[self.phase]

    # ──────────────────────────────────────────
    # EVALUATION HEURISTIC
    # ──────────────────────────────────────────
    def evaluate(self, boss_x, boss_y, boss_hp, player_x, player_y, player_hp, grid):
        score = 0

        dist = abs(boss_x - player_x) + abs(boss_y - player_y)

        # Player very close — high chance to shoot
        if dist <= 3:
            score += 60

        # Line of sight bonus
        if self._check_los(boss_x, boss_y, player_x, player_y, grid):
            score += 50

        # Cover behind steel
        for dx, dy in DIRECTIONS:
            nx, ny = boss_x + dx, boss_y + dy
            if 0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE:
                if grid.get(nx, ny) == STEEL:
                    score += 30
                    break

        # Player HP missing (player is weakened)
        score += (1 - player_hp) * 20

        # Boss HP missing — penalise
        score -= (BOSS_HP - boss_hp) * 40

        # Player in forest — uncertain position
        if grid.get(player_x, player_y) == FOREST:
            score -= 20

        # Proximity bonus (closer = better for boss)
        score += max(0, 20 - dist * 2)

        return score

    def _check_los(self, bx, by, px, py, grid):
        """Check line of sight between two positions."""
        if by == py:
            step = 1 if px > bx else -1
            for x in range(bx + step, px, step):
                if grid.get(x, by) in (BRICK, STEEL, WATER):
                    return False
            return True
        if bx == px:
            step = 1 if py > by else -1
            for y in range(by + step, py, step):
                if grid.get(bx, y) in (BRICK, STEEL, WATER):
                    return False
            return True
        return False

    # ──────────────────────────────────────────
    # GET LEGAL ACTIONS
    # ──────────────────────────────────────────
    def get_actions(self, x, y, grid):
        """Return list of legal (dx,dy) moves + shoot action."""
        actions = ["shoot"]
        for dx, dy in DIRECTIONS:
            nx, ny = x + dx, y + dy
            if 0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE:
                tile = grid.get(nx, ny)
                if tile in (EMPTY, FOREST, BRICK):
                    actions.append((dx, dy))
        return actions

    # ──────────────────────────────────────────
    # MINIMAX WITHOUT ALPHA-BETA (for node count)
    # ──────────────────────────────────────────
    def minimax_plain(self, depth, is_max,
                      boss_x, boss_y, boss_hp,
                      player_x, player_y, player_hp,
                      grid):
        self.nodes_no_pruning += 1

        if depth == 0 or boss_hp <= 0 or player_hp <= 0:
            return self.evaluate(boss_x, boss_y, boss_hp,
                                 player_x, player_y, player_hp, grid)

        if is_max:  # Boss turn — maximise
            best = float('-inf')
            for action in self.get_actions(boss_x, boss_y, grid):
                if action == "shoot":
                    new_php = player_hp - (1 if self._check_los(
                        boss_x, boss_y, player_x, player_y, grid) else 0)
                    val = self.minimax_plain(depth-1, False,
                                            boss_x, boss_y, boss_hp,
                                            player_x, player_y, new_php, grid)
                else:
                    dx, dy = action
                    val = self.minimax_plain(depth-1, False,
                                            boss_x+dx, boss_y+dy, boss_hp,
                                            player_x, player_y, player_hp, grid)
                best = max(best, val)
            return best
        else:       # Player turn — minimise
            best = float('inf')
            for action in self.get_actions(player_x, player_y, grid):
                if action == "shoot":
                    new_bhp = boss_hp - (1 if self._check_los(
                        player_x, player_y, boss_x, boss_y, grid) else 0)
                    val = self.minimax_plain(depth-1, True,
                                            boss_x, boss_y, new_bhp,
                                            player_x, player_y, player_hp, grid)
                else:
                    dx, dy = action
                    val = self.minimax_plain(depth-1, True,
                                            boss_x, boss_y, boss_hp,
                                            player_x+dx, player_y+dy, player_hp, grid)
                best = min(best, val)
            return best

    # ──────────────────────────────────────────
    # MINIMAX WITH ALPHA-BETA PRUNING
    # ──────────────────────────────────────────
    def minimax_ab(self, depth, is_max, alpha, beta,
                   boss_x, boss_y, boss_hp,
                   player_x, player_y, player_hp,
                   grid):
        self.nodes_with_pruning += 1

        if depth == 0 or boss_hp <= 0 or player_hp <= 0:
            return self.evaluate(boss_x, boss_y, boss_hp,
                                 player_x, player_y, player_hp, grid)

        if is_max:  # Boss — maximise
            best = float('-inf')
            for action in self.get_actions(boss_x, boss_y, grid):
                if action == "shoot":
                    new_php = player_hp - (1 if self._check_los(
                        boss_x, boss_y, player_x, player_y, grid) else 0)
                    val = self.minimax_ab(depth-1, False, alpha, beta,
                                         boss_x, boss_y, boss_hp,
                                         player_x, player_y, new_php, grid)
                else:
                    dx, dy = action
                    val = self.minimax_ab(depth-1, False, alpha, beta,
                                         boss_x+dx, boss_y+dy, boss_hp,
                                         player_x, player_y, player_hp, grid)
                best  = max(best, val)
                alpha = max(alpha, best)
                if alpha >= beta:
                    break   # ← Beta cutoff (pruning happens here)
            return best
        else:       # Player — minimise
            best = float('inf')
            for action in self.get_actions(player_x, player_y, grid):
                if action == "shoot":
                    new_bhp = boss_hp - (1 if self._check_los(
                        player_x, player_y, boss_x, boss_y, grid) else 0)
                    val = self.minimax_ab(depth-1, True, alpha, beta,
                                         boss_x, boss_y, new_bhp,
                                         player_x, player_y, player_hp, grid)
                else:
                    dx, dy = action
                    val = self.minimax_ab(depth-1, True, alpha, beta,
                                         boss_x, boss_y, boss_hp,
                                         player_x+dx, player_y+dy, player_hp, grid)
                best = min(best, val)
                beta = min(beta, best)
                if alpha >= beta:
                    break   # ← Alpha cutoff (pruning happens here)
            return best

    # ──────────────────────────────────────────
    # CHOOSE BEST ACTION (runs both for report)
    # ──────────────────────────────────────────
    def choose_action(self, player, grid):
        """
        Run Minimax with Alpha-Beta to pick best action.
        Also runs plain Minimax once to count nodes (for report).
        """
        depth = self.get_depth()

        # Count nodes WITHOUT pruning (report requirement)
        self.nodes_no_pruning = 0
        self.minimax_plain(depth, True,
                           self.x, self.y, self.hp,
                           player.x, player.y, player.hp,
                           grid)

        # Now find best action WITH Alpha-Beta
        self.nodes_with_pruning = 0
        best_val    = float('-inf')
        best_action = None
        alpha       = float('-inf')
        beta        = float('inf')

        for action in self.get_actions(self.x, self.y, grid):
            if action == "shoot":
                new_php = player.hp - (1 if self._check_los(
                    self.x, self.y, player.x, player.y, grid) else 0)
                val = self.minimax_ab(depth-1, False, alpha, beta,
                                      self.x, self.y, self.hp,
                                      player.x, player.y, new_php, grid)
            else:
                dx, dy = action
                val = self.minimax_ab(depth-1, False, alpha, beta,
                                      self.x+dx, self.y+dy, self.hp,
                                      player.x, player.y, player.hp, grid)
            if val > best_val:
                best_val    = val
                best_action = action
            alpha = max(alpha, best_val)

        # Print node counts for project report
        if self.nodes_no_pruning > 0:
            ratio = self.nodes_no_pruning / max(self.nodes_with_pruning, 1)
            print(f"[BOSS Phase {self.phase} Depth {depth}] "
                  f"No pruning: {self.nodes_no_pruning} nodes | "
                  f"Alpha-Beta: {self.nodes_with_pruning} nodes | "
                  f"Speedup: {ratio:.1f}x")

        return best_action

    # ──────────────────────────────────────────
    # TAKE HIT — override for phase tracking
    # ──────────────────────────────────────────
    def take_hit(self):
        self.hp -= 1
        self.flash_timer = 10
        if self.hp <= 0:
            self.alive = False
            return
        self.update_phase()
        # Color changes per phase
        phase_colors = {
            1: BOSS_TANK_COLOR,
            2: (255, 140,   0),   # Orange in phase 2
            3: (255,  30,  30),   # Red in phase 3
        }
        self.color = phase_colors.get(self.phase, BOSS_TANK_COLOR)
        print(f"[BOSS] Hit! HP={self.hp} → Phase {self.phase}")

    # ──────────────────────────────────────────
    # MAIN UPDATE
    # ──────────────────────────────────────────
    def update(self, grid, all_tanks, player, bullets):
        self.tick_move_timer()
        self.tick_fire_timer()

        self.action_timer -= 1
        if self.action_timer > 0:
            return

        self.action_timer = self.DECISION_INTERVAL
        self.update_phase()

        if not player or not player.alive:
            return

        # Choose best action via Minimax + Alpha-Beta
        action = self.choose_action(player, grid)

        if action is None:
            return

        if action == "shoot":
            # Face player and shoot
            self.direction = self._direction_to(player.x, player.y)
            if self.can_shoot():
                bullet = self.shoot()
                if bullet:
                    bullets.append(bullet)
        else:
            dx, dy = action
            self.direction = (dx, dy)
            if self.can_move():
                moved = self.try_move(dx, dy, grid, all_tanks)
                if moved:
                    self.reset_move_timer()

    def _direction_to(self, tx, ty):
        dx = tx - self.x
        dy = ty - self.y
        if abs(dx) >= abs(dy):
            return RIGHT if dx > 0 else LEFT
        return DOWN if dy > 0 else UP