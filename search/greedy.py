import heapq
import math
from typing import Callable
from topology.grid import Grid, Node
from world_content.terrain import TerrainType, TERRAIN_COST
from search.result import SearchResult
from search.heuristics import euclidean


def run(
    grid: Grid,
    terrain_map: dict[tuple[int, int], TerrainType],
    start: Node,
    goal: Node,
    biome_modifier: float = 1.0,
    heuristic: Callable[[Node, Node], float] = euclidean,
) -> SearchResult:
    """
    Greedy Best-First Search from start to goal.
    Always expands the node that looks closest to the goal.
    Fast but not guaranteed to find the optimal path.
    """
    visited: list[Node] = []
    visited_set: set[tuple[int, int]] = set()
    parent: dict[tuple[int, int], Node | None] = {}
    heap: list[tuple[float, int, int]] = []

    start_coords = (start.grid_position.x, start.grid_position.y)
    parent[start_coords] = None
    heapq.heappush(heap, (heuristic(start, goal), start_coords[0], start_coords[1]))

    goal_reached = False

    while heap:
        _, cx, cy = heapq.heappop(heap)
        coords = (cx, cy)

        if coords in visited_set:
            continue

        current = grid.get_node(cx, cy)
        if current is None:
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

            if TERRAIN_COST[terrain] == math.inf:
                continue

            if n_coords not in parent:
                parent[n_coords] = current

            h = heuristic(neighbour, goal)
            heapq.heappush(heap, (h, n_coords[0], n_coords[1]))

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
