"""Главный модуль управления игровым процессом и событиями «Астероидов»."""

import random
import tkinter as tk
from typing import List, Set

from src.config import (
    ASTEROID_SPAWN_INTERVAL_MS,
    FIRE_COOLDOWN,
    FRAME_DELAY_MS,
    HEIGHT,
    INITIAL_LIVES,
    INITIAL_SCORE,
    MAX_ASTEROIDS,
    SAFE_SPAWN_DISTANCE,
    WIDTH,
    WINDOW_TITLE,
)
from src.models.game_objects import (
    Asteroid,
    Explosion,
    Missile,
    Ship,
    toroidal_distance,
)
from src.renderers.renderer import Renderer


class AsteroidsApp:
    """Главный класс приложения, связывающий модель игры, ввод и рендеринг."""

    def __init__(self, root: tk.Tk) -> None:
        """Инициализировать главное окно, холст и начальное состояние игры."""
        self.root = root
        self.root.title(WINDOW_TITLE)
        self.root.resizable(False, False)

        self.canvas = tk.Canvas(
            root, width=WIDTH, height=HEIGHT, highlightthickness=0, bg="#060814"
        )
        self.canvas.pack()

        self.renderer = Renderer(self.canvas)
        self.in_play = False
        self.lives = INITIAL_LIVES
        self.score = INITIAL_SCORE

        self.ship = Ship()
        self.asteroids: List[Asteroid] = []
        self.missiles: List[Missile] = []
        self.explosions: List[Explosion] = []
        self.pressed_keys: Set[str] = set()
        self.fire_timer = 0

        self._bind_events()
        self._schedule_spawner()
        self._game_loop()

    def _bind_events(self) -> None:
        """Привязать обработчики событий мыши и клавиатуры."""
        self.canvas.bind("<Button-1>", self._on_mouse_click)
        self.root.bind("<KeyPress>", self._on_key_press)
        self.root.bind("<KeyRelease>", self._on_key_release)

    def _on_mouse_click(self, event: tk.Event) -> None:
        """Запустить новую игру при щелчке строго по прямоугольнику заставки."""
        if self.in_play:
            return
        x1, y1, x2, y2 = self.renderer.get_splash_bounds()
        if x1 <= event.x <= x2 and y1 <= event.y <= y2:
            self._start_game()

    def _start_game(self) -> None:
        """Сбросить счётчики, очистить поле и начать новую игровую сессию."""
        self.in_play = True
        self.lives = INITIAL_LIVES
        self.score = INITIAL_SCORE
        self.ship.reset()
        self.asteroids.clear()
        self.missiles.clear()
        self.explosions.clear()
        self.fire_timer = 0

    def _on_key_press(self, event: tk.Event) -> None:
        """Обработать нажатие клавиш управления кораблём."""
        key = event.keysym
        self.pressed_keys.add(key)
        if not self.in_play:
            return
        if key == "space" and self.fire_timer <= 0:
            self.missiles.append(self.ship.shoot())
            self.fire_timer = FIRE_COOLDOWN

    def _on_key_release(self, event: tk.Event) -> None:
        """Обработать отпускание клавиш управления."""
        self.pressed_keys.discard(event.keysym)

    def _apply_controls(self) -> None:
        """Применить текущее состояние зажатых клавиш к кораблю."""
        left = "Left" in self.pressed_keys
        right = "Right" in self.pressed_keys
        if left and not right:
            self.ship.angle_vel = -4.5
        elif right and not left:
            self.ship.angle_vel = 4.5
        else:
            self.ship.angle_vel = 0.0

        self.ship.thrust = "Up" in self.pressed_keys
        if self.fire_timer > 0:
            self.fire_timer -= 1

    def _schedule_spawner(self) -> None:
        """Периодически генерировать новые астероиды в случайных точках поля."""
        if self.in_play and len(self.asteroids) < MAX_ASTEROIDS:
            for _ in range(15):
                rx = random.uniform(0.0, WIDTH)
                ry = random.uniform(0.0, HEIGHT)
                if toroidal_distance(rx, ry, self.ship.x, self.ship.y) >= SAFE_SPAWN_DISTANCE:
                    self.asteroids.append(Asteroid(rx, ry))
                    break
        self.root.after(ASTEROID_SPAWN_INTERVAL_MS, self._schedule_spawner)

    def _handle_collisions(self) -> None:
        """Проверить столкновения ракет и корабля с астероидами."""
        # 1. Столкновения ракет и астероидов
        remaining_asteroids: List[Asteroid] = []
        hit_missiles: Set[int] = set()

        for asteroid in self.asteroids:
            destroyed = False
            for idx, missile in enumerate(self.missiles):
                if idx not in hit_missiles and asteroid.collides_with(missile):
                    hit_missiles.add(idx)
                    destroyed = True
                    self.score += 1
                    self.explosions.append(Explosion(asteroid.x, asteroid.y))
                    break
            if not destroyed:
                remaining_asteroids.append(asteroid)

        self.asteroids = remaining_asteroids
        self.missiles = [
            m for idx, m in enumerate(self.missiles) if idx not in hit_missiles
        ]

        # 2. Столкновения корабля и астероидов
        for asteroid in list(self.asteroids):
            if self.ship.collides_with(asteroid):
                self.asteroids.remove(asteroid)
                self.explosions.append(Explosion(asteroid.x, asteroid.y))
                self.lives -= 1
                if self.lives <= 0:
                    self.lives = 0
                    self._end_game()
                    return
                self.ship.reset()
                break

    def _end_game(self) -> None:
        """Завершить игру при потере всех жизней и вернуть заставку."""
        self.in_play = False
        self.ship.thrust = False
        self.asteroids.clear()
        self.missiles.clear()

    def _update_world(self) -> None:
        """Обновить физику всех активных объектов на один игровой кадр."""
        self.renderer.update_background()
        if not self.in_play:
            for exp in self.explosions:
                exp.update()
            self.explosions = [e for e in self.explosions if not e.is_finished]
            return

        self._apply_controls()
        self.ship.update()

        for asteroid in self.asteroids:
            asteroid.update()

        for missile in self.missiles:
            missile.update()
        self.missiles = [m for m in self.missiles if not m.is_expired]

        self._handle_collisions()

        for exp in self.explosions:
            exp.update()
        self.explosions = [e for e in self.explosions if not e.is_finished]

    def _render_world(self) -> None:
        """Отрисовать текущий кадр игры на холсте."""
        self.renderer.draw_background()
        if self.in_play:
            for missile in self.missiles:
                self.renderer.draw_missile(missile)
            for asteroid in self.asteroids:
                self.renderer.draw_asteroid(asteroid)
            self.renderer.draw_ship(self.ship)
        for exp in self.explosions:
            self.renderer.draw_explosion(exp)

        self.renderer.draw_hud(self.lives, self.score)
        if not self.in_play:
            self.renderer.draw_splash()

    def _game_loop(self) -> None:
        """Главный цикл обновления и перерисовки с заданной частотой кадров."""
        self._update_world()
        self._render_world()
        self.root.after(FRAME_DELAY_MS, self._game_loop)
