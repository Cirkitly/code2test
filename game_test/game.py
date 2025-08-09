import pygame
import math
import random
import json
import os
from enum import Enum
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

# Initialize Pygame
pygame.init()

# Constants
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800
FPS = 60
GRID_SIZE = 40
TILE_SIZE = 20

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
PURPLE = (128, 0, 128)
ORANGE = (255, 165, 0)
CYAN = (0, 255, 255)
GRAY = (128, 128, 128)
LIGHT_GRAY = (192, 192, 192)
DARK_GRAY = (64, 64, 64)
BROWN = (139, 69, 19)
LIME = (0, 255, 0)
PINK = (255, 192, 203)
GOLD = (255, 215, 0)

# Game states
class GameStateEnum(Enum):
    MENU = "menu"
    PLAYING = "playing"
    PAUSED = "paused"
    GAME_OVER = "game_over"
    VICTORY = "victory"
    SHOP = "shop"
    SETTINGS = "settings"

# Tower types
class TowerType(Enum):
    BASIC = "basic"
    SNIPER = "sniper"
    CANNON = "cannon"
    FREEZE = "freeze"
    POISON = "poison"
    LASER = "laser"
    MISSILE = "missile"
    ELECTRIC = "electric"

# Enemy types
class EnemyType(Enum):
    BASIC = "basic"
    FAST = "fast"
    HEAVY = "heavy"
    FLYING = "flying"
    BOSS = "boss"
    STEALTH = "stealth"
    REGENERATING = "regenerating"
    IMMUNE = "immune"

# Projectile types
class ProjectileType(Enum):
    BULLET = "bullet"
    CANNONBALL = "cannonball"
    LASER = "laser"
    MISSILE = "missile"
    ELECTRIC = "electric"
    FREEZE = "freeze"
    POISON = "poison"

@dataclass
class Vector2:
    x: float
    y: float
    
    def __add__(self, other):
        return Vector2(self.x + other.x, self.y + other.y)
    
    def __sub__(self, other):
        return Vector2(self.x - other.x, self.y - other.y)
    
    def __mul__(self, scalar):
        return Vector2(self.x * scalar, self.y * scalar)
    
    def magnitude(self):
        return math.sqrt(self.x ** 2 + self.y ** 2)
    
    def normalize(self):
        mag = self.magnitude()
        if mag == 0:
            return Vector2(0, 0)
        return Vector2(self.x / mag, self.y / mag)
    
    def distance_to(self, other):
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)

class GameObject(ABC):
    """Base class for all game objects"""
    def __init__(self, x: float, y: float):
        self.position = Vector2(x, y)
        self.active = True
    
    @abstractmethod
    def update(self, dt: float):
        pass
    
    @abstractmethod
    def draw(self, screen: pygame.Surface):
        pass

class Particle(GameObject):
    """Visual effects particle system"""
    def __init__(self, x: float, y: float, velocity: Vector2, color: Tuple[int, int, int], 
                 life_time: float, size: float = 3):
        super().__init__(x, y)
        self.velocity = velocity
        self.color = color
        self.life_time = life_time
        self.max_life_time = life_time
        self.size = size
        self.gravity = Vector2(0, 50)
    
    def update(self, dt: float):
        self.position = self.position + self.velocity * dt
        self.velocity = self.velocity + self.gravity * dt
        self.life_time -= dt
        if self.life_time <= 0:
            self.active = False
    
    def draw(self, screen: pygame.Surface):
        if self.active:
            alpha = self.life_time / self.max_life_time
            current_size = self.size * alpha
            if current_size > 1:
                pygame.draw.circle(screen, self.color, 
                                 (int(self.position.x), int(self.position.y)), 
                                 int(current_size))

class ParticleSystem:
    """Manages particle effects"""
    def __init__(self):
        self.particles: List[Particle] = []
    
    def add_explosion(self, x: float, y: float, color: Tuple[int, int, int], count: int = 10):
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(50, 150)
            velocity = Vector2(math.cos(angle) * speed, math.sin(angle) * speed)
            life_time = random.uniform(0.5, 1.5)
            size = random.uniform(2, 6)
            self.particles.append(Particle(x, y, velocity, color, life_time, size))
    
    def add_trail(self, x: float, y: float, color: Tuple[int, int, int]):
        velocity = Vector2(random.uniform(-20, 20), random.uniform(-20, 20))
        life_time = random.uniform(0.2, 0.5)
        self.particles.append(Particle(x, y, velocity, color, life_time, 2))
    
    def update(self, dt: float):
        self.particles = [p for p in self.particles if p.active]
        for particle in self.particles:
            particle.update(dt)
    
    def draw(self, screen: pygame.Surface):
        for particle in self.particles:
            particle.draw(screen)

class StatusEffect:
    """Base class for status effects on enemies"""
    def __init__(self, duration: float, effect_type: str):
        self.duration = duration
        self.max_duration = duration
        self.effect_type = effect_type
        self.active = True
    
    def update(self, dt: float, enemy):
        self.duration -= dt
        if self.duration <= 0:
            self.active = False
        else:
            self.apply_effect(enemy)
    
    def apply_effect(self, enemy):
        pass

class SlowEffect(StatusEffect):
    def __init__(self, duration: float, slow_factor: float):
        super().__init__(duration, "slow")
        self.slow_factor = slow_factor
    
    def apply_effect(self, enemy):
        enemy.speed_multiplier = min(enemy.speed_multiplier, self.slow_factor)

class PoisonEffect(StatusEffect):
    def __init__(self, duration: float, damage_per_second: float):
        super().__init__(duration, "poison")
        self.damage_per_second = damage_per_second
        self.damage_timer = 0
    
    def apply_effect(self, enemy):
        self.damage_timer += 1/60  # Assuming 60 FPS
        if self.damage_timer >= 1.0:
            enemy.take_damage(self.damage_per_second)
            self.damage_timer = 0

