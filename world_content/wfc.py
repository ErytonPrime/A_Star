import math
import random
from typing import Optional
from topology.grid import Grid
from world_content.terrain import TerrainType, TERRAIN_COST
from world_content.biome import Biome, get_composition
from world_content.affinity import get_affinity


def _affinity_score(
    terrain: TerrainType, collapsed_neighbours: list[TerrainType]
) -> float:
    """Product of affinities between a candidate terrain and all collapsed neighbours."""
    if not collapsed_neighbours:
        return 1.0
    score = 1.0
    for neighbour_terrain in collapsed_neighbours:
        score *= get_affinity(terrain, neighbour_terrain)
    return score


def _correction(
    terrain: TerrainType,
    current_counts: dict[TerrainType, int],
    target_composition: dict[TerrainType, float],
    total_collapsed: int,
) -> float:
    """
    Restoring force toward target biome composition.
    Returns a weight > 1 if terrain is underrepresented, < 1 if overrepresented.
    Uses exponential correction: exp(target_fraction - current_fraction)
    """
    if terrain not in target_composition:
        return 0.0  # terrain not in this biome — impossible

    target = target_composition[terrain]

    if total_collapsed == 0:
        current = 0.0
    else:
        current = current_counts.get(terrain, 0) / total_collapsed

    return math.exp(target - current)


def _compute_probabilities(
    candidate_terrains: list[TerrainType],
    collapsed_neighbours: list[TerrainType],
    current_counts: dict[TerrainType, int],
    target_composition: dict[TerrainType, float],
    total_collapsed: int,
) -> dict[TerrainType, float]:
    """
    Compute normalized probability distribution over candidate terrains
    by combining affinity score and correction multiplicatively.
    """
    raw: dict[TerrainType, float] = {}

    for terrain in candidate_terrains:
        affinity = _affinity_score(terrain, collapsed_neighbours)
        correction = _correction(
            terrain, current_counts, target_composition, total_collapsed
        )
        raw[terrain] = affinity * correction

    total = sum(raw.values())

    if total == 0.0:
        # All probabilities collapsed to zero — fall back to uniform over biome terrains
        biome_terrains = list(target_composition.keys())
        return {t: 1.0 / len(biome_terrains) for t in biome_terrains}

    return {t: w / total for t, w in raw.items()}


def _shannon_entropy(probabilities: dict[TerrainType, float]) -> float:
    """Compute Shannon entropy of a probability distribution."""
    entropy = 0.0
    for p in probabilities.values():
        if p > 0:
            entropy -= p * math.log(p)
    return entropy


def _sample(probabilities: dict[TerrainType, float]) -> TerrainType:
    """Sample a terrain type from a probability distribution."""
    terrains = list(probabilities.keys())
    weights = [probabilities[t] for t in terrains]
    return random.choices(terrains, weights=weights, k=1)[0]


def _is_impassable(terrain: TerrainType) -> bool:
    return TERRAIN_COST[terrain] == math.inf


def _fix_isolated_tiles(
    collapsed: dict[tuple[int, int], TerrainType],
    grid: Grid,
) -> dict[tuple[int, int], TerrainType]:
    """
    Replace passable tiles that are completely surrounded by impassable
    tiles with the most common impassable neighbour terrain.
    Repeats until no isolated tiles remain.
    """
    changed = True
    while changed:
        changed = False
        for coords, terrain in list(collapsed.items()):
            if _is_impassable(terrain):
                continue

            node = grid.get_node(*coords)
            assert node is not None

            neighbour_terrains = [
                collapsed[(n.grid_position.x, n.grid_position.y)]
                for n in grid.get_neighbours(node)
                if (n.grid_position.x, n.grid_position.y) in collapsed
            ]

            if not neighbour_terrains:
                continue

            all_impassable = all(_is_impassable(t) for t in neighbour_terrains)

            if all_impassable:
                # Replace with most common impassable neighbour
                impassable_neighbours = [
                    t for t in neighbour_terrains if _is_impassable(t)
                ]
                replacement = max(
                    set(impassable_neighbours), key=impassable_neighbours.count
                )
                collapsed[coords] = replacement
                changed = True

    return collapsed


def generate(
    grid: Grid,
    biome: Biome,
    seed: Optional[int] = None,
) -> dict[tuple[int, int], TerrainType]:
    """
    Run WFC terrain generation on the grid for the given biome.
    Returns a mapping of grid coordinates to terrain types.
    """
    if seed is not None:
        random.seed(seed)

    target_composition = get_composition(biome)
    candidate_terrains = list(target_composition.keys())

    # State
    collapsed: dict[tuple[int, int], TerrainType] = {}
    current_counts: dict[TerrainType, int] = {t: 0 for t in candidate_terrains}

    # All nodes start uncollapsed
    uncollapsed: set[tuple[int, int]] = set(grid.nodes.keys())

    while uncollapsed:
        # --- Find cell with lowest Shannon entropy ---
        lowest_entropy = math.inf
        lowest_coords: Optional[tuple[int, int]] = None

        for coords in uncollapsed:
            node = grid.get_node(*coords)
            assert node is not None

            # Get already collapsed neighbours
            collapsed_neighbours = [
                collapsed[n.grid_position.x, n.grid_position.y]
                for n in grid.get_neighbours(node)
                if (n.grid_position.x, n.grid_position.y) in collapsed
            ]

            probs = _compute_probabilities(
                candidate_terrains,
                collapsed_neighbours,
                current_counts,
                target_composition,
                len(collapsed),
            )

            entropy = _shannon_entropy(probs)

            # Add tiny noise to break ties randomly
            entropy += random.uniform(0, 1e-6)

            if entropy < lowest_entropy:
                lowest_entropy = entropy
                lowest_coords = coords

        assert lowest_coords is not None

        # --- Collapse the chosen cell ---
        node = grid.get_node(*lowest_coords)
        assert node is not None

        collapsed_neighbours = [
            collapsed[n.grid_position.x, n.grid_position.y]
            for n in grid.get_neighbours(node)
            if (n.grid_position.x, n.grid_position.y) in collapsed
        ]

        probs = _compute_probabilities(
            candidate_terrains,
            collapsed_neighbours,
            current_counts,
            target_composition,
            len(collapsed),
        )

        chosen = _sample(probs)
        collapsed[lowest_coords] = chosen
        current_counts[chosen] += 1
        uncollapsed.remove(lowest_coords)

    # Post-generation cleanup
    collapsed = _fix_isolated_tiles(collapsed, grid)

    return collapsed
