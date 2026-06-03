from topology.grid import Grid, Shape
from world_content.biome import Biome
from typing import Optional, Callable
from world_content.terrain import TerrainType
from world_content.wfc import generate
from visualization.visual import run


def main():
    current_grid = Grid(2, 1, Shape.SQUARE)
    set_grid_callback: Optional[Callable[[Grid], None]] = (
        None  # will be assigned once the visualizer is ready
    )
    set_terrain_callback: Optional[
        Callable[[dict[tuple[int, int], TerrainType]], None]
    ] = None  # will be assigned once biome and seed are choosen

    def on_grid_ready(set_grid, set_terrain):
        nonlocal set_grid_callback, set_terrain_callback
        set_grid_callback = set_grid
        set_terrain_callback = set_terrain
        # Push the initial grid immediately
        set_grid(current_grid)

    def on_generate(width, height, shape_name):
        nonlocal current_grid
        shape_map = {
            "Square": Shape.SQUARE,
            "Hexagon": Shape.HEXAGON,
            "Triangle": Shape.TRIANGLE,
        }
        current_grid = Grid(width, height, shape_map[shape_name])
        if set_grid_callback:
            set_grid_callback(current_grid)
        if set_terrain_callback:
            set_terrain_callback({})

    def on_populate(biome: Biome, seed: int):
        if current_grid is None:
            return
        terrain_map = generate(current_grid, biome, seed=seed)
        if set_terrain_callback:
            set_terrain_callback(terrain_map)

    run(
        on_generate=on_generate,
        on_populate=on_populate,
        on_grid_ready=on_grid_ready,
        initial_width=2,
        initial_height=1,
    )


if __name__ == "__main__":
    main()