class Projectile(GameObject):
    """Base class for all projectiles"""
    def __init__(self, x: float, y: float, target_pos: Vector2, damage: float, 
                 speed: float, projectile_type: ProjectileType):
        super().__init__(x, y)
        self.target_pos = target_pos
        self.damage = damage
        self.speed = speed
        self.type = projectile_type
        
        # Calculate direction
        direction = target_pos - self.position
        self.velocity = direction.normalize() * speed
        
        # Visual properties
        self.size = 4
        self.color = YELLOW
        self.trail_particles = []
    
    def update(self, dt: float):
        self.position = self.position + self.velocity * dt
        
        # Check if reached target area
        if self.position.distance_to(self.target_pos) < 5:
            self.active = False
        
        # Remove if off screen
        if (self.position.x < 0 or self.position.x > SCREEN_WIDTH or 
            self.position.y < 0 or self.position.y > SCREEN_HEIGHT):
            self.active = False
    
    def draw(self, screen: pygame.Surface):
        if self.active:
            pygame.draw.circle(screen, self.color, 
                             (int(self.position.x), int(self.position.y)), self.size)

class Bullet(Projectile):
    def __init__(self, x: float, y: float, target_pos: Vector2, damage: float):
        super().__init__(x, y, target_pos, damage, 400, ProjectileType.BULLET)
        self.color = YELLOW
        self.size = 3

class Cannonball(Projectile):
    def __init__(self, x: float, y: float, target_pos: Vector2, damage: float):
        super().__init__(x, y, target_pos, damage, 250, ProjectileType.CANNONBALL)
        self.color = DARK_GRAY
        self.size = 6
        self.explosion_radius = 50

class LaserBeam(Projectile):
    def __init__(self, x: float, y: float, target_pos: Vector2, damage: float):
        super().__init__(x, y, target_pos, damage, 800, ProjectileType.LASER)
        self.color = RED
        self.size = 2
    
    def draw(self, screen: pygame.Surface):
        if self.active:
            pygame.draw.line(screen, self.color, 
                           (int(self.position.x), int(self.position.y)),
                           (int(self.target_pos.x), int(self.target_pos.y)), 3)

class Missile(Projectile):
    def __init__(self, x: float, y: float, target, damage: float):
        super().__init__(x, y, target.position, damage, 300, ProjectileType.MISSILE)
        self.target = target
        self.color = ORANGE
        self.size = 5
        self.homing_strength = 2.0
    
    def update(self, dt: float):
        if self.target and self.target.active:
            # Update target position for homing
            direction_to_target = self.target.position - self.position
            if direction_to_target.magnitude() > 0:
                desired_velocity = direction_to_target.normalize() * self.speed
                steering = desired_velocity - self.velocity
                self.velocity = self.velocity + steering * self.homing_strength * dt
        
        super().update(dt)

class Enemy(GameObject):
    """Base enemy class"""
    def __init__(self, x: float, y: float, enemy_type: EnemyType, path: List[Vector2]):
        super().__init__(x, y)
        self.type = enemy_type
        self.path = path
        self.path_index = 0
        self.max_health = 100
        self.health = self.max_health
        self.speed = 50
        self.speed_multiplier = 1.0
        self.reward = 10
        self.size = 15
        self.color = RED
        self.status_effects: List[StatusEffect] = []
        self.armor = 0
        self.magic_resistance = 0
        self.regeneration_rate = 0
        self.stealth_time = 0
        self.is_flying = False
    
    def take_damage(self, damage: float, damage_type: str = "physical"):
        if damage_type == "physical":
            actual_damage = max(1, damage - self.armor)
        elif damage_type == "magic":
            actual_damage = damage * (1 - self.magic_resistance)
        else:
            actual_damage = damage
        
        self.health -= actual_damage
        if self.health <= 0:
            self.active = False
        return actual_damage
    
    def add_status_effect(self, effect: StatusEffect):
        # Remove existing effects of the same type
        self.status_effects = [e for e in self.status_effects 
                              if e.effect_type != effect.effect_type]
        self.status_effects.append(effect)
    
    def update(self, dt: float):
        # Reset speed multiplier
        self.speed_multiplier = 1.0
        
        # Update status effects
        for effect in self.status_effects[:]:
            effect.update(dt, self)
            if not effect.active:
                self.status_effects.remove(effect)
        
        # Regeneration
        if self.regeneration_rate > 0:
            self.health = min(self.max_health, self.health + self.regeneration_rate * dt)
        
        # Move along path
        if self.path_index < len(self.path):
            target = self.path[self.path_index]
            direction = target - self.position
            distance = direction.magnitude()
            
            if distance < 5:
                self.path_index += 1
                if self.path_index >= len(self.path):
                    self.active = False  # Reached end
            else:
                move_vector = direction.normalize() * self.speed * self.speed_multiplier * dt
                self.position = self.position + move_vector
    
    def draw(self, screen: pygame.Surface):
        if self.active:
            # Main enemy body
            pygame.draw.circle(screen, self.color, 
                             (int(self.position.x), int(self.position.y)), self.size)
            
            # Health bar
            bar_width = self.size * 2
            bar_height = 4
            health_ratio = self.health / self.max_health
            
            # Background
            pygame.draw.rect(screen, RED, 
                           (self.position.x - bar_width//2, 
                            self.position.y - self.size - 10, 
                            bar_width, bar_height))
            
            # Health
            pygame.draw.rect(screen, GREEN, 
                           (self.position.x - bar_width//2, 
                            self.position.y - self.size - 10, 
                            bar_width * health_ratio, bar_height))
            
            # Status effect indicators
            y_offset = self.size + 15
            for i, effect in enumerate(self.status_effects):
                if effect.effect_type == "slow":
                    pygame.draw.circle(screen, BLUE, 
                                     (int(self.position.x - 10 + i * 8), 
                                      int(self.position.y + y_offset)), 3)
                elif effect.effect_type == "poison":
                    pygame.draw.circle(screen, GREEN, 
                                     (int(self.position.x - 10 + i * 8), 
                                      int(self.position.y + y_offset)), 3)

