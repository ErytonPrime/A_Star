from enum import Enum, auto
import math


class TerrainType(Enum):
    # Impassable
    DEEP_WATER = auto()
    MOUNTAIN = auto()
    THIN_ICE = auto()
    BUILDING = auto()

    # Very High
    SHALLOW_WATER = auto()

    # High
    SWAMP = auto()
    DENSE_FOREST = auto()
    ROCKY_GROUND = auto()
    JUNGLE = auto()
    RAINFOREST = auto()

    # Medium
    FOREST = auto()
    HILLS = auto()
    SNOW = auto()
    SAND = auto()
    RUBBLE = auto()
    MUD = auto()

    # Low
    GRASSLAND = auto()
    SCRUBLAND = auto()

    # Very Low
    DIRT_PATH = auto()
    PAVEMENT = auto()
    COBBLESTONE = auto()


# Base movement costs per terrain type
TERRAIN_COST: dict[TerrainType, float] = {
    TerrainType.DEEP_WATER: math.inf,
    TerrainType.MOUNTAIN: math.inf,
    TerrainType.THIN_ICE: math.inf,
    TerrainType.BUILDING: math.inf,
    TerrainType.SHALLOW_WATER: 8.0,
    TerrainType.SWAMP: 4.0,
    TerrainType.DENSE_FOREST: 4.0,
    TerrainType.ROCKY_GROUND: 4.0,
    TerrainType.JUNGLE: 4.0,
    TerrainType.RAINFOREST: 4.0,
    TerrainType.FOREST: 2.0,
    TerrainType.HILLS: 2.0,
    TerrainType.SNOW: 2.0,
    TerrainType.SAND: 2.0,
    TerrainType.RUBBLE: 2.0,
    TerrainType.MUD: 2.0,
    TerrainType.GRASSLAND: 1.0,
    TerrainType.SCRUBLAND: 1.0,
    TerrainType.DIRT_PATH: 0.5,
    TerrainType.PAVEMENT: 0.5,
    TerrainType.COBBLESTONE: 0.5,
}

TERRAIN_COLORS: dict[TerrainType, tuple[int, int, int]] = {
    TerrainType.DEEP_WATER: (20, 60, 120),
    TerrainType.SHALLOW_WATER: (60, 130, 190),
    TerrainType.MOUNTAIN: (120, 100, 90),
    TerrainType.THIN_ICE: (200, 225, 240),
    TerrainType.BUILDING: (80, 80, 85),
    TerrainType.SWAMP: (60, 80, 50),
    TerrainType.DENSE_FOREST: (30, 90, 40),
    TerrainType.ROCKY_GROUND: (130, 115, 100),
    TerrainType.JUNGLE: (40, 110, 50),
    TerrainType.RAINFOREST: (20, 140, 60),
    TerrainType.FOREST: (60, 130, 60),
    TerrainType.HILLS: (140, 150, 90),
    TerrainType.SNOW: (220, 230, 240),
    TerrainType.SAND: (210, 190, 130),
    TerrainType.RUBBLE: (140, 120, 100),
    TerrainType.MUD: (100, 85, 65),
    TerrainType.GRASSLAND: (120, 180, 80),
    TerrainType.SCRUBLAND: (160, 170, 90),
    TerrainType.DIRT_PATH: (170, 140, 100),
    TerrainType.PAVEMENT: (150, 150, 155),
    TerrainType.COBBLESTONE: (130, 125, 115),
}


def get_cost(terrain: TerrainType, biome_modifier: float = 1.0) -> float:
    """Return the movement cost for a terrain type with optional biome modifier."""
    base = TERRAIN_COST[terrain]
    if base == math.inf:
        return math.inf
    return base * biome_modifier
