from topology.grid import Grid, Shape
from visualization.visual import run


def main():
    current_grid = Grid(2, 1, Shape.SQUARE)
    set_grid = None  # will be assigned once the visualizer is ready

    def on_grid_ready(callback):
        nonlocal set_grid
        set_grid = callback
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
        if set_grid:
            set_grid(current_grid)

    run(
        on_generate=on_generate,
        on_grid_ready=on_grid_ready,
        initial_width=2,
        initial_height=1,
    )


if __name__ == "__main__":
    main()