class BasicEnemy(Enemy):
    def __init__(self, x: float, y: float, path: List[Vector2]):
        super().__init__(x, y, EnemyType.BASIC, path)
        self.max_health = 100
        self.health = self.max_health
        self.speed = 50
        self.reward = 10
        self.color = RED

class FastEnemy(Enemy):
    def __init__(self, x: float, y: float, path: List[Vector2]):
        super().__init__(x, y, EnemyType.FAST, path)
        self.max_health = 50
        self.health = self.max_health
        self.speed = 100
        self.reward = 15
        self.color = CYAN
        self.size = 12

class HeavyEnemy(Enemy):
    def __init__(self, x: float, y: float, path: List[Vector2]):
        super().__init__(x, y, EnemyType.HEAVY, path)
        self.max_health = 300
        self.health = self.max_health
        self.speed = 25
        self.armor = 5
        self.reward = 25
        self.color = GRAY
        self.size = 20

class FlyingEnemy(Enemy):
    def __init__(self, x: float, y: float, path: List[Vector2]):
        super().__init__(x, y, EnemyType.FLYING, path)
        self.max_health = 75
        self.health = self.max_health
        self.speed = 75
        self.reward = 20
        self.color = PURPLE
        self.is_flying = True
        self.size = 13

class BossEnemy(Enemy):
    def __init__(self, x: float, y: float, path: List[Vector2]):
        super().__init__(x, y, EnemyType.BOSS, path)
        self.max_health = 1000
        self.health = self.max_health
        self.speed = 30
        self.armor = 10
        self.magic_resistance = 0.3
        self.regeneration_rate = 5
        self.reward = 100
        self.color = DARK_GRAY
        self.size = 30

class Tower(GameObject):
    """Base tower class"""
    def __init__(self, x: float, y: float, tower_type: TowerType):
        super().__init__(x, y)
        self.type = tower_type
        self.damage = 25
        self.range = 100
        self.fire_rate = 1.0  # shots per second
        self.last_shot_time = 0
        self.cost = 50
        self.level = 1
        self.upgrade_cost = 25
        self.target_priority = "first"  # "first", "last", "strongest", "weakest"
        self.can_target_air = True
        self.size = 15
        self.color = BLUE
        self.projectiles: List[Projectile] = []
    
    def can_shoot(self) -> bool:
        current_time = pygame.time.get_ticks() / 1000.0
        return current_time - self.last_shot_time >= (1.0 / self.fire_rate)
    
    def find_target(self, enemies: List[Enemy]) -> Optional[Enemy]:
        targets_in_range = []
        for enemy in enemies:
            if enemy.active and self.position.distance_to(enemy.position) <= self.range:
                if self.can_target_air or not enemy.is_flying:
                    targets_in_range.append(enemy)
        
        if not targets_in_range:
            return None
        
        if self.target_priority == "first":
            return max(targets_in_range, key=lambda e: e.path_index)
        elif self.target_priority == "last":
            return min(targets_in_range, key=lambda e: e.path_index)
        elif self.target_priority == "strongest":
            return max(targets_in_range, key=lambda e: e.health)
        elif self.target_priority == "weakest":
            return min(targets_in_range, key=lambda e: e.health)
        else:
            return targets_in_range[0]
    
    def shoot(self, target: Enemy, particle_system: ParticleSystem):
        if self.can_shoot():
            self.create_projectile(target)
            self.last_shot_time = pygame.time.get_ticks() / 1000.0
    
    def create_projectile(self, target: Enemy):
        projectile = Bullet(self.position.x, self.position.y, target.position, self.damage)
        self.projectiles.append(projectile)
    
    def upgrade(self):
        if self.level < 5:  # Max level 5
            self.level += 1
            self.damage *= 1.3
            self.range *= 1.1
            self.fire_rate *= 1.2
            self.upgrade_cost = int(self.upgrade_cost * 1.5)
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "level": self.level,
            "damage": int(self.damage),
            "range": int(self.range),
            "fire_rate": round(self.fire_rate, 1),
            "upgrade_cost": self.upgrade_cost
        }
    
    def update(self, dt: float, enemies: List[Enemy], particle_system: ParticleSystem):
        # Update projectiles
        for projectile in self.projectiles[:]:
            projectile.update(dt)
            if not projectile.active:
                self.projectiles.remove(projectile)
                # Check for hits
                for enemy in enemies:
                    if (enemy.active and 
                        enemy.position.distance_to(projectile.position) < enemy.size):
                        damage_dealt = enemy.take_damage(projectile.damage)
                        particle_system.add_explosion(enemy.position.x, enemy.position.y, 
                                                    YELLOW, 5)
                        break
        
        # Find and shoot at targets
        target = self.find_target(enemies)
        if target:
            self.shoot(target, particle_system)
    
    def draw(self, screen: pygame.Surface):
        if self.active:
            # Tower body
            pygame.draw.circle(screen, self.color, 
                             (int(self.position.x), int(self.position.y)), self.size)
            
            # Level indicator
            font = pygame.font.Font(None, 16)
            level_text = font.render(str(self.level), True, WHITE)
            screen.blit(level_text, (self.position.x - 5, self.position.y - 5))
        
        # Draw projectiles
        for projectile in self.projectiles:
            projectile.draw(screen)
    
    def draw_range(self, screen: pygame.Surface):
        """Draw tower range circle"""
        pygame.draw.circle(screen, (255, 255, 255, 50), 
                         (int(self.position.x), int(self.position.y)), 
                         int(self.range), 2)

