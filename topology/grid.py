from enum import Enum, auto
from dataclasses import dataclass
from math import sqrt


class Shape(Enum):
    SQUARE = auto()
    HEXAGON = auto()
    TRIANGLE = auto()


@dataclass(frozen=True)
class GridCoordinate:
    x: int
    y: int


@dataclass(frozen=True)
class WorldCoordinate:
    x: float
    y: float


@dataclass
class Node:
    grid_position: GridCoordinate
    world_position: WorldCoordinate

    # terrain: Terrain | None = None


class Grid:
    def __init__(self, width: int, height: int, shape: Shape):
        self.width = width
        self.height = height
        self.shape = shape

        self.nodes: dict[tuple[int, int], Node] = {}

        self._create_nodes()

    def __repr__(self):
        return f"Grid(width={self.width}, height={self.height}, shape={self.shape.name}, nodes={len(self.nodes)})"

    def _create_nodes(self):
        for y in range(self.height):
            for x in range(self.width):
                world_x, world_y = self.grid_to_world(x, y)

                node = Node(
                    grid_position=GridCoordinate(x, y),
                    world_position=WorldCoordinate(world_x, world_y),
                )

                self.nodes[(x, y)] = node

    def grid_to_world(self, x, y) -> tuple[float, float]:
        match self.shape:
            case Shape.SQUARE:
                return x + 0.5, y + 0.5

            case Shape.HEXAGON:
                if x % 2 == 1:
                    return 1.5 * x, sqrt(3) * y + sqrt(3) / 2
                return 1.5 * x, sqrt(3) * y

            case Shape.TRIANGLE:
                if (x + y) % 2 == 1:
                    return x / 2, sqrt(3) / 2 * y + (1 / sqrt(3))
                return x / 2, sqrt(3) / 2 * y + (1 / (2 * sqrt(3)))

            case _:
                raise ValueError(f"Unsupported shape: {self.shape}")

    def get_node(self, x: int, y: int) -> Node | None:
        return self.nodes.get((x, y))

    def all_nodes(self):
        return self.nodes.values()

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def get_neighbours(self, node: Node) -> list[Node]:

        neighbours = []

        for dx, dy in self.get_directions(node):
            nx = node.grid_position.x + dx
            ny = node.grid_position.y + dy

            if self.in_bounds(nx, ny):
                neighbour = self.get_node(nx, ny)
                if neighbour is not None:
                    neighbours.append(neighbour)

        return neighbours

    def get_directions(self, node: Node) -> list[tuple[int, int]]:
        match self.shape:
            case Shape.SQUARE:
                return [(1, 0), (0, 1), (-1, 0), (0, -1)]

            case Shape.HEXAGON:
                if node.grid_position.x % 2 == 1:
                    return [(1, 0), (0, 1), (-1, 0), (0, -1), (1, 1), (-1, 1)]
                return [(1, 0), (0, 1), (-1, 0), (0, -1), (-1, -1), (1, -1)]

            case Shape.TRIANGLE:
                if (node.grid_position.x + node.grid_position.y) % 2 == 1:
                    return [(-1, 0), (0, 1), (1, 0)]
                return [(-1, 0), (0, -1), (1, 0)]

            case _:
                raise ValueError(f"Unsupported shape: {self.shape}")
