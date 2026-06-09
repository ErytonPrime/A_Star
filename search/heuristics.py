from math import sqrt, log
from typing import Callable
from topology.grid import Node


def euclidean(a: Node, b: Node) -> float:
    """
    Straight line distance between two nodes.
    Admissible for all grid types since it never overestimates.
    """
    dx = a.world_position.x - b.world_position.x
    dy = a.world_position.y - b.world_position.y
    return sqrt(dx * dx + dy * dy)


def euclidean_squared(a: Node, b: Node) -> float:
    """
    Squared Euclidean distance.
    Inadmissible — grows much faster than true cost at larger distances.
    Strongly biases search toward the goal, often missing optimal paths.
    """
    dx = a.world_position.x - b.world_position.x
    dy = a.world_position.y - b.world_position.y
    return dx * dx + dy * dy


def euclidean_sqrt(a: Node, b: Node) -> float:
    """
    Square root of Euclidean distance.
    Admissible — grows slower than true distance, never overestimates.
    More conservative than Euclidean, explores more nodes.
    """
    return sqrt(euclidean(a, b))


def euclidean_log(a: Node, b: Node) -> float:
    """
    Logarithm of Euclidean distance.
    Admissible for distances > 1 — grows very slowly.
    Nearly blind heuristic, approaches BFS behavior.
    """
    return log(euclidean(a, b) + 1)


def manhattan(a: Node, b: Node) -> float:
    """
    Sum of absolute differences in grid coordinates.
    Admissible for square grids with no diagonal movement.
    Inadmissible for hex and triangle grids.
    """
    return abs(a.grid_position.x - b.grid_position.x) + abs(
        a.grid_position.y - b.grid_position.y
    )


def weighted_euclidean(a: Node, b: Node, weight: float = 2.0) -> float:
    """
    Euclidean distance multiplied by a weight factor.
    Inadmissible when weight > 1 — overestimates the true cost.
    Finds paths faster but sacrifices optimality.
    """
    return euclidean(a, b) * weight


HEURISTICS: dict[str, Callable[[Node, Node], float]] = {
    "Euclidean": euclidean,
    "Euclidean Squared": euclidean_squared,
    "Euclidean Sqrt": euclidean_sqrt,
    "Euclidean Log": euclidean_log,
    "Manhattan": manhattan,
    "Weighted Euclidean x2": weighted_euclidean,
}