class BasicTower(Tower):
    def __init__(self, x: float, y: float):
        super().__init__(x, y, TowerType.BASIC)
        self.damage = 25
        self.range = 100
        self.fire_rate = 2.0
        self.cost = 50
        self.color = BLUE

class SniperTower(Tower):
    def __init__(self, x: float, y: float):
        super().__init__(x, y, TowerType.SNIPER)
        self.damage = 75
        self.range = 200
        self.fire_rate = 0.5
        self.cost = 100
        self.color = GREEN
    
    def create_projectile(self, target: Enemy):
        projectile = Bullet(self.position.x, self.position.y, target.position, self.damage)
        projectile.speed = 600
        projectile.color = GREEN
        self.projectiles.append(projectile)

class CannonTower(Tower):
    def __init__(self, x: float, y: float):
        super().__init__(x, y, TowerType.CANNON)
        self.damage = 100
        self.range = 80
        self.fire_rate = 0.8
        self.cost = 150
        self.color = DARK_GRAY
    
    def create_projectile(self, target: Enemy):
        projectile = Cannonball(self.position.x, self.position.y, target.position, self.damage)
        self.projectiles.append(projectile)

class FreezeTower(Tower):
    def __init__(self, x: float, y: float):
        super().__init__(x, y, TowerType.FREEZE)
        self.damage = 15
        self.range = 90
        self.fire_rate = 1.5
        self.cost = 120
        self.color = CYAN
        self.slow_factor = 0.5
        self.slow_duration = 2.0
    
    def create_projectile(self, target: Enemy):
        # Create freeze effect
        target.add_status_effect(SlowEffect(self.slow_duration, self.slow_factor))
        projectile = Bullet(self.position.x, self.position.y, target.position, self.damage)
        projectile.color = CYAN
        self.projectiles.append(projectile)

class PoisonTower(Tower):
    def __init__(self, x: float, y: float):
        super().__init__(x, y, TowerType.POISON)
        self.damage = 20
        self.range = 85
        self.fire_rate = 1.2
        self.cost = 110
        self.color = LIME
        self.poison_dps = 10
        self.poison_duration = 3.0
    
    def create_projectile(self, target: Enemy):
        # Create poison effect
        target.add_status_effect(PoisonEffect(self.poison_duration, self.poison_dps))
        projectile = Bullet(self.position.x, self.position.y, target.position, self.damage)
        projectile.color = LIME
        self.projectiles.append(projectile)

class LaserTower(Tower):
    def __init__(self, x: float, y: float):
        super().__init__(x, y, TowerType.LASER)
        self.damage = 50
        self.range = 120
        self.fire_rate = 3.0
        self.cost = 200
        self.color = RED
    
    def create_projectile(self, target: Enemy):
        projectile = LaserBeam(self.position.x, self.position.y, target.position, self.damage)
        self.projectiles.append(projectile)

class MissileTower(Tower):
    def __init__(self, x: float, y: float):
        super().__init__(x, y, TowerType.MISSILE)
        self.damage = 80
        self.range = 150
        self.fire_rate = 1.0
        self.cost = 250
        self.color = ORANGE
    
    def create_projectile(self, target: Enemy):
        projectile = Missile(self.position.x, self.position.y, target, self.damage)
        self.projectiles.append(projectile)

class Wave:
    """Manages enemy waves"""
    def __init__(self, wave_number: int):
        self.wave_number = wave_number
        self.enemies_to_spawn: List[Tuple[EnemyType, float]] = []
        self.spawn_timer = 0
        self.current_enemy_index = 0
        self.completed = False
        self.started = False
        
        self.generate_wave()
    
    def generate_wave(self):
        """Generate enemies for this wave"""
        base_enemies = 5 + self.wave_number * 2
        
        # Basic composition
        for i in range(base_enemies):
            spawn_time = i * 1.0  # 1 second between spawns
            if i % 5 == 0 and self.wave_number > 2:  # Heavy every 5th enemy after wave 2
                self.enemies_to_spawn.append((EnemyType.HEAVY, spawn_time))
            elif i % 3 == 0 and self.wave_number > 1:  # Fast every 3rd enemy after wave 1
                self.enemies_to_spawn.append((EnemyType.FAST, spawn_time))
            elif i % 4 == 0 and self.wave_number > 3:  # Flying every 4th enemy after wave 3
                self.enemies_to_spawn.append((EnemyType.FLYING, spawn_time))
            else:
                self.enemies_to_spawn.append((EnemyType.BASIC, spawn_time))
        
        # Boss every 5 waves
        if self.wave_number % 5 == 0:
            boss_spawn_time = len(self.enemies_to_spawn) * 1.0 + 2.0
            self.enemies_to_spawn.append((EnemyType.BOSS, boss_spawn_time))
    
    def update(self, dt: float, enemies: List[Enemy], path: List[Vector2]) -> bool:
        """Update wave spawning, returns True if wave is complete"""
        if not self.started:
            return False
        
        self.spawn_timer += dt
        
        # Spawn enemies
        while (self.current_enemy_index < len(self.enemies_to_spawn) and 
               self.spawn_timer >= self.enemies_to_spawn[self.current_enemy_index][1]):
            
            enemy_type = self.enemies_to_spawn[self.current_enemy_index][0]
            spawn_pos = path[0] if path else Vector2(0, 0)
            
            # Create enemy based on type
            if enemy_type == EnemyType.BASIC:
                enemy = BasicEnemy(spawn_pos.x, spawn_pos.y, path)
            elif enemy_type == EnemyType.FAST:
                enemy = FastEnemy(spawn_pos.x, spawn_pos.y, path)
            elif enemy_type == EnemyType.HEAVY:
                enemy = HeavyEnemy(spawn_pos.x, spawn_pos.y, path)
            elif enemy_type == EnemyType.FLYING:
                enemy = FlyingEnemy(spawn_pos.x, spawn_pos.y, path)
            elif enemy_type == EnemyType.BOSS:
                enemy = BossEnemy(spawn_pos.x, spawn_pos.y, path)
            else:
                enemy = BasicEnemy(spawn_pos.x, spawn_pos.y, path)
            
            enemies.append(enemy)
            self.current_enemy_index += 1
        
        # Check if wave is complete
        if (self.current_enemy_index >= len(self.enemies_to_spawn) and 
            not any(e.active for e in enemies)):
            self.completed = True
        
        return self.completed
    
    def start(self):
        self.started = True

