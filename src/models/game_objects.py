"""Объектная модель и физика сущностей игры «Астероиды»."""

import math
import random
from typing import List, Tuple

from src.config import (
    ASTEROID_MAX_ANGULAR_SPEED,
    ASTEROID_MAX_RADIUS,
    ASTEROID_MAX_SPEED,
    ASTEROID_MIN_RADIUS,
    ASTEROID_MIN_SPEED,
    EXPLOSION_FRAMES,
    EXPLOSION_MAX_RADIUS,
    HEIGHT,
    MISSILE_LIFESPAN,
    MISSILE_RADIUS,
    MISSILE_SPEED,
    SHIP_FRICTION,
    SHIP_MAX_SPEED,
    SHIP_RADIUS,
    SHIP_THRUST,
    SHIP_TURN_SPEED,
    WIDTH,
)


def angle_to_vector(angle_deg: float) -> Tuple[float, float]:
    """Преобразовать угол в градусах в единичный вектор направления."""
    rad = math.radians(angle_deg)
    return math.cos(rad), math.sin(rad)


def toroidal_distance(x1: float, y1: float, x2: float, y2: float) -> float:
    """Вычислить кратчайшее расстояние между двумя точками на торе."""
    dx = min(abs(x1 - x2), WIDTH - abs(x1 - x2))
    dy = min(abs(y1 - y2), HEIGHT - abs(y1 - y2))
    return math.hypot(dx, dy)


class SpaceObject:
    """Базовый класс для всех движущихся космических объектов."""

    def __init__(
        self, x: float, y: float, vx: float, vy: float,
        angle: float, angle_vel: float, radius: float,
    ) -> None:
        """Инициализировать космический объект."""
        self.x = float(x)
        self.y = float(y)
        self.vx = float(vx)
        self.vy = float(vy)
        self.angle = float(angle)
        self.angle_vel = float(angle_vel)
        self.radius = float(radius)

    def update(self) -> None:
        """Обновить положение и угол объекта с учётом тороидального поля."""
        self.x = (self.x + self.vx) % WIDTH
        self.y = (self.y + self.vy) % HEIGHT
        self.angle = (self.angle + self.angle_vel) % 360.0

    def collides_with(self, other: "SpaceObject") -> bool:
        """Проверить пересечение с другим космическим объектом."""
        dist = toroidal_distance(self.x, self.y, other.x, other.y)
        return dist <= (self.radius + other.radius)


class Missile(SpaceObject):
    """Класс ракеты, выпускаемой кораблём."""

    def __init__(self, x: float, y: float, vx: float, vy: float, angle: float) -> None:
        """Инициализировать ракету с ограниченным временем жизни."""
        super().__init__(x, y, vx, vy, angle, 0.0, MISSILE_RADIUS)
        self.age = 0

    def update(self) -> None:
        """Переместить ракету и увеличить счётчик её возраста."""
        super().update()
        self.age += 1

    @property
    def is_expired(self) -> bool:
        """Проверить, истекло ли время жизни ракеты."""
        return self.age >= MISSILE_LIFESPAN


class Asteroid(SpaceObject):
    """Класс астероида со случайной скоростью, вращением и формой."""

    def __init__(self, x: float, y: float) -> None:
        """Создать астероид со случайными кинематическими параметрами."""
        radius = random.uniform(ASTEROID_MIN_RADIUS, ASTEROID_MAX_RADIUS)
        speed = random.uniform(ASTEROID_MIN_SPEED, ASTEROID_MAX_SPEED)
        fx, fy = angle_to_vector(random.uniform(0.0, 360.0))
        angle = random.uniform(0.0, 360.0)
        angle_vel = random.uniform(-ASTEROID_MAX_ANGULAR_SPEED, ASTEROID_MAX_ANGULAR_SPEED)
        super().__init__(x, y, fx * speed, fy * speed, angle, angle_vel, radius)
        self.shape_offsets = [
            ((2.0 * math.pi * i) / 12, random.uniform(0.76, 1.12)) for i in range(12)
        ]


class Ship(SpaceObject):
    """Класс космического корабля, управляемого игроком."""

    def __init__(self) -> None:
        """Создать корабль в центре игрового поля в состоянии покоя."""
        super().__init__(WIDTH / 2.0, HEIGHT / 2.0, 0.0, 0.0, -90.0, 0.0, SHIP_RADIUS)
        self.thrust = False

    def reset(self) -> None:
        """Возродить корабль неподвижным в центре экрана."""
        self.x, self.y, self.vx, self.vy = WIDTH / 2.0, HEIGHT / 2.0, 0.0, 0.0
        self.angle, self.angle_vel, self.thrust = -90.0, 0.0, False

    def update(self) -> None:
        """Обновить положение, скорость (с тягой и трением) и угол корабля."""
        if self.thrust:
            fx, fy = angle_to_vector(self.angle)
            self.vx += fx * SHIP_THRUST
            self.vy += fy * SHIP_THRUST
            speed = math.hypot(self.vx, self.vy)
            if speed > SHIP_MAX_SPEED:
                self.vx *= SHIP_MAX_SPEED / speed
                self.vy *= SHIP_MAX_SPEED / speed

        self.vx *= SHIP_FRICTION
        self.vy *= SHIP_FRICTION
        if math.hypot(self.vx, self.vy) < 0.02:
            self.vx, self.vy = 0.0, 0.0
        super().update()

    def shoot(self) -> Missile:
        """Выпустить ракету из носовой части корабля по направлению его ориентации."""
        fx, fy = angle_to_vector(self.angle)
        return Missile(
            self.x + fx * self.radius,
            self.y + fy * self.radius,
            self.vx + fx * MISSILE_SPEED,
            self.vy + fy * MISSILE_SPEED,
            self.angle,
        )


class Explosion:
    """Класс тайловой (покадровой) анимации взрыва."""

    def __init__(self, x: float, y: float) -> None:
        """Инициализировать анимацию взрыва в заданной точке."""
        self.x, self.y, self.frame = float(x), float(y), 0

    def update(self) -> None:
        """Перейти к следующему кадру тайловой анимации."""
        self.frame += 1

    @property
    def is_finished(self) -> bool:
        """Проверить завершение всех кадров анимации взрыва."""
        return self.frame >= EXPLOSION_FRAMES

    @property
    def progress(self) -> float:
        """Вернуть нормализованный прогресс анимации от 0.0 до 1.0."""
        return min(1.0, self.frame / max(1, EXPLOSION_FRAMES))

    @property
    def current_radius(self) -> float:
        """Вычислить текущий радиус ударной волны взрыва."""
        return EXPLOSION_MAX_RADIUS * math.sin(self.progress * math.pi * 0.85)
