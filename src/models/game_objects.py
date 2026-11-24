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
    # Перевод градусов в радианы для тригонометрических функций
    rad = math.radians(angle_deg)
    return math.cos(rad), math.sin(rad)


def toroidal_distance(
    pos1: Tuple[float, float], pos2: Tuple[float, float]
) -> float:
    """Вычислить кратчайшее расстояние между двумя точками на торе."""
    # Учитываем склейку противоположных границ экрана по осям X и Y
    dx = abs(pos1[0] - pos2[0])
    dy = abs(pos1[1] - pos2[1])
    dx = min(dx, WIDTH - dx)
    dy = min(dy, HEIGHT - dy)
    return math.hypot(dx, dy)


class SpaceObject:
    """Базовый класс для всех движущихся космических объектов."""

    def __init__(
        self,
        pos: List[float],
        vel: List[float],
        angle: float,
        angle_vel: float,
        radius: float,
    ) -> None:
        """Инициализировать космический объект."""
        self.pos = [float(pos[0]), float(pos[1])]
        self.vel = [float(vel[0]), float(vel[1])]
        self.angle = float(angle)
        self.angle_vel = float(angle_vel)
        self.radius = float(radius)

    def update(self) -> None:
        """Обновить положение и угол объекта с учётом тороидального поля."""
        # Тороидальная геометрия: при выходе за край объект появляется с другой стороны
        self.pos[0] = (self.pos[0] + self.vel[0]) % WIDTH
        self.pos[1] = (self.pos[1] + self.vel[1]) % HEIGHT
        self.angle = (self.angle + self.angle_vel) % 360.0

    def collides_with(self, other: "SpaceObject") -> bool:
        """Проверить пересечение с другим космическим объектом."""
        distance = toroidal_distance(
            (self.pos[0], self.pos[1]), (other.pos[0], other.pos[1])
        )
        return distance <= (self.radius + other.radius)


class Missile(SpaceObject):
    """Класс ракеты, выпускаемой кораблём."""

    def __init__(self, pos: List[float], vel: List[float], angle: float) -> None:
        """Инициализировать ракету с ограниченным временем жизни."""
        super().__init__(pos, vel, angle, 0.0, MISSILE_RADIUS)
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

    def __init__(self, pos: List[float]) -> None:
        """Создать астероид со случайными кинематическими параметрами."""
        radius = random.uniform(ASTEROID_MIN_RADIUS, ASTEROID_MAX_RADIUS)
        speed = random.uniform(ASTEROID_MIN_SPEED, ASTEROID_MAX_SPEED)
        move_angle = random.uniform(0.0, 360.0)
        vx, vy = angle_to_vector(move_angle)
        vel = [vx * speed, vy * speed]

        angle = random.uniform(0.0, 360.0)
        angle_vel = random.uniform(
            -ASTEROID_MAX_ANGULAR_SPEED, ASTEROID_MAX_ANGULAR_SPEED
        )
        super().__init__(pos, vel, angle, angle_vel, radius)

        # Генерация неровного контура астероида в полярных координатах
        self.shape_offsets = self._generate_shape()

    @staticmethod
    def _generate_shape() -> List[Tuple[float, float]]:
        """Сгенерировать вершины многоугольника для визуализации астероида."""
        vertices_count = 12
        points: List[Tuple[float, float]] = []
        for i in range(vertices_count):
            theta = (2.0 * math.pi * i) / vertices_count
            # Случайное отклонение радиуса для создания реалистичных кратеров
            factor = random.uniform(0.76, 1.12)
            points.append((theta, factor))
        return points


class Ship(SpaceObject):
    """Класс космического корабля, управляемого игроком."""

    def __init__(self) -> None:
        """Создать корабль в центре игрового поля в состоянии покоя."""
        super().__init__([WIDTH / 2.0, HEIGHT / 2.0], [0.0, 0.0], -90.0, 0.0, SHIP_RADIUS)
        self.thrust = False

    def reset(self) -> None:
        """Возродить корабль неподвижным в центре экрана."""
        self.pos = [WIDTH / 2.0, HEIGHT / 2.0]
        self.vel = [0.0, 0.0]
        self.angle = -90.0
        self.angle_vel = 0.0
        self.thrust = False

    def rotate_left(self) -> None:
        """Задать угловую скорость вращения против часовой стрелки."""
        self.angle_vel = -SHIP_TURN_SPEED

    def rotate_right(self) -> None:
        """Задать угловую скорость вращения по часовой стрелке."""
        self.angle_vel = SHIP_TURN_SPEED

    def stop_rotation(self) -> None:
        """Остановить вращение корабля."""
        self.angle_vel = 0.0

    def set_thrust(self, active: bool) -> None:
        """Включить или выключить маршевые двигатели корабля."""
        self.thrust = active

    def update(self) -> None:
        """Обновить положение, скорость (с тягой и трением) и угол корабля."""
        if self.thrust:
            fx, fy = angle_to_vector(self.angle)
            self.vel[0] += fx * SHIP_THRUST
            self.vel[1] += fy * SHIP_THRUST

            # Ограничение максимальной скорости корабля
            speed = math.hypot(self.vel[0], self.vel[1])
            if speed > SHIP_MAX_SPEED:
                scale = SHIP_MAX_SPEED / speed
                self.vel[0] *= scale
                self.vel[1] *= scale

        # Сопротивление среды: постепенное замедление при выключенных двигателях
        self.vel[0] *= SHIP_FRICTION
        self.vel[1] *= SHIP_FRICTION

        # Полная остановка при пренебрежимо малой скорости
        if math.hypot(self.vel[0], self.vel[1]) < 0.02:
            self.vel = [0.0, 0.0]

        super().update()

    def shoot(self) -> Missile:
        """Выпустить ракету из носовой части корабля по направлению его ориентации."""
        fx, fy = angle_to_vector(self.angle)
        nose_x = self.pos[0] + fx * self.radius
        nose_y = self.pos[1] + fy * self.radius
        missile_vel = [
            self.vel[0] + fx * MISSILE_SPEED,
            self.vel[1] + fy * MISSILE_SPEED,
        ]
        return Missile([nose_x, nose_y], missile_vel, self.angle)


class Explosion:
    """Класс тайловой (покадровой) анимации взрыва."""

    def __init__(self, pos: List[float]) -> None:
        """Инициализировать анимацию взрыва в заданной точке."""
        self.pos = [float(pos[0]), float(pos[1])]
        self.frame = 0
        self.max_frames = EXPLOSION_FRAMES

    def update(self) -> None:
        """Перейти к следующему кадру тайловой анимации."""
        self.frame += 1

    @property
    def is_finished(self) -> bool:
        """Проверить завершение всех кадров анимации взрыва."""
        return self.frame >= self.max_frames

    @property
    def progress(self) -> float:
        """Вернуть нормализованный прогресс анимации от 0.0 до 1.0."""
        return min(1.0, self.frame / max(1, self.max_frames))

    @property
    def current_radius(self) -> float:
        """Вычислить текущий радиус ударной волны взрыва."""
        return EXPLOSION_MAX_RADIUS * math.sin(self.progress * math.pi * 0.85)