class GameMap:
    """Manages the game map and pathfinding"""
    def __init__(self):
        self.width = SCREEN_WIDTH // TILE_SIZE
        self.height = SCREEN_HEIGHT // TILE_SIZE
        self.tiles = [[0 for _ in range(self.width)] for _ in range(self.height)]
        self.path = self.generate_path()
    
    def generate_path(self) -> List[Vector2]:
        """Generate a simple path from left to right with some turns"""
        path = []
        
        # Start from left side
        start_y = SCREEN_HEIGHT // 2
        path.append(Vector2(0, start_y))
        
        # Add some waypoints
        waypoints = [
            Vector2(200, start_y),
            Vector2(200, start_y - 100),
            Vector2(400, start_y - 100),
            Vector2(400, start_y + 100),
            Vector2(600, start_y + 100),
            Vector2(600, start_y - 50),
            Vector2(800, start_y - 50),
            Vector2(800, start_y + 50),
            Vector2(SCREEN_WIDTH, start_y + 50)
        ]
        
        path.extend(waypoints)
        return path
    
    def can_place_tower(self, x: int, y: int, tower_size: int = 20) -> bool:
        """Check if a tower can be placed at the given position"""
        # Check if position is too close to path
        tower_pos = Vector2(x, y)
        for path_point in self.path:
            if tower_pos.distance_to(path_point) < tower_size + 10:
                return False
        
        # Check bounds
        if (x < tower_size or x > SCREEN_WIDTH - tower_size or
            y < tower_size or y > SCREEN_HEIGHT - tower_size):
            return False
        
        return True
    
    def draw(self, screen: pygame.Surface):
        """Draw the map including the path"""
        # Draw background
        screen.fill((34, 139, 34))  # Forest green
        
        # Draw path
        if len(self.path) > 1:
            pygame.draw.lines(screen, BROWN, False, 
                            [(int(p.x), int(p.y)) for p in self.path], 20)
            
            # Draw path markers
            for i, point in enumerate(self.path):
                if i == 0:  # Start
                    pygame.draw.circle(screen, GREEN, (int(point.x), int(point.y)), 15)
                elif i == len(self.path) - 1:  # End
                    pygame.draw.circle(screen, RED, (int(point.x), int(point.y)), 15)

