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
    Depth-first search from start to goal.
    Finds a path but not necessarily the optimal one.
    """
    visited: list[Node] = []
    visited_set: set[tuple[int, int]] = set()
    parent: dict[tuple[int, int], Node | None] = {}
    stack: list[Node] = []

    start_coords = (start.grid_position.x, start.grid_position.y)
    stack.append(start)
    parent[start_coords] = None

    goal_reached = False

    while stack:
        current = stack.pop()
        coords = (current.grid_position.x, current.grid_position.y)

        if coords in visited_set:
            continue

        visited_set.add(coords)
        visited.append(current)

        if current == goal:
            goal_reached = True
            break

        for neighbour in grid.get_neighbours(current):
            n_coords = (neighbour.grid_position.x, neighbour.grid_position.y)
            if n_coords in visited_set:
                continue

            terrain = terrain_map.get(n_coords)
            if terrain is None:
                continue

            cost = TERRAIN_COST[terrain]
            if cost == math.inf:
                continue

            if n_coords not in parent:
                parent[n_coords] = current
            stack.append(neighbour)

    # Reconstruct path
    path: list[Node] = []
    total_cost = 0.0

    if goal_reached:
        node: Node | None = goal
        while node is not None:
            path.append(node)
            n_coords = (node.grid_position.x, node.grid_position.y)
            terrain = terrain_map.get(n_coords)
            if terrain is not None:
                total_cost += TERRAIN_COST[terrain] * biome_modifier
            node = parent.get(n_coords)
        path.reverse()

    return SearchResult(
        visited=visited,
        path=path,
        success=goal_reached,
        cost=total_cost,
    )
