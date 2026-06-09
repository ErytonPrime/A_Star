import time
import math
import random
from typing import Optional, Callable
from topology.grid import Grid, Shape, Node
from world_content.biome import Biome, get_composition, get_modifier
from world_content.terrain import TerrainType, get_valid_start_terrains, TERRAIN_COST
from world_content.wfc import generate
from search import flood_fill, dfs, bfs, dijkstra, greedy, astar
from search.result import SearchResult
from search.heuristics import HEURISTICS, euclidean
from visualization.visual import run


ALGORITHMS = {
    "DFS": dfs,
    "BFS": bfs,
    "Dijkstra": dijkstra,
    "Greedy": greedy,
    "A*": astar,
}

HEURISTIC_ALGORITHMS = {"Greedy", "A*"}


def main():
    current_grid: Grid = Grid(2, 1, Shape.SQUARE)
    current_terrain_map: dict[tuple[int, int], TerrainType] = {}
    current_biome_modifier: float = 1.0
    current_biome: Optional[Biome] = None
    current_start: Optional[Node] = None
    current_goal: Optional[Node] = None
    valid_start_terrains: frozenset[TerrainType] = frozenset()

    set_grid_callback: Optional[Callable[[Grid], None]] = None
    set_terrain_callback: Optional[
        Callable[
            [dict[tuple[int, int], TerrainType], frozenset[TerrainType], float], None
        ]
    ] = None
    set_result_callback: Optional[Callable[[SearchResult, float], None]] = None
    set_flood_fill_callback: Optional[Callable[[SearchResult], None]] = None
    set_error_callback: Optional[Callable[[str], None]] = None
    set_start_callback: Optional[Callable[[Node], None]] = None
    set_goal_callback: Optional[Callable[[Node], None]] = None

    def on_grid_ready(
        set_grid,
        set_terrain,
        set_result,
        set_flood_fill,
        set_error,
        set_start,
        set_goal,
    ):
        nonlocal \
            set_grid_callback, \
            set_terrain_callback, \
            set_result_callback, \
            set_flood_fill_callback, \
            set_error_callback, \
            set_start_callback, \
            set_goal_callback
        set_grid_callback = set_grid
        set_terrain_callback = set_terrain
        set_result_callback = set_result
        set_flood_fill_callback = set_flood_fill
        set_error_callback = set_error
        set_start_callback = set_start
        set_goal_callback = set_goal
        set_grid(current_grid)

    def on_generate(width, height, shape_name):
        nonlocal \
            current_grid, \
            current_terrain_map, \
            current_biome_modifier, \
            current_biome
        nonlocal current_start, current_goal
        shape_map = {
            "Square": Shape.SQUARE,
            "Hexagon": Shape.HEXAGON,
            "Triangle": Shape.TRIANGLE,
        }
        current_grid = Grid(width, height, shape_map[shape_name])
        current_terrain_map = {}
        current_biome_modifier = 1.0
        current_start = None
        current_goal = None
        if set_grid_callback:
            set_grid_callback(current_grid)
        if set_terrain_callback:
            set_terrain_callback({}, frozenset(), 1.0)

    def on_populate(biome: Biome, seed: int):
        nonlocal \
            valid_start_terrains, \
            current_terrain_map, \
            current_biome_modifier, \
            current_biome
        nonlocal current_start, current_goal
        composition = get_composition(biome)
        valid_start_terrains = get_valid_start_terrains(composition)
        current_terrain_map = generate(current_grid, biome, seed=seed)
        current_biome_modifier = get_modifier(biome)
        current_biome = biome
        current_start = None
        current_goal = None
        if set_terrain_callback:
            set_terrain_callback(
                current_terrain_map, valid_start_terrains, current_biome_modifier
            )

    def on_start_set(node: Node):
        nonlocal current_start
        current_start = node

    def on_goal_set(node: Node):
        nonlocal current_goal
        current_goal = node

    def on_run(algorithm_name: str, heuristic_name: str, run_flood_fill: bool):
        nonlocal current_start, current_goal, current_terrain_map
        nonlocal current_biome, current_biome_modifier, valid_start_terrains

        # Auto-populate if terrain is empty
        if not current_terrain_map:
            if current_biome is None:
                current_biome = Biome.PLAINS
            composition = get_composition(current_biome)
            valid_start_terrains = get_valid_start_terrains(composition)
            current_terrain_map = generate(current_grid, current_biome, seed=42)
            current_biome_modifier = get_modifier(current_biome)
            if set_terrain_callback:
                set_terrain_callback(
                    current_terrain_map, valid_start_terrains, current_biome_modifier
                )

        # Auto-assign random valid start in upper left quadrant
        if current_start is None:
            mid_x = current_grid.width // 2
            mid_y = current_grid.height // 2
            valid_starts = [
                current_grid.get_node(x, y)
                for (x, y), t in current_terrain_map.items()
                if t in valid_start_terrains and x < mid_x and y < mid_y
            ]
            if not valid_starts:
                valid_starts = [
                    current_grid.get_node(x, y)
                    for (x, y), t in current_terrain_map.items()
                    if t in valid_start_terrains
                ]
            if not valid_starts:
                if set_error_callback:
                    set_error_callback("No valid start tiles found.")
                return
            current_start = random.choice([n for n in valid_starts if n is not None])
            if set_start_callback:
                set_start_callback(current_start)

        # Auto-assign random valid goal in lower right quadrant
        if current_goal is None:
            mid_x = current_grid.width // 2
            mid_y = current_grid.height // 2
            valid_goals = [
                current_grid.get_node(x, y)
                for (x, y), t in current_terrain_map.items()
                if TERRAIN_COST[t] != math.inf and x >= mid_x and y >= mid_y
            ]
            if not valid_goals:
                valid_goals = [
                    current_grid.get_node(x, y)
                    for (x, y), t in current_terrain_map.items()
                    if TERRAIN_COST[t] != math.inf
                ]
            if not valid_goals:
                if set_error_callback:
                    set_error_callback("No valid goal tiles found.")
                return
            current_goal = random.choice([n for n in valid_goals if n is not None])
            if set_goal_callback:
                set_goal_callback(current_goal)

        # Build admissible scaled heuristic
        if current_biome is not None:
            composition = get_composition(current_biome)
            min_cost = min(
                TERRAIN_COST[t] * current_biome_modifier
                for t in composition.keys()
                if TERRAIN_COST[t] != math.inf
            )
        else:
            min_cost = 1.0

        base_heuristic = HEURISTICS.get(heuristic_name, euclidean)

        def scaled_heuristic(a, b):
            return base_heuristic(a, b) * min_cost

        # Run flood fill if requested
        if run_flood_fill:
            ff_result = flood_fill.run(
                current_grid,
                current_terrain_map,
                current_start,
                current_goal,
                current_biome_modifier,
            )
            if set_flood_fill_callback:
                set_flood_fill_callback(ff_result)
            if not ff_result.success:
                return

        algorithm = ALGORITHMS[algorithm_name]
        start_time = time.perf_counter()

        if algorithm_name in HEURISTIC_ALGORITHMS:
            result = algorithm.run(
                current_grid,
                current_terrain_map,
                current_start,
                current_goal,
                current_biome_modifier,
                scaled_heuristic,
            )
        else:
            result = algorithm.run(
                current_grid,
                current_terrain_map,
                current_start,
                current_goal,
                current_biome_modifier,
            )

        runtime = time.perf_counter() - start_time

        if set_result_callback:
            set_result_callback(result, runtime)

    run(
        on_generate=on_generate,
        on_populate=on_populate,
        on_grid_ready=on_grid_ready,
        on_start_set=on_start_set,
        on_goal_set=on_goal_set,
        on_run=on_run,
        initial_width=2,
        initial_height=1,
    )


if __name__ == "__main__":
    main()