class UI:
    """User interface management"""
    def __init__(self):
        self.font_small = pygame.font.Font(None, 20)
        self.font_medium = pygame.font.Font(None, 32)
        self.font_large = pygame.font.Font(None, 48)
        
        self.selected_tower = None
        self.selected_tower_type = TowerType.BASIC
        self.tower_menu_visible = False
        
        # UI panels
        self.side_panel_width = 200
        self.bottom_panel_height = 100
        
        # Button definitions
        self.buttons = {
            'basic_tower': pygame.Rect(SCREEN_WIDTH - 190, 10, 80, 40),
            'sniper_tower': pygame.Rect(SCREEN_WIDTH - 100, 10, 80, 40),
            'cannon_tower': pygame.Rect(SCREEN_WIDTH - 190, 60, 80, 40),
            'freeze_tower': pygame.Rect(SCREEN_WIDTH - 100, 60, 80, 40),
            'poison_tower': pygame.Rect(SCREEN_WIDTH - 190, 110, 80, 40),
            'laser_tower': pygame.Rect(SCREEN_WIDTH - 100, 110, 80, 40),
            'missile_tower': pygame.Rect(SCREEN_WIDTH - 190, 160, 80, 40),
            'next_wave': pygame.Rect(SCREEN_WIDTH - 190, 220, 180, 40),
            'upgrade_tower': pygame.Rect(SCREEN_WIDTH - 190, 270, 80, 40),
            'sell_tower': pygame.Rect(SCREEN_WIDTH - 100, 270, 80, 40),
        }
        
        self.tower_costs = {
            TowerType.BASIC: 50,
            TowerType.SNIPER: 100,
            TowerType.CANNON: 150,
            TowerType.FREEZE: 120,
            TowerType.POISON: 110,
            TowerType.LASER: 200,
            TowerType.MISSILE: 250,
        }
    
    def handle_click(self, pos: Tuple[int, int], game_state) -> Optional[str]:
        """Handle UI clicks and return action"""
        x, y = pos
        
        # Check button clicks
        for button_name, button_rect in self.buttons.items():
            if button_rect.collidepoint(x, y):
                return button_name
        
        # Check tower placement/selection
        if x < SCREEN_WIDTH - self.side_panel_width:
            return "game_area_click"
        
        return None
    
    def draw(self, screen: pygame.Surface, game_state):
        """Draw the UI"""
        # Side panel background
        panel_rect = pygame.Rect(SCREEN_WIDTH - self.side_panel_width, 0, 
                               self.side_panel_width, SCREEN_HEIGHT)
        pygame.draw.rect(screen, DARK_GRAY, panel_rect)
        pygame.draw.rect(screen, WHITE, panel_rect, 2)
        
        # Title
        title_text = self.font_medium.render("Tower Defense", True, WHITE)
        screen.blit(title_text, (SCREEN_WIDTH - 190, 320))
        
        # Game stats
        stats_y = 350
        money_text = self.font_small.render(f"Money: ${game_state.money}", True, WHITE)
        screen.blit(money_text, (SCREEN_WIDTH - 190, stats_y))
        
        lives_text = self.font_small.render(f"Lives: {game_state.lives}", True, WHITE)
        screen.blit(lives_text, (SCREEN_WIDTH - 190, stats_y + 25))
        
        wave_text = self.font_small.render(f"Wave: {game_state.current_wave}", True, WHITE)
        screen.blit(wave_text, (SCREEN_WIDTH - 190, stats_y + 50))
        
        score_text = self.font_small.render(f"Score: {game_state.score}", True, WHITE)
        screen.blit(score_text, (SCREEN_WIDTH - 190, stats_y + 75))
        
        # Tower buttons
        self.draw_tower_button(screen, "Basic", TowerType.BASIC, self.buttons['basic_tower'])
        self.draw_tower_button(screen, "Sniper", TowerType.SNIPER, self.buttons['sniper_tower'])
        self.draw_tower_button(screen, "Cannon", TowerType.CANNON, self.buttons['cannon_tower'])
        self.draw_tower_button(screen, "Freeze", TowerType.FREEZE, self.buttons['freeze_tower'])
        self.draw_tower_button(screen, "Poison", TowerType.POISON, self.buttons['poison_tower'])
        self.draw_tower_button(screen, "Laser", TowerType.LASER, self.buttons['laser_tower'])
        self.draw_tower_button(screen, "Missile", TowerType.MISSILE, self.buttons['missile_tower'])
        
        # Wave control
        next_wave_color = GREEN if game_state.can_start_next_wave() else GRAY
        pygame.draw.rect(screen, next_wave_color, self.buttons['next_wave'])
        pygame.draw.rect(screen, WHITE, self.buttons['next_wave'], 2)
        
        next_wave_text = self.font_small.render("Next Wave", True, WHITE)
        screen.blit(next_wave_text, (SCREEN_WIDTH - 180, 230))
        
        # Tower management buttons (if tower selected)
        if self.selected_tower:
            pygame.draw.rect(screen, BLUE, self.buttons['upgrade_tower'])
            pygame.draw.rect(screen, WHITE, self.buttons['upgrade_tower'], 2)
            upgrade_text = self.font_small.render("Upgrade", True, WHITE)
            screen.blit(upgrade_text, (SCREEN_WIDTH - 185, 280))
            
            pygame.draw.rect(screen, RED, self.buttons['sell_tower'])
            pygame.draw.rect(screen, WHITE, self.buttons['sell_tower'], 2)
            sell_text = self.font_small.render("Sell", True, WHITE)
            screen.blit(sell_text, (SCREEN_WIDTH - 90, 280))
            
            # Tower stats
            stats = self.selected_tower.get_stats()
            stats_y = 450
            for i, (key, value) in enumerate(stats.items()):
                stat_text = self.font_small.render(f"{key}: {value}", True, WHITE)
                screen.blit(stat_text, (SCREEN_WIDTH - 190, stats_y + i * 20))
    
    def draw_tower_button(self, screen: pygame.Surface, name: str, tower_type: TowerType, rect: pygame.Rect):
        """Draw a tower selection button"""
        cost = self.tower_costs[tower_type]
        color = BLUE if tower_type == self.selected_tower_type else GRAY
        
        pygame.draw.rect(screen, color, rect)
        pygame.draw.rect(screen, WHITE, rect, 2)
        
        # Tower name
        name_text = self.font_small.render(name, True, WHITE)
        screen.blit(name_text, (rect.x + 5, rect.y + 5))
        
        # Cost
        cost_text = self.font_small.render(f"${cost}", True, WHITE)
        screen.blit(cost_text, (rect.x + 5, rect.y + 20))

