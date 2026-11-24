"""Модуль графической отрисовки и анимации игры «Астероиды» на Canvas."""

import math
import random
import tkinter as tk
from typing import Dict, List, Tuple

from src.config import (
    BG_ASTEROIDS_COUNT,
    BG_SCROLL_SPEED,
    HEIGHT,
    SPLASH_HEIGHT,
    SPLASH_WIDTH,
    WIDTH,
)
from src.models.game_objects import Asteroid, Explosion, Missile, Ship


class Renderer:
    """Класс, отвечающий за рендеринг сцены, объектов, анимаций и интерфейса."""

    def __init__(self, canvas: tk.Canvas) -> None:
        """Инициализировать рендерер и сгенерировать слои космического фона."""
        self.canvas = canvas
        palette = ("#ffffff", "#dbeafe", "#fef08a", "#c4b5fd", "#93c5fd")
        self.stars = [
            (random.randint(0, WIDTH), random.randint(0, HEIGHT), random.randint(1, 3), random.choice(palette))
            for _ in range(95)
        ]
        self.bg_debris: List[Dict[str, float]] = [
            {
                "x": random.uniform(0, WIDTH),
                "y": random.uniform(20, HEIGHT - 20),
                "r": random.uniform(14, 34),
                "angle": random.uniform(0, 360),
                "rot": random.uniform(-0.4, 0.4),
            }
            for _ in range(BG_ASTEROIDS_COUNT)
        ]

    def update_background(self) -> None:
        """Сдвинуть динамический фон астероидов влево с постоянной скоростью."""
        for item in self.bg_debris:
            item["x"] = (item["x"] - BG_SCROLL_SPEED) % WIDTH
            item["angle"] = (item["angle"] + item["rot"]) % 360.0

    def draw_background(self) -> None:
        """Отрисовать неподвижный космос и движущийся полупрозрачный слой."""
        self.canvas.delete("all")
        self.canvas.configure(bg="#060814")
        self.canvas.create_oval(90, 70, 360, 310, fill="#111633", outline="", stipple="gray50")
        self.canvas.create_oval(450, 260, 760, 540, fill="#1b1130", outline="", stipple="gray50")

        for x, y, size, color in self.stars:
            self.canvas.create_oval(x, y, x + size, y + size, fill=color, outline="")

        for item in self.bg_debris:
            cx, cy, r, rad = item["x"], item["y"], item["r"], math.radians(item["angle"])
            pts: List[float] = []
            for i in range(8):
                theta = rad + (2.0 * math.pi * i) / 8.0
                dist = r * (0.85 if i % 2 == 0 else 1.0)
                pts.extend([cx + math.cos(theta) * dist, cy + math.sin(theta) * dist])
            self.canvas.create_polygon(pts, fill="#283556", outline="#3b4d7a", width=1, stipple="gray50")

    def _get_wrap_positions(self, x: float, y: float, margin: float) -> List[Tuple[float, float]]:
        """Получить координаты дублирования объекта у границ тороидального экрана."""
        xs = [x] + ([x + WIDTH] if x < margin else ([x - WIDTH] if x > WIDTH - margin else []))
        ys = [y] + ([y + HEIGHT] if y < margin else ([y - HEIGHT] if y > HEIGHT - margin else []))
        return [(px, py) for px in xs for py in ys]

    def draw_ship(self, ship: Ship) -> None:
        """Отрисовать корабль (обычный или с пламенем включённых двигателей)."""
        for cx, cy in self._get_wrap_positions(ship.x, ship.y, ship.radius + 12):
            rad = math.radians(ship.angle)
            cos_a, sin_a = math.cos(rad), math.sin(rad)

            def to_world(lx: float, ly: float) -> Tuple[float, float]:
                return cx + lx * cos_a - ly * sin_a, cy + lx * sin_a + ly * cos_a

            if ship.thrust:
                flame_len = random.uniform(26.0, 36.0)
                self.canvas.create_polygon(
                    [to_world(-13, -7), to_world(-flame_len, 0), to_world(-13, 7)],
                    fill="#f97316", outline="#fde047", width=1,
                )
                self.canvas.create_polygon(
                    [to_world(-13, -4), to_world(-flame_len * 0.65, 0), to_world(-13, 4)],
                    fill="#fef08a", outline="",
                )

            self.canvas.create_polygon(
                [to_world(22, 0), to_world(-14, -14), to_world(-8, 0), to_world(-14, 14)],
                fill="#e2e8f0", outline="#38bdf8", width=2,
            )
            self.canvas.create_polygon(
                [to_world(8, 0), to_world(-2, -5), to_world(-2, 5)],
                fill="#0284c7", outline="#bae6fd", width=1,
            )

    def draw_asteroid(self, asteroid: Asteroid) -> None:
        """Отрисовать вращающийся астероид с рельефом и кратерами."""
        for cx, cy in self._get_wrap_positions(asteroid.x, asteroid.y, asteroid.radius + 8):
            rad_offset = math.radians(asteroid.angle)
            pts: List[float] = []
            for theta, factor in asteroid.shape_offsets:
                r = asteroid.radius * factor
                pts.extend([cx + math.cos(theta + rad_offset) * r, cy + math.sin(theta + rad_offset) * r])
            self.canvas.create_polygon(pts, fill="#64748b", outline="#cbd5e1", width=2)

            cr_x = cx + math.cos(rad_offset) * (asteroid.radius * 0.32)
            cr_y = cy + math.sin(rad_offset) * (asteroid.radius * 0.32)
            cr_r = asteroid.radius * 0.24
            self.canvas.create_oval(
                cr_x - cr_r, cr_y - cr_r, cr_x + cr_r, cr_y + cr_r,
                fill="#475569", outline="#94a3b8", width=1,
            )

    def draw_missile(self, missile: Missile) -> None:
        """Отрисовать летящую ракету со световым следом."""
        x, y, r = missile.x, missile.y, missile.radius
        self.canvas.create_oval(x - r - 2, y - r - 2, x + r + 2, y + r + 2, fill="#f97316", outline="")
        self.canvas.create_oval(x - r, y - r, x + r, y + r, fill="#fef08a", outline="#ffffff", width=1)

    def draw_explosion(self, explosion: Explosion) -> None:
        """Отрисовать текущий кадр тайловой (покадровой) анимации взрыва."""
        cx, cy, progress, outer_r = explosion.x, explosion.y, explosion.progress, explosion.current_radius
        if outer_r <= 1.0:
            return
        if progress < 0.85:
            self.canvas.create_oval(
                cx - outer_r, cy - outer_r, cx + outer_r, cy + outer_r,
                fill="#ea580c", outline="#facc15", width=2, stipple="gray75" if progress > 0.5 else "",
            )
        mid_r = outer_r * 0.65 * (1.0 - progress * 0.4)
        if mid_r > 1.0:
            self.canvas.create_oval(cx - mid_r, cy - mid_r, cx + mid_r, cy + mid_r, fill="#facc15", outline="")
        if progress < 0.45:
            core_r = outer_r * 0.35
            self.canvas.create_oval(cx - core_r, cy - core_r, cx + core_r, cy + core_r, fill="#ffffff", outline="")
        for i in range(12):
            theta = (2.0 * math.pi * i) / 12 + progress * 0.8
            dist = outer_r * (0.5 + progress * 0.85)
            sr = max(1.5, 4.0 * (1.0 - progress))
            sx, sy = cx + math.cos(theta) * dist, cy + math.sin(theta) * dist
            self.canvas.create_oval(
                sx - sr, sy - sr, sx + sr, sy + sr,
                fill="#fde047" if i % 2 == 0 else "#fb923c", outline="",
            )

    def draw_hud(self, lives: int, score: int) -> None:
        """Отрисовать интерфейс игрока: количество жизней и набранные очки."""
        self.canvas.create_text(24, 24, anchor="nw", text=f"Lives: {lives}", fill="#86efac", font=("Consolas", 18, "bold"))
        self.canvas.create_text(WIDTH - 24, 24, anchor="ne", text=f"Score: {score}", fill="#fde047", font=("Consolas", 18, "bold"))

    @staticmethod
    def get_splash_bounds() -> Tuple[float, float, float, float]:
        """Вернуть координаты (x1, y1, x2, y2) прямоугольника заставки."""
        x1 = (WIDTH - SPLASH_WIDTH) / 2.0
        y1 = (HEIGHT - SPLASH_HEIGHT) / 2.0
        return x1, y1, x1 + SPLASH_WIDTH, y1 + SPLASH_HEIGHT

    def draw_splash(self) -> None:
        """Отрисовать центральную заставку с кнопкой запуска игры."""
        x1, y1, x2, y2 = self.get_splash_bounds()
        cx, cy = WIDTH / 2.0, HEIGHT / 2.0
        self.canvas.create_rectangle(x1, y1, x2, y2, fill="#0f172a", outline="#38bdf8", width=3)
        self.canvas.create_rectangle(x1 + 6, y1 + 6, x2 - 6, y2 - 6, outline="#1e3a8a", width=1)
        self.canvas.create_text(cx, cy - 28, text="ASTEROIDS", fill="#f8fafc", font=("Consolas", 34, "bold"))
        self.canvas.create_text(cx, cy + 24, text="CLICK TO START", fill="#38bdf8", font=("Consolas", 16, "bold"))
        self.canvas.create_text(
            cx, cy + 58, text="← → : Поворот   ↑ : Двигатель   Space : Огонь",
            fill="#94a3b8", font=("Consolas", 10),
        )
