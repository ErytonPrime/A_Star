from enum import Enum, auto
from world_content.terrain import TerrainType


class Biome(Enum):
    PLAINS = auto()
    WOODLANDS = auto()
    WETLANDS = auto()
    MOUNTAINS = auto()
    DESERT = auto()
    TUNDRA = auto()
    URBAN = auto()
    JUNGLE = auto()


# Biome movement cost modifiers
BIOME_MODIFIER: dict[Biome, float] = {
    Biome.PLAINS: 1.0,
    Biome.WOODLANDS: 1.1,
    Biome.URBAN: 1.0,
    Biome.WETLANDS: 1.3,
    Biome.JUNGLE: 1.4,
    Biome.DESERT: 1.5,
    Biome.MOUNTAINS: 1.6,
    Biome.TUNDRA: 1.7,
}


# Target terrain compositions per biome
# Values are weights, not strict percentages — WFC uses these as targets
BIOME_COMPOSITION: dict[Biome, dict[TerrainType, float]] = {
    Biome.PLAINS: {
        TerrainType.GRASSLAND: 0.50,
        TerrainType.SCRUBLAND: 0.20,
        TerrainType.DIRT_PATH: 0.15,
        TerrainType.HILLS: 0.10,
        TerrainType.FOREST: 0.05,
    },
    Biome.WOODLANDS: {
        TerrainType.FOREST: 0.40,
        TerrainType.DENSE_FOREST: 0.20,
        TerrainType.GRASSLAND: 0.15,
        TerrainType.DIRT_PATH: 0.15,
        TerrainType.SHALLOW_WATER: 0.10,
    },
    Biome.WETLANDS: {
        TerrainType.SWAMP: 0.30,
        TerrainType.SHALLOW_WATER: 0.20,
        TerrainType.MUD: 0.20,
        TerrainType.DEEP_WATER: 0.15,
        TerrainType.GRASSLAND: 0.10,
        TerrainType.DIRT_PATH: 0.05,
    },
    Biome.MOUNTAINS: {
        TerrainType.MOUNTAIN: 0.25,
        TerrainType.ROCKY_GROUND: 0.25,
        TerrainType.HILLS: 0.20,
        TerrainType.SNOW: 0.15,
        TerrainType.THIN_ICE: 0.05,
        TerrainType.SHALLOW_WATER: 0.05,
        TerrainType.FOREST: 0.05,
    },
    Biome.DESERT: {
        TerrainType.SAND: 0.50,
        TerrainType.ROCKY_GROUND: 0.20,
        TerrainType.SCRUBLAND: 0.15,
        TerrainType.HILLS: 0.10,
        TerrainType.SHALLOW_WATER: 0.05,
    },
    Biome.TUNDRA: {
        TerrainType.SNOW: 0.35,
        TerrainType.ROCKY_GROUND: 0.25,
        TerrainType.THIN_ICE: 0.15,
        TerrainType.SCRUBLAND: 0.10,
        TerrainType.MUD: 0.10,
        TerrainType.SHALLOW_WATER: 0.05,
    },
    Biome.URBAN: {
        TerrainType.PAVEMENT: 0.35,
        TerrainType.COBBLESTONE: 0.20,
        TerrainType.BUILDING: 0.20,
        TerrainType.DIRT_PATH: 0.10,
        TerrainType.RUBBLE: 0.10,
        TerrainType.GRASSLAND: 0.05,
    },
    Biome.JUNGLE: {
        TerrainType.JUNGLE: 0.35,
        TerrainType.RAINFOREST: 0.25,
        TerrainType.DENSE_FOREST: 0.15,
        TerrainType.SWAMP: 0.10,
        TerrainType.MUD: 0.10,
        TerrainType.SHALLOW_WATER: 0.05,
    },
}


def get_modifier(biome: Biome) -> float:
    """Return the movement cost modifier for a biome."""
    return BIOME_MODIFIER[biome]


def get_composition(biome: Biome) -> dict[TerrainType, float]:
    """Return the target terrain composition for a biome."""
    return BIOME_COMPOSITION[biome]