class GameState:
    """Manages the overall game state"""
    def __init__(self):
        self.state = GameStateEnum.MENU
        self.money = 200
        self.lives = 20
        self.score = 0
        self.current_wave = 1
        
        # Game objects
        self.towers: List[Tower] = []
        self.enemies: List[Enemy] = []
        self.waves: List[Wave] = []
        self.current_wave_obj: Optional[Wave] = None
        
        # Systems
        self.particle_system = ParticleSystem()
        self.game_map = GameMap()
        self.ui = UI()
        
        # Game settings
        self.wave_delay = 3.0  # Seconds between waves
        self.wave_timer = 0
        self.game_speed = 1.0
        self.paused = False
        
        # Initialize first wave
        self.prepare_next_wave()
    
    def prepare_next_wave(self):
        """Prepare the next wave"""
        self.current_wave_obj = Wave(self.current_wave)
        self.waves.append(self.current_wave_obj)
    
    def can_start_next_wave(self) -> bool:
        """Check if next wave can be started"""
        return (self.current_wave_obj is not None and 
                not self.current_wave_obj.started and
                not any(e.active for e in self.enemies))
    
    def start_next_wave(self):
        """Start the next wave"""
        if self.can_start_next_wave():
            self.current_wave_obj.start()
    
    def add_money(self, amount: int):
        """Add money to player"""
        self.money += amount
        self.score += amount
    
    def spend_money(self, amount: int) -> bool:
        """Try to spend money, returns True if successful"""
        if self.money >= amount:
            self.money -= amount
            return True
        return False
    
    def lose_life(self):
        """Player loses a life"""
        self.lives -= 1
        if self.lives <= 0:
            self.state = GameStateEnum.GAME_OVER
    
    def place_tower(self, x: int, y: int, tower_type: TowerType) -> bool:
        """Try to place a tower at the given position"""
        if not self.game_map.can_place_tower(x, y):
            return False
        
        cost = self.ui.tower_costs[tower_type]
        if not self.spend_money(cost):
            return False
        
        # Check for existing tower at this position
        for tower in self.towers:
            if tower.position.distance_to(Vector2(x, y)) < 30:
                return False
        
        # Create tower based on type
        if tower_type == TowerType.BASIC:
            tower = BasicTower(x, y)
        elif tower_type == TowerType.SNIPER:
            tower = SniperTower(x, y)
        elif tower_type == TowerType.CANNON:
            tower = CannonTower(x, y)
        elif tower_type == TowerType.FREEZE:
            tower = FreezeTower(x, y)
        elif tower_type == TowerType.POISON:
            tower = PoisonTower(x, y)
        elif tower_type == TowerType.LASER:
            tower = LaserTower(x, y)
        elif tower_type == TowerType.MISSILE:
            tower = MissileTower(x, y)
        else:
            tower = BasicTower(x, y)
        
        self.towers.append(tower)
        return True
    
    def select_tower(self, x: int, y: int):
        """Select a tower at the given position"""
        click_pos = Vector2(x, y)
        self.ui.selected_tower = None
        
        for tower in self.towers:
            if tower.position.distance_to(click_pos) < tower.size + 10:
                self.ui.selected_tower = tower
                break
    
    def upgrade_selected_tower(self) -> bool:
        """Upgrade the selected tower"""
        if not self.ui.selected_tower:
            return False
        
        tower = self.ui.selected_tower
        if tower.level >= 5:  # Max level
            return False
        
        if self.spend_money(tower.upgrade_cost):
            tower.upgrade()
            return True
        return False
    
    def sell_selected_tower(self) -> bool:
        """Sell the selected tower"""
        if not self.ui.selected_tower:
            return False
        
        tower = self.ui.selected_tower
        sell_price = tower.cost // 2  # Sell for half the original cost
        
        self.add_money(sell_price)
        self.towers.remove(tower)
        self.ui.selected_tower = None
        return True
    
    def update(self, dt: float):
        """Update game state"""
        if self.paused or self.state != GameStateEnum.PLAYING:
            return
        
        # Update particle system
        self.particle_system.update(dt)
        
        # Update current wave
        if self.current_wave_obj and self.current_wave_obj.started:
            if self.current_wave_obj.update(dt, self.enemies, self.game_map.path):
                # Wave completed
                self.current_wave += 1
                self.add_money(50 + self.current_wave * 10)  # Wave completion bonus
                self.prepare_next_wave()
        
        # Update towers
        for tower in self.towers[:]:
            tower.update(dt, self.enemies, self.particle_system)
        
        # Update enemies
        for enemy in self.enemies[:]:
            enemy.update(dt)
            
            # Check if enemy reached the end
            if not enemy.active and enemy.path_index >= len(enemy.path):
                self.lose_life()
                self.enemies.remove(enemy)
            elif not enemy.active:
                # Enemy died, give reward
                self.add_money(enemy.reward)
                self.enemies.remove(enemy)
        
        # Check for projectile hits
        self.check_projectile_hits()
    
    def check_projectile_hits(self):
        """Check for projectile collisions with enemies"""
        for tower in self.towers:
            for projectile in tower.projectiles[:]:
                if not projectile.active:
                    continue
                
                for enemy in self.enemies:
                    if (enemy.active and 
                        enemy.position.distance_to(projectile.position) < enemy.size):
                        
                        # Apply damage
                        damage_type = "physical"
                        if isinstance(projectile, LaserBeam):
                            damage_type = "magic"
                        
                        damage_dealt = enemy.take_damage(projectile.damage, damage_type)
                        
                        # Create hit effect
                        self.particle_system.add_explosion(enemy.position.x, enemy.position.y, 
                                                         YELLOW, 3)
                        
                        # Handle special projectile effects
                        if isinstance(projectile, Cannonball):
                            # Splash damage
                            for other_enemy in self.enemies:
                                if (other_enemy != enemy and other_enemy.active and
                                    other_enemy.position.distance_to(projectile.position) < 
                                    projectile.explosion_radius):
                                    splash_damage = projectile.damage * 0.5
                                    other_enemy.take_damage(splash_damage)
                                    self.particle_system.add_explosion(
                                        other_enemy.position.x, other_enemy.position.y, 
                                        ORANGE, 2)
                        
                        projectile.active = False
                        break
    
    def draw(self, screen: pygame.Surface):
        """Draw everything"""
        # Clear screen
        screen.fill(BLACK)
        
        if self.state == GameStateEnum.PLAYING:
            # Draw game map
            self.game_map.draw(screen)
            
            # Draw range of selected tower
            if self.ui.selected_tower:
                self.ui.selected_tower.draw_range(screen)
            
            # Draw towers
            for tower in self.towers:
                tower.draw(screen)
            
            # Draw enemies
            for enemy in self.enemies:
                enemy.draw(screen)
            
            # Draw particles
            self.particle_system.draw(screen)
            
            # Draw UI
            self.ui.draw(screen, self)
            
            # Draw selected tower highlight
            if self.ui.selected_tower:
                pygame.draw.circle(screen, WHITE, 
                                 (int(self.ui.selected_tower.position.x), 
                                  int(self.ui.selected_tower.position.y)), 
                                 self.ui.selected_tower.size + 3, 3)
        
        elif self.state == GameStateEnum.MENU:
            self.draw_menu(screen)
        elif self.state == GameStateEnum.GAME_OVER:
            self.draw_game_over(screen)
        elif self.state == GameStateEnum.VICTORY:
            self.draw_victory(screen)
    
    def draw_menu(self, screen: pygame.Surface):
        """Draw main menu"""
        screen.fill(BLACK)
        
        title_text = self.ui.font_large.render("TOWER DEFENSE", True, WHITE)
        title_rect = title_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 100))
        screen.blit(title_text, title_rect)
        
        start_text = self.ui.font_medium.render("Press SPACE to Start", True, WHITE)
        start_rect = start_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2))
        screen.blit(start_text, start_rect)
        
        quit_text = self.ui.font_medium.render("Press Q to Quit", True, WHITE)
        quit_rect = quit_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 50))
        screen.blit(quit_text, quit_rect)
    
    def draw_game_over(self, screen: pygame.Surface):
        """Draw game over screen"""
        screen.fill(BLACK)
        
        game_over_text = self.ui.font_large.render("GAME OVER", True, RED)
        game_over_rect = game_over_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 50))
        screen.blit(game_over_text, game_over_rect)
        
        score_text = self.ui.font_medium.render(f"Final Score: {self.score}", True, WHITE)
        score_rect = score_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2))
        screen.blit(score_text, score_rect)
        
        restart_text = self.ui.font_medium.render("Press R to Restart", True, WHITE)
        restart_rect = restart_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 50))
        screen.blit(restart_text, restart_rect)
    
    def draw_victory(self, screen: pygame.Surface):
        """Draw victory screen"""
        screen.fill(BLACK)
        
        victory_text = self.ui.font_large.render("VICTORY!", True, GOLD)
        victory_rect = victory_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 50))
        screen.blit(victory_text, victory_rect)
        
        score_text = self.ui.font_medium.render(f"Final Score: {self.score}", True, WHITE)
        score_rect = score_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2))
        screen.blit(score_text, score_rect)
    
    def reset_game(self):
        """Reset the game to initial state"""
        self.__init__()
        self.state = GameStateEnum.PLAYING

