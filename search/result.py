from dataclasses import dataclass, field
from topology.grid import Node


@dataclass
class SearchResult:
    # The nodes visited in order — for visualization
    visited: list[Node] = field(default_factory=list)
    # The final path from start to goal — empty if no path found
    path: list[Node] = field(default_factory=list)
    # Whether a valid path was found
    success: bool = False
    # Total path cost
    cost: float = 0.0
