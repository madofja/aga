import math
import random
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import pygame


# =========================
# CONFIG
# =========================
SCREEN_W, SCREEN_H = 1280, 840
PANEL_W = 320
WORLD_W = SCREEN_W - PANEL_W
FPS = 60
GRID_W = 120
GRID_H = 90
CELL = min(WORLD_W // GRID_W, SCREEN_H // GRID_H)
WORLD_PX_W = GRID_W * CELL
WORLD_PX_H = GRID_H * CELL

TARGET_AGENT_COUNT = 480
MAX_AGENT_COUNT = 1400
INITIAL_AGENT_COUNT = 420
INITIAL_RESOURCE_PATCHES = 950

TERRAIN_TYPES = ("water", "plains", "forest", "mountain", "desert", "ruins")
TERRAIN_COLORS = {
    "water": (45, 95, 210),
    "plains": (82, 176, 88),
    "forest": (30, 126, 52),
    "mountain": (138, 138, 140),
    "desert": (218, 194, 121),
    "ruins": (128, 93, 133),
}

BIOME_MOVE_COST = {
    "water": 1.85,
    "plains": 0.94,
    "forest": 1.05,
    "mountain": 1.40,
    "desert": 1.32,
    "ruins": 1.12,
}

BIOME_FOOD_BONUS = {
    "water": 0.65,
    "plains": 1.20,
    "forest": 1.30,
    "mountain": 0.85,
    "desert": 0.68,
    "ruins": 1.05,
}

TRIBE_COLORS = {
    "R": (255, 90, 90),
    "B": (85, 132, 255),
    "G": (88, 245, 145),
    "Y": (255, 225, 100),
    "P": (206, 132, 255),
    "C": (98, 228, 236),
}

SIGNALS = [
    "ra",
    "ki",
    "ul",
    "zen",
    "do",
    "mar",
    "shi",
    "vox",
    "ni",
    "qar",
    "tho",
    "el",
]


# =========================
# DATA MODELS
# =========================
@dataclass
class Storm:
    x: float
    y: float
    intensity: float
    radius: int
    dx: float
    dy: float


@dataclass
class Agent:
    x: int
    y: int
    energy: float
    tribe: str
    bias: float
    age: int
    curiosity: float
    aggression: float
    risk_aversion: float
    social_tolerance: float
    language: Dict[str, float] = field(default_factory=dict)
    memory_food: float = 0.0
    memory_danger: float = 0.0
    memory_coop: float = 0.0
    inventory: float = 0.0


class World:
    def __init__(self, seed: Optional[int] = None) -> None:
        self.rng = random.Random(seed)
        self.time_ticks = 0
        self.year = 1
        self.season = "Spring"
        self.temperature = 0.5
        self.running = True
        self.sim_speed = 1

        self.terrain = [["plains" for _ in range(GRID_H)] for _ in range(GRID_W)]
        self.wetness = [[0.0 for _ in range(GRID_H)] for _ in range(GRID_W)]
        self.rain = [[0.0 for _ in range(GRID_H)] for _ in range(GRID_W)]
        self.resources: Dict[Tuple[int, int], float] = {}

        self.storms: List[Storm] = [self._new_storm() for _ in range(6)]
        self.agents: List[Agent] = []

        self.stats_history: Dict[str, List[float]] = {
            "agents": [],
            "resources": [],
            "cohesion": [],
            "conflict": [],
            "rain": [],
        }

        self.generate_terrain()
        self.seed_resources(INITIAL_RESOURCE_PATCHES)
        self.spawn_agents(INITIAL_AGENT_COUNT)

    def _new_storm(self) -> Storm:
        return Storm(
            x=self.rng.uniform(0, GRID_W - 1),
            y=self.rng.uniform(0, GRID_H - 1),
            intensity=self.rng.uniform(0.35, 1.45),
            radius=self.rng.randint(4, 11),
            dx=self.rng.choice([-1.0, 1.0]) * self.rng.uniform(0.16, 0.54),
            dy=self.rng.choice([-1.0, 1.0]) * self.rng.uniform(0.16, 0.54),
        )

    def generate_terrain(self) -> None:
        cx, cy = GRID_W / 2, GRID_H / 2
        max_dist = math.hypot(cx, cy)
        for x in range(GRID_W):
            for y in range(GRID_H):
                nx, ny = x / GRID_W, y / GRID_H
                continental = 1.0 - math.hypot(x - cx, y - cy) / max_dist
                wave = (
                    math.sin(nx * 8.5)
                    + math.cos(ny * 9.2)
                    + math.sin((nx + ny) * 12.4)
                ) / 3.0
                noise = wave + self.rng.uniform(-0.35, 0.35)
                score = continental * 0.8 + noise * 0.55

                if score < -0.27:
                    biome = "water"
                elif score < 0.03:
                    biome = "desert"
                elif score < 0.22:
                    biome = "plains"
                elif score < 0.44:
                    biome = "forest"
                elif score < 0.66:
                    biome = "ruins"
                else:
                    biome = "mountain"
                self.terrain[x][y] = biome

    def seed_resources(self, count: int) -> None:
        for _ in range(count):
            x = self.rng.randint(0, GRID_W - 1)
            y = self.rng.randint(0, GRID_H - 1)
            biome = self.terrain[x][y]
            base = BIOME_FOOD_BONUS[biome] * self.rng.uniform(6, 18)
            if biome == "mountain" and self.rng.random() < 0.33:
                base += self.rng.uniform(6, 15)
            if biome == "ruins" and self.rng.random() < 0.44:
                base += self.rng.uniform(4, 20)
            self.resources[(x, y)] = self.resources.get((x, y), 0.0) + base

    def spawn_agents(self, count: int) -> None:
        tribes = list(TRIBE_COLORS.keys())
        for _ in range(count):
            while True:
                x = self.rng.randint(0, GRID_W - 1)
                y = self.rng.randint(0, GRID_H - 1)
                if self.terrain[x][y] != "water":
                    break
            tribe = self.rng.choice(tribes)
            vocab = {}
            for s in self.rng.sample(SIGNALS, k=self.rng.randint(3, 6)):
                vocab[s] = self.rng.uniform(0.2, 1.0)
            self.agents.append(
                Agent(
                    x=x,
                    y=y,
                    energy=self.rng.uniform(70, 130),
                    tribe=tribe,
                    bias=self.rng.uniform(0.2, 0.95),
                    age=self.rng.randint(0, 80),
                    curiosity=self.rng.uniform(0.1, 1.0),
                    aggression=self.rng.uniform(0.05, 1.0),
                    risk_aversion=self.rng.uniform(0.05, 1.0),
                    social_tolerance=self.rng.uniform(0.1, 1.0),
                    language=vocab,
                    memory_food=self.rng.uniform(-0.2, 0.2),
                    memory_danger=self.rng.uniform(-0.2, 0.2),
                    memory_coop=self.rng.uniform(-0.2, 0.2),
                    inventory=self.rng.uniform(0, 7),
                )
            )

    def update_climate(self) -> None:
        evap = 0.987
        for x in range(GRID_W):
            rain_col = self.rain[x]
            wet_col = self.wetness[x]
            for y in range(GRID_H):
                rain_col[y] *= evap
                wet_col[y] = max(0.0, min(2.6, wet_col[y] * 0.991 + rain_col[y] * 0.045))

        if self.time_ticks % 130 == 0 and len(self.storms) < 9:
            self.storms.append(self._new_storm())
        if self.time_ticks % 260 == 0 and len(self.storms) > 4:
            self.storms.pop(self.rng.randrange(len(self.storms)))

        for s in self.storms:
            seasonal = 1.0 + math.sin(self.time_ticks / 900) * 0.22
            s.x += s.dx * seasonal
            s.y += s.dy * seasonal
            if s.x < 0 or s.x >= GRID_W:
                s.dx *= -1
                s.x = max(0, min(GRID_W - 1, s.x))
            if s.y < 0 or s.y >= GRID_H:
                s.dy *= -1
                s.y = max(0, min(GRID_H - 1, s.y))

            ix, iy, r = int(s.x), int(s.y), s.radius
            for dx in range(-r, r + 1):
                tx = ix + dx
                if tx < 0 or tx >= GRID_W:
                    continue
                for dy in range(-r, r + 1):
                    ty = iy + dy
                    if ty < 0 or ty >= GRID_H:
                        continue
                    d2 = dx * dx + dy * dy
                    if d2 <= r * r:
                        falloff = 1.0 - (d2 / max(1.0, r * r))
                        self.rain[tx][ty] = min(
                            2.2, self.rain[tx][ty] + s.intensity * 0.042 * falloff
                        )

    def _pick_move(self, a: Agent) -> Tuple[int, int]:
        candidates = [(0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)]
        best = (a.x, a.y)
        best_score = -1e9
        for dx, dy in candidates:
            tx = max(0, min(GRID_W - 1, a.x + dx))
            ty = max(0, min(GRID_H - 1, a.y + dy))
            biome = self.terrain[tx][ty]
            wet = self.wetness[tx][ty]
            food_here = self.resources.get((tx, ty), 0.0)

            score = 0.0
            score += food_here * 0.28
            score += (BIOME_FOOD_BONUS[biome] - BIOME_MOVE_COST[biome]) * 3.2
            score -= wet * (0.75 + a.risk_aversion)
            if biome == "water":
                score -= 1.5 + a.risk_aversion * 2.8
            score += self.rng.uniform(-0.3, 0.3) * a.curiosity
            score += a.memory_food * 0.5
            score -= a.memory_danger * 0.4

            if score > best_score:
                best_score = score
                best = (tx, ty)
        return best

    def _communicate(self, cell_agents: List[Agent]) -> float:
        if len(cell_agents) < 2:
            return 0.0
        cohesion = 0.0
        for i in range(len(cell_agents) - 1):
            a = cell_agents[i]
            b = cell_agents[i + 1]
            shared = set(a.language.keys()) & set(b.language.keys())
            harmony = len(shared) * 0.03
            tribe_bonus = 0.06 if a.tribe == b.tribe else -0.02
            tolerance = (a.social_tolerance + b.social_tolerance) * 0.5
            mood = harmony + tribe_bonus + tolerance * 0.02
            if mood > 0:
                a.energy += mood * 1.3
                b.energy += mood * 1.3
                a.memory_coop = min(2.0, a.memory_coop + mood * 0.2)
                b.memory_coop = min(2.0, b.memory_coop + mood * 0.2)
                cohesion += mood
            else:
                a.energy += mood * 0.7
                b.energy += mood * 0.7
                a.memory_danger = min(2.0, a.memory_danger + abs(mood) * 0.18)
                b.memory_danger = min(2.0, b.memory_danger + abs(mood) * 0.18)

            if self.rng.random() < 0.25:
                token = self.rng.choice(list(a.language.keys()) or SIGNALS)
                a.language[token] = min(2.0, a.language.get(token, 0) + 0.04)
                b.language[token] = min(2.0, b.language.get(token, 0) + 0.04)
        return cohesion

    def _trade_or_conflict(self, cell_agents: List[Agent]) -> float:
        if len(cell_agents) < 2:
            return 0.0
        conflict = 0.0
        self.rng.shuffle(cell_agents)
        for i in range(0, len(cell_agents) - 1, 2):
            a = cell_agents[i]
            b = cell_agents[i + 1]
            trust = (a.social_tolerance + b.social_tolerance) * 0.5 + a.memory_coop * 0.08
            hostility = (a.aggression + b.aggression) * 0.5 + a.memory_danger * 0.12
            scarcity = 0.0 if (a.inventory + b.inventory) > 8 else 0.18
            if trust > hostility + scarcity:
                amount = min(1.2, a.inventory * 0.25)
                a.inventory -= amount
                b.inventory += amount * 0.9
                a.energy += 0.8
                b.energy += 0.6
            else:
                dmg = 0.9 + hostility
                a.energy -= dmg * self.rng.uniform(0.6, 1.2)
                b.energy -= dmg * self.rng.uniform(0.6, 1.2)
                conflict += dmg
        return conflict

    def _mutate_language(self, a: Agent) -> None:
        if self.rng.random() < 0.05:
            if a.language and self.rng.random() < 0.65:
                token = self.rng.choice(list(a.language.keys()))
                a.language[token] = max(0.05, a.language[token] + self.rng.uniform(-0.2, 0.25))
            else:
                token = self.rng.choice(SIGNALS)
                a.language[token] = a.language.get(token, 0.1) + self.rng.uniform(0.1, 0.3)

    def step(self) -> None:
        self.time_ticks += 1
        if self.time_ticks % 800 == 0:
            self.year += 1
            self.season = ["Spring", "Summer", "Autumn", "Winter"][self.year % 4]
        self.temperature = 0.5 + 0.35 * math.sin(self.time_ticks / 1300)

        self.update_climate()
        cell_map: Dict[Tuple[int, int], List[Agent]] = {}
        births: List[Agent] = []
        alive: List[Agent] = []

        total_rain = 0.0

        for a in self.agents:
            a.age += 1
            nx, ny = self._pick_move(a)
            biome = self.terrain[nx][ny]
            rain = self.rain[nx][ny]
            wet = self.wetness[nx][ny]
            total_rain += rain

            move_cost = BIOME_MOVE_COST[biome] * (1.0 + wet * 0.24)
            a.energy -= 0.11 + move_cost * 0.18 + max(0, self.temperature - 0.78) * 0.12
            a.x, a.y = nx, ny

            food = self.resources.get((nx, ny), 0.0)
            if food > 0:
                harvest = min(food, 0.9 + BIOME_FOOD_BONUS[biome] * 0.45)
                self.resources[(nx, ny)] = food - harvest
                if self.resources[(nx, ny)] <= 0.05:
                    del self.resources[(nx, ny)]
                eat = harvest * 0.7
                store = harvest * 0.3
                a.energy += eat * 2.2
                a.inventory += store
                a.memory_food = min(2.2, a.memory_food + 0.07)
            else:
                a.memory_food = max(-1.0, a.memory_food - 0.03)

            if rain > 1.2 and self.rng.random() < 0.46:
                a.energy -= 0.45
                a.memory_danger = min(2.5, a.memory_danger + 0.05)

            if a.inventory > 0.8 and a.energy < 52:
                consume = min(1.2, a.inventory)
                a.inventory -= consume
                a.energy += consume * 1.85

            self._mutate_language(a)

            if a.energy > 132 and len(self.agents) + len(births) < MAX_AGENT_COUNT:
                child_bias = max(0.08, min(0.98, a.bias + self.rng.uniform(-0.06, 0.06)))
                child = Agent(
                    x=a.x,
                    y=a.y,
                    energy=78,
                    tribe=a.tribe,
                    bias=child_bias,
                    age=0,
                    curiosity=max(0.05, min(1.0, a.curiosity + self.rng.uniform(-0.05, 0.05))),
                    aggression=max(0.05, min(1.0, a.aggression + self.rng.uniform(-0.05, 0.06))),
                    risk_aversion=max(0.05, min(1.0, a.risk_aversion + self.rng.uniform(-0.05, 0.05))),
                    social_tolerance=max(0.05, min(1.0, a.social_tolerance + self.rng.uniform(-0.06, 0.05))),
                    language=dict(a.language),
                    memory_food=a.memory_food * 0.4,
                    memory_danger=a.memory_danger * 0.4,
                    memory_coop=a.memory_coop * 0.4,
                )
                a.energy -= 28
                births.append(child)

            if a.energy > 0 and a.age < 4200:
                alive.append(a)
                cell_map.setdefault((a.x, a.y), []).append(a)

        cohesion_sum = 0.0
        conflict_sum = 0.0
        for loc_agents in cell_map.values():
            cohesion_sum += self._communicate(loc_agents)
            conflict_sum += self._trade_or_conflict(loc_agents)

        self.agents = alive + births

        if len(self.agents) < TARGET_AGENT_COUNT and self.time_ticks % 30 == 0:
            self.spawn_agents(min(18, TARGET_AGENT_COUNT - len(self.agents)))

        if self.time_ticks % 8 == 0:
            self.seed_resources(16)

        self.stats_history["agents"].append(len(self.agents))
        self.stats_history["resources"].append(sum(self.resources.values()))
        self.stats_history["cohesion"].append(cohesion_sum)
        self.stats_history["conflict"].append(conflict_sum)
        self.stats_history["rain"].append(total_rain / (GRID_W * GRID_H))

        for key in self.stats_history:
            if len(self.stats_history[key]) > 280:
                self.stats_history[key] = self.stats_history[key][-280:]


class Game:
    def __init__(self) -> None:
        pygame.init()
        pygame.font.init()
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption("Whisper Network: Sentient Society")
        self.clock = pygame.time.Clock()
        self.world = World()
        self.big_font = pygame.font.SysFont("consolas", 28, bold=True)
        self.font = pygame.font.SysFont("consolas", 18)
        self.small = pygame.font.SysFont("consolas", 14)
        self.show_help = False

    def draw_world(self) -> None:
        surf = self.screen
        for x in range(GRID_W):
            for y in range(GRID_H):
                biome = self.world.terrain[x][y]
                c = TERRAIN_COLORS[biome]
                rain = self.world.rain[x][y]
                wet = self.world.wetness[x][y]
                blue_boost = int(min(110, rain * 48 + wet * 28))
                col = (c[0], min(255, c[1] + blue_boost // 6), min(255, c[2] + blue_boost))
                px, py = x * CELL, y * CELL
                pygame.draw.rect(surf, col, (px, py, CELL, CELL))

        for (x, y), amount in self.world.resources.items():
            if amount <= 0:
                continue
            px = x * CELL + CELL // 2
            py = y * CELL + CELL // 2
            radius = 1 + int(min(3, amount / 16))
            glow = min(255, 160 + int(amount * 2.8))
            pygame.draw.circle(surf, (255, glow, 110), (px, py), radius)

        for _ in range(180):
            x = self.world.rng.randint(0, GRID_W - 1)
            y = self.world.rng.randint(0, GRID_H - 1)
            if self.world.rain[x][y] > 0.7:
                px = x * CELL
                py = y * CELL
                pygame.draw.line(surf, (160, 190, 255), (px, py), (px + 3, py + 6), 1)

        for a in self.world.agents:
            px = a.x * CELL + CELL // 2
            py = a.y * CELL + CELL // 2
            color = TRIBE_COLORS.get(a.tribe, (255, 255, 255))
            radius = 2 if a.energy < 45 else 3
            pygame.draw.circle(surf, color, (px, py), radius)

        pygame.draw.rect(
            surf,
            (0, 0, 0),
            (WORLD_PX_W, 0, SCREEN_W - WORLD_PX_W, SCREEN_H),
        )

    def _draw_line_graph(
        self,
        rect: pygame.Rect,
        values: List[float],
        color: Tuple[int, int, int],
        baseline_color: Tuple[int, int, int] = (80, 80, 80),
    ) -> None:
        pygame.draw.rect(self.screen, (16, 18, 22), rect)
        pygame.draw.rect(self.screen, (52, 55, 66), rect, 1)
        mid_y = rect.y + rect.height // 2
        pygame.draw.line(self.screen, baseline_color, (rect.x, mid_y), (rect.right, mid_y), 1)

        if len(values) < 2:
            return
        vmin = min(values)
        vmax = max(values)
        if math.isclose(vmin, vmax):
            vmax = vmin + 1.0
        points = []
        for i, v in enumerate(values):
            px = rect.x + int(i / (len(values) - 1) * (rect.width - 1))
            norm = (v - vmin) / (vmax - vmin)
            py = rect.bottom - int(norm * (rect.height - 1))
            points.append((px, py))
        if len(points) > 1:
            pygame.draw.lines(self.screen, color, False, points, 2)

    def draw_panel(self) -> None:
        x0 = WORLD_PX_W + 12
        y = 12
        draw = self.screen.blit

        title = self.big_font.render("Whisper Network", True, (236, 239, 255))
        draw(title, (x0, y))
        y += 34
        subtitle = self.small.render("Sentient Society", True, (170, 176, 214))
        draw(subtitle, (x0 + 2, y))
        y += 26

        w = self.world
        lines = [
            f"Year {w.year} / {w.season}",
            f"Ticks: {w.time_ticks}",
            f"Population: {len(w.agents)}",
            f"Resource Mass: {sum(w.resources.values()):.1f}",
            f"Storm Cells: {len(w.storms)}",
            f"Temp Index: {w.temperature:.2f}",
            f"Speed: {w.sim_speed}x",
        ]
        for line in lines:
            draw(self.font.render(line, True, (218, 218, 224)), (x0, y))
            y += 24

        y += 8
        self._draw_line_graph(
            pygame.Rect(x0, y, PANEL_W - 24, 90),
            w.stats_history["agents"],
            (88, 250, 144),
        )
        draw(self.small.render("Population", True, (180, 223, 189)), (x0 + 6, y + 6))
        y += 102
        self._draw_line_graph(
            pygame.Rect(x0, y, PANEL_W - 24, 90),
            w.stats_history["resources"],
            (255, 214, 107),
        )
        draw(self.small.render("Resources", True, (255, 228, 161)), (x0 + 6, y + 6))
        y += 102
        self._draw_line_graph(
            pygame.Rect(x0, y, PANEL_W - 24, 75),
            w.stats_history["cohesion"],
            (132, 181, 255),
        )
        draw(self.small.render("Social Cohesion", True, (170, 194, 248)), (x0 + 6, y + 6))
        y += 86
        self._draw_line_graph(
            pygame.Rect(x0, y, PANEL_W - 24, 75),
            w.stats_history["conflict"],
            (255, 132, 132),
        )
        draw(self.small.render("Conflict", True, (250, 165, 165)), (x0 + 6, y + 6))

        help_lines = [
            "Controls:",
            "Space: Pause/Resume",
            "Up/Down: Sim speed +/-",
            "R: Regenerate world",
            "H: Toggle help",
            "Esc: Quit",
        ]
        hy = SCREEN_H - 150
        for line in help_lines:
            draw(self.small.render(line, True, (177, 181, 194)), (x0, hy))
            hy += 21

        if self.show_help:
            overlay = pygame.Surface((WORLD_PX_W, WORLD_PX_H), pygame.SRCALPHA)
            overlay.fill((10, 10, 18, 180))
            self.screen.blit(overlay, (0, 0))
            tips = [
                "Observe population clusters around wet plains and forests.",
                "Heavy rain increases travel costs and can split civilizations.",
                "Shared language tokens improve cooperation outcomes.",
                "Scarcity drives conflict and tribal migration.",
                "No two runs produce the same history.",
            ]
            yy = 100
            self.screen.blit(
                self.big_font.render("Observer Mode", True, (255, 255, 255)),
                (80, yy),
            )
            yy += 54
            for tip in tips:
                self.screen.blit(self.font.render(f"- {tip}", True, (232, 232, 238)), (82, yy))
                yy += 32

    def handle_events(self) -> None:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                self.world.running = False
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    self.world.running = False
                elif e.key == pygame.K_SPACE:
                    self.world.sim_speed = 0 if self.world.sim_speed > 0 else 1
                elif e.key == pygame.K_UP:
                    self.world.sim_speed = min(12, max(1, self.world.sim_speed + 1))
                elif e.key == pygame.K_DOWN:
                    self.world.sim_speed = max(1, self.world.sim_speed - 1)
                elif e.key == pygame.K_r:
                    self.world = World()
                elif e.key == pygame.K_h:
                    self.show_help = not self.show_help

    def run(self) -> None:
        while self.world.running:
            self.clock.tick(FPS)
            self.handle_events()
            if self.world.sim_speed > 0:
                for _ in range(self.world.sim_speed):
                    self.world.step()

            self.draw_world()
            self.draw_panel()
            pygame.display.flip()

        pygame.quit()


def main() -> None:
    game = Game()
    game.run()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        pygame.quit()
        print(f"Fatal error: {exc}", file=sys.stderr)
        raise