class Game:
    """Main game class"""
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Tower Defense Game")
        self.clock = pygame.time.Clock()
        self.running = True
        
        self.game_state = GameState()
    
    def handle_events(self):
        """Handle pygame events"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            elif event.type == pygame.KEYDOWN:
                if self.game_state.state == GameStateEnum.MENU:
                    if event.key == pygame.K_SPACE:
                        self.game_state.state = GameStateEnum.PLAYING
                    elif event.key == pygame.K_q:
                        self.running = False
                
                elif self.game_state.state == GameStateEnum.PLAYING:
                    if event.key == pygame.K_p:
                        self.game_state.paused = not self.game_state.paused
                    elif event.key == pygame.K_SPACE:
                        self.game_state.start_next_wave()
                    elif event.key == pygame.K_1:
                        self.game_state.ui.selected_tower_type = TowerType.BASIC
                    elif event.key == pygame.K_2:
                        self.game_state.ui.selected_tower_type = TowerType.SNIPER
                    elif event.key == pygame.K_3:
                        self.game_state.ui.selected_tower_type = TowerType.CANNON
                    elif event.key == pygame.K_4:
                        self.game_state.ui.selected_tower_type = TowerType.FREEZE
                    elif event.key == pygame.K_5:
                        self.game_state.ui.selected_tower_type = TowerType.POISON
                    elif event.key == pygame.K_6:
                        self.game_state.ui.selected_tower_type = TowerType.LASER
                    elif event.key == pygame.K_7:
                        self.game_state.ui.selected_tower_type = TowerType.MISSILE
                
                elif self.game_state.state == GameStateEnum.GAME_OVER:
                    if event.key == pygame.K_r:
                        self.game_state.reset_game()
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    self.handle_click(event.pos)
    
    def handle_click(self, pos: Tuple[int, int]):
        """Handle mouse clicks"""
        action = self.game_state.ui.handle_click(pos, self.game_state)
        
        if action == "game_area_click":
            x, y = pos
            # Try to place tower or select existing tower
            if not self.game_state.place_tower(x, y, self.game_state.ui.selected_tower_type):
                self.game_state.select_tower(x, y)
        
        elif action == "next_wave":
            self.game_state.start_next_wave()
        
        elif action == "upgrade_tower":
            self.game_state.upgrade_selected_tower()
        
        elif action == "sell_tower":
            self.game_state.sell_selected_tower()
        
        elif action in ["basic_tower", "sniper_tower", "cannon_tower", "freeze_tower", 
                       "poison_tower", "laser_tower", "missile_tower"]:
            tower_type_map = {
                "basic_tower": TowerType.BASIC,
                "sniper_tower": TowerType.SNIPER,
                "cannon_tower": TowerType.CANNON,
                "freeze_tower": TowerType.FREEZE,
                "poison_tower": TowerType.POISON,
                "laser_tower": TowerType.LASER,
                "missile_tower": TowerType.MISSILE,
            }
            self.game_state.ui.selected_tower_type = tower_type_map[action]
    
    def update(self, dt: float):
        """Update game"""
        self.game_state.update(dt)
    
    def draw(self):
        """Draw everything"""
        self.game_state.draw(self.screen)
        pygame.display.flip()
    
    def run(self):
        """Main game loop"""
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0  # Delta time in seconds
            
            self.handle_events()
            self.update(dt)
            self.draw()
        
        pygame.quit()

def main():
    """Entry point"""
    game = Game()
    game.run()

if __name__ == "__main__":
    main()