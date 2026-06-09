from collections import deque
from topology.grid import Grid, Node
from world_content.terrain import TerrainType, TERRAIN_COST
from search.result import SearchResult
import math


def run(
    grid: Grid,
    terrain_map: dict[tuple[int, int], TerrainType],
    start: Node,
    goal: Node,
    biome_modifier: float = 1.0,
) -> SearchResult:
    """
    Flood fill from start node, expanding to all reachable passable nodes.
    Returns all visited nodes in order and whether the goal is reachable.
    """
    visited: list[Node] = []
    visited_set: set[tuple[int, int]] = set()
    queue: deque[Node] = deque()

    start_coords = (start.grid_position.x, start.grid_position.y)
    queue.append(start)
    visited_set.add(start_coords)

    goal_reached = False

    while queue:
        current = queue.popleft()
        visited.append(current)

        if current == goal:
            goal_reached = True
            break

        for neighbour in grid.get_neighbours(current):
            coords = (neighbour.grid_position.x, neighbour.grid_position.y)
            if coords in visited_set:
                continue

            terrain = terrain_map.get(coords)
            if terrain is None:
                continue

            cost = TERRAIN_COST[terrain]
            if cost == math.inf:
                continue

            visited_set.add(coords)
            queue.append(neighbour)

    return SearchResult(
        visited=visited,
        path=[],
        success=goal_reached,
        cost=0.0,
    )
