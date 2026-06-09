import os
import json
import math
import pygame
import pygame_gui
from math import sqrt
from typing import List, Tuple
from visualization.camera import Camera
from visualization.popup import Popup
from topology.grid import Shape, Node
from world_content.terrain import TerrainType, TERRAIN_COLORS, VALID_GOAL_TERRAINS
from world_content.biome import Biome
from search.result import SearchResult
from search.heuristics import HEURISTICS

# Detect monitor resolution at import time
pygame.init()
_monitor_size = pygame.display.get_desktop_sizes()[0]
pygame.quit()

# Internal resolution matches monitor — no scaling artifacts
INTERNAL_WIDTH, INTERNAL_HEIGHT = _monitor_size

# Layout constants — all relative to internal resolution
SIDEBAR_WIDTH = min(int(INTERNAL_WIDTH * 0.175), 400)
CANVAS_WIDTH = INTERNAL_WIDTH - SIDEBAR_WIDTH

# Sidebar layout helpers — relative to sidebar and screen height
PADDING = int(INTERNAL_WIDTH * 0.0125)
LABEL_WIDTH = int(SIDEBAR_WIDTH * 0.35)
WIDGET_HEIGHT = int(INTERNAL_HEIGHT * 0.032)
PANEL_BORDER_RADIUS = 6

# Font sizes
FONT_SIZE_SMALL = int(WIDGET_HEIGHT * 0.3)
FONT_SIZE_MEDIUM = int(WIDGET_HEIGHT * 0.42)
FONT_SIZE_LARGE = int(WIDGET_HEIGHT * 0.6)

# Colors
COLOR_BACKGROUND = (30, 30, 30)
COLOR_CANVAS = (20, 20, 20)
COLOR_SIDEBAR = (45, 45, 48)
COLOR_DIVIDER = (70, 70, 70)
COLOR_PANEL_BORDER = (80, 80, 85)
COLOR_PANEL_LABEL = (180, 180, 180)
COLOR_NODE = (100, 110, 130)
COLOR_OVERLAY_BG = (15, 15, 15, 210)
COLOR_OVERLAY_BORDER = (80, 80, 85)
COLOR_OVERLAY_TITLE = (220, 220, 220)
COLOR_OVERLAY_KEY = (140, 180, 140)
COLOR_OVERLAY_TEXT = (180, 180, 180)
COLOR_START = (140, 100, 180)
COLOR_GOAL = (160, 60, 60)

# Grid input constraints
MIN_WIDTH = 2
MIN_HEIGHT = 1
MAX_SIZE = 100

# Zoom
ZOOM_IN_FACTOR = 1.1
ZOOM_OUT_FACTOR = 1 / ZOOM_IN_FACTOR

# Pulse
MAX_PULSE_TIMER = int(math.pi * 1000)

# Help content — add new controls here as the project grows
HELP_ENTRIES = [
    ("Scroll Wheel", "Zoom in / out"),
    ("Right / Middle Drag", "Pan the canvas"),
    ("F", "Toggle borderless fullscreen"),
    ("H", "Toggle this help menu"),
    ("Space", "Run algorithm"),
    ("R", "Replay visualization"),
    ("S", "Set start node"),
    ("G", "Set goal node"),
]

# Biome display names
BIOME_NAMES = {biome: biome.name.capitalize() for biome in Biome}
BIOME_BY_NAME = {v: k for k, v in BIOME_NAMES.items()}

ALGORITHMS: List[str | Tuple[str, str]] = ["DFS", "BFS", "Dijkstra", "Greedy", "A*"]


def get_square_points(sx: float, sy: float, scale: float):
    half = scale / 2
    return [
        (sx - half, sy - half),
        (sx + half, sy - half),
        (sx + half, sy + half),
        (sx - half, sy + half),
    ]


def get_hex_points(sx: float, sy: float, scale: float) -> list[tuple[float, float]]:
    """Flat-top hexagon centered at (sx, sy)."""
    r = scale
    return [
        (sx + r, sy),
        (sx + r / 2, sy + r * sqrt(3) / 2),
        (sx - r / 2, sy + r * sqrt(3) / 2),
        (sx - r, sy),
        (sx - r / 2, sy - r * sqrt(3) / 2),
        (sx + r / 2, sy - r * sqrt(3) / 2),
    ]


def get_triangle_points(
    sx: float, sy: float, scale: float, pointing_up: bool
) -> list[tuple[float, float]]:
    """Equilateral triangle, pointing up or down."""
    s = scale
    h = s * sqrt(3) / 2
    if pointing_up:
        return [
            (sx, sy - h * 2 / 3),
            (sx + s / 2, sy + h / 3),
            (sx - s / 2, sy + h / 3),
        ]
    else:
        return [
            (sx, sy + h * 2 / 3),
            (sx + s / 2, sy - h / 3),
            (sx - s / 2, sy - h / 3),
        ]


def draw_corner_lines(
    surface, points, center, color, length_fraction=0.55, line_width=4
):
    """Draw lines from each corner toward the cell center."""
    cx, cy = center
    for px, py in points:
        ex = px + (cx - px) * length_fraction
        ey = py + (cy - py) * length_fraction
        pygame.draw.line(
            surface, color, (int(px), int(py)), (int(ex), int(ey)), line_width
        )


def draw_panel(surface, font, title, rect):
    pygame.draw.rect(surface, COLOR_PANEL_BORDER, rect, 1, border_radius=6)
    label = font.render(f" {title} ", True, COLOR_PANEL_LABEL, COLOR_SIDEBAR)
    label_height = label.get_height()
    surface.blit(label, (rect.x + 10, rect.y - label_height // 2))


def draw_help_overlay(surface, title_font, key_font, manager):
    overlay_w = int(INTERNAL_WIDTH * 0.3)
    row_h = WIDGET_HEIGHT + int(INTERNAL_HEIGHT * 0.01)
    overlay_h = (
        int(INTERNAL_HEIGHT * 0.08)
        + len(HELP_ENTRIES) * row_h
        + int(INTERNAL_HEIGHT * 0.06)
    )
    overlay_x = (CANVAS_WIDTH - overlay_w) // 2
    overlay_y = (INTERNAL_HEIGHT - overlay_h) // 2

    # Background with rounded corners
    pygame.draw.rect(
        surface,
        (15, 15, 15),
        pygame.Rect(overlay_x, overlay_y, overlay_w, overlay_h),
        border_radius=8,
    )

    # Border
    pygame.draw.rect(
        surface,
        COLOR_OVERLAY_BORDER,
        pygame.Rect(overlay_x, overlay_y, overlay_w, overlay_h),
        2,
        border_radius=8,
    )

    # Title
    title_y = overlay_y + int(INTERNAL_HEIGHT * 0.02)
    title = title_font.render("Controls", True, COLOR_OVERLAY_TITLE)
    title_rect = title.get_rect(centerx=overlay_x + overlay_w // 2, y=title_y)
    surface.blit(title, title_rect)

    # Divider
    divider_y = overlay_y + int(INTERNAL_HEIGHT * 0.055)
    pygame.draw.line(
        surface,
        COLOR_OVERLAY_BORDER,
        (overlay_x + int(overlay_w * 0.05), divider_y),
        (overlay_x + int(overlay_w * 0.95), divider_y),
        1,
    )

    # Entries
    entries_start_y = overlay_y + int(INTERNAL_HEIGHT * 0.065)
    desc_x_offset = int(overlay_w * 0.45)
    for i, (key, description) in enumerate(HELP_ENTRIES):
        row_y = entries_start_y + i * row_h
        key_label = key_font.render(key, True, COLOR_OVERLAY_KEY)
        desc_label = key_font.render(description, True, COLOR_OVERLAY_TEXT)
        surface.blit(key_label, (overlay_x + int(overlay_w * 0.05), row_y))
        surface.blit(desc_label, (overlay_x + desc_x_offset, row_y))

    # Close button
    close_w = int(SIDEBAR_WIDTH * 0.5)
    close_y = overlay_y + overlay_h - int(WIDGET_HEIGHT * 1.5)
    close_x = overlay_x + (overlay_w - close_w) // 2
    return pygame.Rect(close_x, close_y, close_w, WIDGET_HEIGHT)


def draw_tooltip(surface, font, node, terrain, biome_modifier, mouse_x, mouse_y):
    from world_content.terrain import TERRAIN_COST
    import math

    # Build content lines
    if terrain is not None:
        base_cost = TERRAIN_COST[terrain]
        if base_cost == math.inf:
            cost_str = "Impassable"
        else:
            cost_str = f"{base_cost * biome_modifier:.2f}"
        terrain_str = terrain.name.replace("_", " ").title()
    else:
        cost_str = "N/A"
        terrain_str = "None"

    lines = [
        f"Terrain:  {terrain_str}",
        f"Cost:     {cost_str}",
        f"Grid:     ({node.grid_position.x}, {node.grid_position.y})",
        f"World:    ({node.world_position.x:.2f}, {node.world_position.y:.2f})",
    ]

    # Measure dimensions
    line_height = font.get_height() + int(INTERNAL_HEIGHT * 0.005)
    padding = int(INTERNAL_HEIGHT * 0.01)
    max_width = max(font.size(line)[0] for line in lines)
    tooltip_w = max_width + padding * 2
    tooltip_h = line_height * len(lines) + padding * 2

    # Offset from cursor
    offset_x = int(INTERNAL_WIDTH * 0.015)
    offset_y = int(INTERNAL_HEIGHT * 0.02)
    tx = int(mouse_x) + offset_x
    ty = int(mouse_y) + offset_y

    # Keep within canvas bounds
    if tx + tooltip_w > CANVAS_WIDTH:
        tx = int(mouse_x) - tooltip_w - offset_x
    if ty + tooltip_h > INTERNAL_HEIGHT:
        ty = int(mouse_y) - tooltip_h - offset_y

    # Background
    pygame.draw.rect(
        surface,
        (15, 15, 15),
        pygame.Rect(tx, ty, tooltip_w, tooltip_h),
        border_radius=4,
    )
    # Border
    pygame.draw.rect(
        surface,
        COLOR_PANEL_BORDER,
        pygame.Rect(tx, ty, tooltip_w, tooltip_h),
        1,
        border_radius=4,
    )

    # Text
    for i, line in enumerate(lines):
        text = font.render(line, True, COLOR_OVERLAY_TEXT)
        surface.blit(text, (tx + padding, ty + padding + i * line_height))


def run(
    on_generate,
    on_populate,
    on_grid_ready,
    on_start_set,
    on_goal_set,
    on_run,
    initial_width,
    initial_height,
):
    global INTERNAL_WIDTH, INTERNAL_HEIGHT
    pygame.init()

    is_fullscreen = False
    show_help = True  # Show on startup
    screen = pygame.display.set_mode(
        (INTERNAL_WIDTH, INTERNAL_HEIGHT), pygame.RESIZABLE
    )
    INTERNAL_WIDTH, INTERNAL_HEIGHT = screen.get_size()
    pygame.display.set_caption("A-Star Visualizer")

    internal_surface = pygame.Surface((INTERNAL_WIDTH, INTERNAL_HEIGHT))
    clock = pygame.time.Clock()

    fonts_dir = os.path.join(os.path.dirname(__file__), "font", "static")

    panel_font = pygame.font.Font(
        os.path.join(fonts_dir, "RobotoMono-Regular.ttf"), FONT_SIZE_MEDIUM
    )
    overlay_title_font = pygame.font.Font(
        os.path.join(fonts_dir, "RobotoMono-Bold.ttf"), FONT_SIZE_LARGE
    )
    overlay_key_font = pygame.font.Font(
        os.path.join(fonts_dir, "RobotoMono-Regular.ttf"), FONT_SIZE_MEDIUM
    )

    theme_data = {
        "defaults": {
            "font": {
                "name": "roboto",
                "size": str(FONT_SIZE_SMALL),
                "regular_path": os.path.join(fonts_dir, "RobotoMono-Regular.ttf"),
                "bold_path": os.path.join(fonts_dir, "RobotoMono-Bold.ttf"),
                "italic_path": os.path.join(fonts_dir, "RobotoMono-Italic.ttf"),
                "bold_italic_path": os.path.join(
                    fonts_dir, "RobotoMono-BoldItalic.ttf"
                ),
            }
        },
        "button": {
            "font": {
                "name": "roboto",
                "size": str(FONT_SIZE_SMALL),
            }
        },
        "label": {
            "font": {
                "name": "roboto",
                "size": str(FONT_SIZE_SMALL),
            }
        },
        "text_entry_line": {
            "font": {
                "name": "roboto",
                "size": str(FONT_SIZE_MEDIUM),
            },
            "misc": {"text_horiz_alignment": "centre"},
        },
        "drop_down_menu": {
            "font": {
                "name": "roboto",
                "size": str(FONT_SIZE_SMALL),
            }
        },
        "#drop_down_menu.#selected_option": {
            "font": {
                "name": "roboto",
                "size": str(FONT_SIZE_MEDIUM),
            }
        },
        "selection_list": {
            "font": {
                "name": "roboto",
                "size": str(FONT_SIZE_MEDIUM),
            },
            "misc": {"list_item_height": str(WIDGET_HEIGHT)},
        },
        "selection_list_item": {
            "font": {
                "name": "roboto",
                "size": str(FONT_SIZE_MEDIUM),
            }
        },
    }
    theme_path = os.path.join(os.path.dirname(__file__), "theme.json")
    with open(theme_path, "w") as f:
        json.dump(theme_data, f, indent=2)

    manager = pygame_gui.UIManager((INTERNAL_WIDTH, INTERNAL_HEIGHT), theme_path)

    camera = Camera(CANVAS_WIDTH, INTERNAL_HEIGHT)

    # --- Layout helpers ---
    padding = int(PADDING * 0.4)
    sidebar_x = CANVAS_WIDTH + PADDING
    widget_width = SIDEBAR_WIDTH - (PADDING * 2)
    label_width = LABEL_WIDTH
    input_x = sidebar_x + label_width + 5
    input_width = widget_width - label_width - 5
    row_stride = int(INTERNAL_HEIGHT * 0.038)

    # --- Grid panel ---
    grid_panel_top = int(INTERNAL_HEIGHT * 0.022)
    grid_panel_rect = pygame.Rect(
        CANVAS_WIDTH + int(SIDEBAR_WIDTH * 0.05),
        grid_panel_top,
        SIDEBAR_WIDTH - int(SIDEBAR_WIDTH * 0.1),
        row_stride * 4 + padding,
    )

    # Width row
    pygame_gui.elements.UILabel(
        relative_rect=pygame.Rect(
            sidebar_x,
            grid_panel_top + padding,
            label_width,
            WIDGET_HEIGHT,
        ),
        text="Width:",
        manager=manager,
    )
    width_input = pygame_gui.elements.UITextEntryLine(
        relative_rect=pygame.Rect(
            input_x,
            grid_panel_top + padding,
            input_width,
            WIDGET_HEIGHT,
        ),
        manager=manager,
    )
    width_input.set_text(str(initial_width))
    width_input.set_allowed_characters("numbers")

    # Height row
    pygame_gui.elements.UILabel(
        relative_rect=pygame.Rect(
            sidebar_x, grid_panel_top + row_stride + padding, label_width, WIDGET_HEIGHT
        ),
        text="Height:",
        manager=manager,
    )
    height_input = pygame_gui.elements.UITextEntryLine(
        relative_rect=pygame.Rect(
            input_x, grid_panel_top + row_stride + padding, input_width, WIDGET_HEIGHT
        ),
        manager=manager,
    )
    height_input.set_text(str(initial_height))
    height_input.set_allowed_characters("numbers")

    # Shape row
    pygame_gui.elements.UILabel(
        relative_rect=pygame.Rect(
            sidebar_x,
            grid_panel_top + row_stride * 2 + padding,
            label_width,
            WIDGET_HEIGHT,
        ),
        text="Shape:",
        manager=manager,
    )
    shape_dropdown = pygame_gui.elements.UIDropDownMenu(
        options_list=["Square", "Hexagon", "Triangle"],
        starting_option="Square",
        relative_rect=pygame.Rect(
            input_x,
            grid_panel_top + row_stride * 2 + padding,
            input_width,
            WIDGET_HEIGHT,
        ),
        manager=manager,
    )

    # Generate button
    generate_button = pygame_gui.elements.UIButton(
        relative_rect=pygame.Rect(
            sidebar_x,
            grid_panel_top + row_stride * 3 + padding,
            widget_width,
            WIDGET_HEIGHT,
        ),
        text="Generate",
        manager=manager,
    )

    # --- Terrain panel ---
    terrain_panel_top = grid_panel_top + int(row_stride * 4.25 + 1.5 * padding)
    terrain_panel_rect = pygame.Rect(
        CANVAS_WIDTH + int(SIDEBAR_WIDTH * 0.05),
        terrain_panel_top,
        SIDEBAR_WIDTH - int(SIDEBAR_WIDTH * 0.1),
        row_stride * 3 + padding,
    )

    # Biome row
    pygame_gui.elements.UILabel(
        relative_rect=pygame.Rect(
            sidebar_x, terrain_panel_top + padding, label_width, WIDGET_HEIGHT
        ),
        text="Biome:",
        manager=manager,
    )
    biome_dropdown = pygame_gui.elements.UIDropDownMenu(
        options_list=[BIOME_NAMES[b] for b in Biome],
        starting_option=BIOME_NAMES[Biome.PLAINS],
        relative_rect=pygame.Rect(
            input_x, terrain_panel_top + padding, input_width, WIDGET_HEIGHT
        ),
        manager=manager,
    )

    # Seed row
    pygame_gui.elements.UILabel(
        relative_rect=pygame.Rect(
            sidebar_x,
            terrain_panel_top + row_stride + padding,
            label_width,
            WIDGET_HEIGHT,
        ),
        text="Seed:",
        manager=manager,
    )
    seed_input = pygame_gui.elements.UITextEntryLine(
        relative_rect=pygame.Rect(
            input_x,
            terrain_panel_top + row_stride + padding,
            input_width,
            WIDGET_HEIGHT,
        ),
        manager=manager,
    )
    seed_input.set_text("42")
    seed_input.set_allowed_characters("numbers")

    # Populate button
    populate_button = pygame_gui.elements.UIButton(
        relative_rect=pygame.Rect(
            sidebar_x,
            terrain_panel_top + row_stride * 2 + padding,
            widget_width,
            WIDGET_HEIGHT,
        ),
        text="Populate",
        manager=manager,
    )

    # --- Setup panel ---
    setup_panel_top = terrain_panel_top + int(row_stride * 3.25 + 1.8 * padding)
    setup_panel_rect = pygame.Rect(
        CANVAS_WIDTH + int(SIDEBAR_WIDTH * 0.05),
        setup_panel_top,
        SIDEBAR_WIDTH - int(SIDEBAR_WIDTH * 0.1),
        row_stride * 2 + padding,
    )

    # Set Start row
    set_start_button = pygame_gui.elements.UIButton(
        relative_rect=pygame.Rect(
            sidebar_x, setup_panel_top + padding, widget_width, WIDGET_HEIGHT
        ),
        text="Set Start",
        manager=manager,
    )

    # Set Goal row
    set_goal_button = pygame_gui.elements.UIButton(
        relative_rect=pygame.Rect(
            sidebar_x,
            setup_panel_top + row_stride + padding,
            widget_width,
            WIDGET_HEIGHT,
        ),
        text="Set Goal",
        manager=manager,
    )

    # --- Algorithm panel ---
    algorithm_panel_top = setup_panel_top + int(row_stride * 2.25 + 2 * padding)
    algorithm_panel_rect = pygame.Rect(
        CANVAS_WIDTH + int(SIDEBAR_WIDTH * 0.05),
        algorithm_panel_top,
        SIDEBAR_WIDTH - int(SIDEBAR_WIDTH * 0.1),
        row_stride * 2 + padding + WIDGET_HEIGHT,
    )

    # Algorithm dropdown
    pygame_gui.elements.UILabel(
        relative_rect=pygame.Rect(
            sidebar_x, algorithm_panel_top + padding, label_width, WIDGET_HEIGHT
        ),
        text="Algorithm:",
        manager=manager,
    )
    algorithm_dropdown = pygame_gui.elements.UIDropDownMenu(
        options_list=ALGORITHMS,
        starting_option="A*",
        relative_rect=pygame.Rect(
            input_x, algorithm_panel_top + padding, input_width, WIDGET_HEIGHT
        ),
        manager=manager,
    )

    # Heuristic dropdown
    pygame_gui.elements.UILabel(
        relative_rect=pygame.Rect(
            sidebar_x,
            algorithm_panel_top + row_stride + padding,
            widget_width,
            WIDGET_HEIGHT,
        ),
        text="Heuristic:",
        manager=manager,
    )
    heuristic_dropdown = pygame_gui.elements.UIDropDownMenu(
        options_list=list(HEURISTICS.keys()),
        starting_option="Euclidean",
        relative_rect=pygame.Rect(
            sidebar_x,
            algorithm_panel_top + row_stride + padding + WIDGET_HEIGHT,
            widget_width,
            WIDGET_HEIGHT,
        ),
        manager=manager,
    )

    # --- Control panel ---
    control_panel_top = (
        algorithm_panel_top + int(row_stride * 2.25) + 2 * padding + WIDGET_HEIGHT
    )
    control_panel_rect = pygame.Rect(
        CANVAS_WIDTH + int(SIDEBAR_WIDTH * 0.05),
        control_panel_top,
        SIDEBAR_WIDTH - int(SIDEBAR_WIDTH * 0.1),
        row_stride * 4 + padding + WIDGET_HEIGHT,
    )

    # Speed slider
    pygame_gui.elements.UILabel(
        relative_rect=pygame.Rect(
            sidebar_x,
            control_panel_top + padding,
            label_width + int(input_width / 2),
            WIDGET_HEIGHT,
        ),
        text="Speed(tiles/sec):",
        manager=manager,
    )
    speed_label = pygame_gui.elements.UILabel(
        relative_rect=pygame.Rect(
            input_x + int(input_width / 2),
            control_panel_top + padding,
            input_width - int(input_width / 2),
            WIDGET_HEIGHT,
        ),
        text="5",
        manager=manager,
    )
    speed_slider = pygame_gui.elements.UIHorizontalSlider(
        relative_rect=pygame.Rect(
            sidebar_x,
            control_panel_top + padding + WIDGET_HEIGHT,
            widget_width,
            WIDGET_HEIGHT,
        ),
        start_value=5,
        value_range=(1, 500),
        manager=manager,
    )

    # Instant toggle button
    instant_button = pygame_gui.elements.UIButton(
        relative_rect=pygame.Rect(
            sidebar_x,
            control_panel_top + row_stride + padding + WIDGET_HEIGHT,
            widget_width,
            WIDGET_HEIGHT,
        ),
        text="Mode: Stepped",
        manager=manager,
    )

    # Flood fill checkbox
    flood_fill_checkbox = pygame_gui.elements.UICheckBox(
        relative_rect=pygame.Rect(
            sidebar_x,
            control_panel_top + row_stride * 2 + padding + WIDGET_HEIGHT,
            WIDGET_HEIGHT,
            WIDGET_HEIGHT,
        ),
        text="Run Flood Fill",
        manager=manager,
    )

    # Run button
    run_button = pygame_gui.elements.UIButton(
        relative_rect=pygame.Rect(
            sidebar_x,
            control_panel_top + row_stride * 3 + padding + WIDGET_HEIGHT,
            int(widget_width / 2 - padding),
            WIDGET_HEIGHT,
        ),
        text="Run",
        manager=manager,
    )

    # Replay button
    replay_button = pygame_gui.elements.UIButton(
        relative_rect=pygame.Rect(
            sidebar_x + int(widget_width / 2 - padding) + 2 * padding,
            control_panel_top + row_stride * 3 + padding + WIDGET_HEIGHT,
            int(widget_width / 2 - padding),
            WIDGET_HEIGHT,
        ),
        text="Replay",
        manager=manager,
    )

    # --- Bottom buttons ---
    # Help button
    help_button = pygame_gui.elements.UIButton(
        relative_rect=pygame.Rect(
            sidebar_x,
            INTERNAL_HEIGHT - (2 * WIDGET_HEIGHT + padding),
            widget_width,
            WIDGET_HEIGHT,
        ),
        text="? Help",
        manager=manager,
    )

    # Exit button
    exit_button = pygame_gui.elements.UIButton(
        relative_rect=pygame.Rect(
            sidebar_x,
            INTERNAL_HEIGHT - (WIDGET_HEIGHT + padding),
            widget_width,
            WIDGET_HEIGHT,
        ),
        text="End Script",
        manager=manager,
    )

    # Close help button — only visible when help is shown
    close_help_button = pygame_gui.elements.UIButton(
        relative_rect=pygame.Rect(0, 0, int(SIDEBAR_WIDTH * 0.5), WIDGET_HEIGHT),
        text="Close",
        manager=manager,
        visible=show_help,
    )

    # --- Flash state ---
    flash_timers = {"width": 0.0, "height": 0.0, "seed": 0.0}
    FLASH_DURATION = 0.5

    # --- Pulse state ---
    pulse_timer = 0.0

    # --- Grid and terrain state ---
    current_grid = None
    current_shape = Shape.SQUARE
    terrain_map: dict[tuple[int, int], TerrainType] = {}

    # --- Biome state ---
    valid_start_terrains: frozenset[TerrainType] = frozenset()
    biome_modifier: float = 1.0

    # --- Pathfinding state ---
    # None = no mode, "start" = placing start, "goal" = placing goal
    placement_mode: str | None = None
    start_node: Node | None = None
    goal_node: Node | None = None

    # --- Tooltip state ---
    tooltip_node: Node | None = None

    # --- Search result state ---
    search_result: SearchResult | None = None
    visited_index: int = 0
    step_timer: float = 0.0
    visualization_done: bool = False

    # --- Visualization state ---
    instant_mode: bool = False
    active_popup: Popup | None = None

    # --- Result state ---
    current_algorithm_name: str = "A*"
    current_heuristic_name: str = "Euclidean"
    results_history: list[dict] = []
    HEURISTIC_SHORTHAND: dict[str, str] = {
        "Euclidean": "Euc",
        "Euclidean Squared": "Euc²",
        "Euclidean Sqrt": "√Euc",
        "Euclidean Log": "logEuc",
        "Manhattan": "Man",
        "Weighted Euclidean x2": "2×Euc",
    }

    def show_flood_fill_popup(result: SearchResult):
        nonlocal active_popup
        title = "Goal Reachable" if result.success else "Goal Unreachable"
        lines = [
            f"Nodes explored:  {len(result.visited)}",
        ]
        if not result.success:
            lines.append("No path exists from start to goal.")
        active_popup = Popup(
            manager=manager,
            title=title,
            lines=lines,
            success=result.success,
            canvas_width=CANVAS_WIDTH,
            internal_width=INTERNAL_WIDTH,
            internal_height=INTERNAL_HEIGHT,
            widget_height=WIDGET_HEIGHT,
            font=overlay_key_font,
            title_font=overlay_title_font,
        )

    def show_search_popup(result: SearchResult, runtime: float):
        nonlocal active_popup
        if active_popup is not None:
            active_popup.dismiss()
        title = "Goal Reached" if result.success else "Search Unsuccessful"
        lines = [
            f"Nodes explored:  {len(result.visited)}",
            f"Runtime:         {runtime:.4f}s",
        ]
        if result.success:
            lines.insert(1, f"Path cost:       {result.cost:.2f}")
        else:
            lines.append("No valid path found.")
        active_popup = Popup(
            manager=manager,
            title=title,
            lines=lines,
            success=result.success,
            canvas_width=CANVAS_WIDTH,
            internal_width=INTERNAL_WIDTH,
            internal_height=INTERNAL_HEIGHT,
            widget_height=WIDGET_HEIGHT,
            font=overlay_key_font,
            title_font=overlay_title_font,
        )

    def draw_results_table(surface: pygame.Surface, font: pygame.font.Font):
        if not results_history:
            return

        col_widths = [
            int(CANVAS_WIDTH * 0.05),  # Algorithm
            int(CANVAS_WIDTH * 0.05),  # Heuristic
            int(CANVAS_WIDTH * 0.05),  # Explored
            int(CANVAS_WIDTH * 0.05),  # Cost
            int(CANVAS_WIDTH * 0.05),  # Runtime
        ]
        headers = ["Algorithm", "Heuristic", "Explored", "Cost", "Runtime"]

        row_h = font.get_height() + int(INTERNAL_HEIGHT * 0.008)
        padding = int(INTERNAL_HEIGHT * 0.012)
        table_w = sum(col_widths) + padding * 2
        table_h = row_h * (len(results_history) + 1) + padding * 2  # +1 for header

        # Position — lower left of canvas
        table_x = int(CANVAS_WIDTH * 0.01)
        table_y = INTERNAL_HEIGHT - table_h - int(INTERNAL_HEIGHT * 0.01)

        # Background
        pygame.draw.rect(
            surface,
            (15, 15, 15),
            pygame.Rect(table_x, table_y, table_w, table_h),
            border_radius=6,
        )
        pygame.draw.rect(
            surface,
            COLOR_PANEL_BORDER,
            pygame.Rect(table_x, table_y, table_w, table_h),
            1,
            border_radius=6,
        )

        # Headers
        x = table_x + padding
        y = table_y + padding
        for i, header in enumerate(headers):
            text = font.render(header, True, (180, 180, 180))
            surface.blit(text, (x, y))
            x += col_widths[i]

        # Divider under headers
        pygame.draw.line(
            surface,
            COLOR_PANEL_BORDER,
            (table_x + padding, y + row_h),
            (table_x + table_w - padding, y + row_h),
            1,
        )

        # Rows
        for row_i, entry in enumerate(results_history):
            x = table_x + padding
            y = table_y + padding + row_h * (row_i + 1) + int(INTERNAL_HEIGHT * 0.005)
            row_color = (
                (220, 200, 80) if row_i == len(results_history) - 1 else (140, 140, 140)
            )

            values = [
                entry["algorithm"],
                entry["heuristic"],
                str(entry["explored"]),
                f"{entry['cost']:.2f}",
                f"{entry['runtime']:.4f}s",
            ]
            for i, val in enumerate(values):
                text = font.render(val, True, row_color)
                surface.blit(text, (x, y))
                x += col_widths[i]

    def reset_pathfinding():
        nonlocal placement_mode, start_node, goal_node
        placement_mode = None
        start_node = None
        goal_node = None

    def set_grid(grid):
        nonlocal \
            current_grid, \
            current_shape, \
            search_result, \
            visited_index, \
            visualization_done
        current_grid = grid
        current_shape = grid.shape
        reset_pathfinding()

        all_wx = [n.world_position.x for n in grid.all_nodes()]
        all_wy = [n.world_position.y for n in grid.all_nodes()]
        world_w = max(all_wx) - min(all_wx) + 1
        world_h = max(all_wy) - min(all_wy) + 1

        padding_factor = 0.85
        scale_x = (CANVAS_WIDTH * padding_factor) / world_w
        scale_y = (INTERNAL_HEIGHT * padding_factor) / world_h
        camera.scale = min(scale_x, scale_y)

        grid_pixel_w = world_w * camera.scale
        grid_pixel_h = world_h * camera.scale
        camera.center_on_grid(grid_pixel_w, grid_pixel_h)
        search_result = None
        visited_index = 0
        visualization_done = False

    def set_terrain(new_terrain_map, new_valid_starts, new_modifier):
        nonlocal \
            terrain_map, \
            valid_start_terrains, \
            biome_modifier, \
            search_result, \
            visited_index, \
            visualization_done
        terrain_map = new_terrain_map
        valid_start_terrains = new_valid_starts
        biome_modifier = new_modifier
        reset_pathfinding()
        search_result = None
        visited_index = 0
        visualization_done = False

    def set_result(result: SearchResult, runtime: float):
        nonlocal search_result, visited_index, step_timer, visualization_done
        search_result = result
        visited_index = 0
        step_timer = 0.0
        visualization_done = False
        show_search_popup(result, runtime)

        # Only add successful runs to the results table
        if not result.success:
            return

        # Add to results history
        algorithm_name = current_algorithm_name
        heuristic_name = current_heuristic_name
        results_history.append(
            {
                "algorithm": algorithm_name,
                "heuristic": HEURISTIC_SHORTHAND.get(heuristic_name, "-")
                if algorithm_name in {"Greedy", "A*"}
                else "-",
                "explored": len(result.visited),
                "cost": result.cost,
                "runtime": runtime,
            }
        )
        if len(results_history) > 7:
            results_history.pop(0)

    def set_flood_fill_result(result: SearchResult):
        show_flood_fill_popup(result)
        # Also visualize the flood fill
        nonlocal search_result, visited_index, step_timer, visualization_done
        search_result = result
        visited_index = 0
        step_timer = 0.0
        visualization_done = False

    def set_start(node: Node):
        nonlocal start_node
        start_node = node

    def set_goal(node: Node):
        nonlocal goal_node
        goal_node = node

    def set_error(message: str):
        nonlocal active_popup
        if active_popup is not None:
            active_popup.dismiss()
        active_popup = Popup(
            manager=manager,
            title="Cannot Run",
            lines=[message],
            success=False,
            canvas_width=CANVAS_WIDTH,
            internal_width=INTERNAL_WIDTH,
            internal_height=INTERNAL_HEIGHT,
            widget_height=WIDGET_HEIGHT,
            font=overlay_key_font,
            title_font=overlay_title_font,
        )

    def dismiss_popup():
        nonlocal active_popup
        if active_popup is not None:
            active_popup.dismiss()
            active_popup = None

    def validate_and_generate():
        width_str = width_input.get_text()
        height_str = height_input.get_text()

        width_ok = True
        height_ok = True

        width = int(width_str) if width_str else 0
        if width < MIN_WIDTH:
            width_ok = False
            flash_timers["width"] = FLASH_DURATION
            width_input.set_text(str(MIN_WIDTH))
        elif width > MAX_SIZE:
            width_ok = False
            flash_timers["width"] = FLASH_DURATION
            width_input.set_text(str(MAX_SIZE))

        height = int(height_str) if height_str else 0
        if height < MIN_HEIGHT:
            height_ok = False
            flash_timers["height"] = FLASH_DURATION
            height_input.set_text(str(MIN_HEIGHT))
        elif height > MAX_SIZE:
            height_ok = False
            flash_timers["height"] = FLASH_DURATION
            height_input.set_text(str(MAX_SIZE))

        if width_ok and height_ok:
            shape_name = shape_dropdown.selected_option[0]
            on_generate(width, height, shape_name)

    def validate_and_populate():
        seed_str = seed_input.get_text()
        seed = int(seed_str) if seed_str else 42
        biome_name = biome_dropdown.selected_option[0]
        biome = BIOME_BY_NAME[biome_name]
        on_populate(biome, seed)

    def is_valid_start(terrain: TerrainType) -> bool:
        return terrain in valid_start_terrains

    def is_valid_goal(terrain: TerrainType) -> bool:
        return terrain in VALID_GOAL_TERRAINS

    def get_node_at_screen(mx, my) -> Node | None:
        if current_grid is None:
            return None
        wx, wy = camera.screen_to_world(mx, my)
        closest = None
        closest_dist = math.inf
        for node in current_grid.all_nodes():
            dx = node.world_position.x - wx
            dy = node.world_position.y - wy
            dist = dx * dx + dy * dy
            if dist < closest_dist:
                closest_dist = dist
                closest = node
        if closest_dist > 1.0:
            return None
        return closest

    def handle_canvas_click(mx, my):
        nonlocal placement_mode, start_node, goal_node
        if placement_mode is None:
            return
        if not terrain_map:
            return

        node = get_node_at_screen(mx, my)
        if node is None:
            return

        coords = (node.grid_position.x, node.grid_position.y)
        terrain = terrain_map.get(coords)
        if terrain is None:
            return

        if placement_mode == "start" and is_valid_start(terrain):
            start_node = node
            placement_mode = None
            on_start_set(node)
        elif placement_mode == "goal" and is_valid_goal(terrain):
            goal_node = node
            placement_mode = None
            on_goal_set(node)

    def toggle_help():
        nonlocal show_help
        show_help = not show_help
        if show_help:
            close_help_button.show()
        else:
            close_help_button.hide()

    def is_on_canvas(mx, my):
        return mx < CANVAS_WIDTH

    def draw_grid(surface, pulse):
        if current_grid is None:
            return

        surface.set_clip(pygame.Rect(0, 0, CANVAS_WIDTH, INTERNAL_HEIGHT))

        # --- Pass 1: Draw all cell fills ---
        for node in current_grid.all_nodes():
            wx, wy = node.world_position.x, node.world_position.y
            sx, sy = camera.world_to_screen(wx, wy)
            coords = (node.grid_position.x, node.grid_position.y)
            terrain = terrain_map.get(coords)

            color = TERRAIN_COLORS[terrain] if terrain is not None else COLOR_NODE

            match current_shape:
                case Shape.SQUARE:
                    points = get_square_points(sx, sy, camera.scale)
                case Shape.HEXAGON:
                    points = get_hex_points(sx, sy, camera.scale)
                case Shape.TRIANGLE:
                    pointing_up = (node.grid_position.x + node.grid_position.y) % 2 == 1
                    points = get_triangle_points(sx, sy, camera.scale, pointing_up)
                case _:
                    continue

            points = [(int(x), int(y)) for x, y in points]

            if placement_mode is not None and terrain is not None:
                valid = (
                    is_valid_start(terrain)
                    if placement_mode == "start"
                    else is_valid_goal(terrain)
                )
                if not valid:
                    color = tuple(max(0, int(c * 0.4)) for c in color)  # type: ignore

            pygame.draw.polygon(surface, color, points)

            if camera.scale > 15:
                pygame.draw.polygon(surface, COLOR_BACKGROUND, points, 1)

        # --- Pass 2: Draw all overlays ---
        for node in current_grid.all_nodes():
            wx, wy = node.world_position.x, node.world_position.y
            sx, sy = camera.world_to_screen(wx, wy)
            coords = (node.grid_position.x, node.grid_position.y)
            terrain = terrain_map.get(coords)

            match current_shape:
                case Shape.SQUARE:
                    points = get_square_points(sx, sy, camera.scale)
                case Shape.HEXAGON:
                    points = get_hex_points(sx, sy, camera.scale)
                case Shape.TRIANGLE:
                    pointing_up = (node.grid_position.x + node.grid_position.y) % 2 == 1
                    points = get_triangle_points(sx, sy, camera.scale, pointing_up)
                case _:
                    continue

            points = [(int(x), int(y)) for x, y in points]

            # Pulsating border for valid tiles in placement mode
            if placement_mode is not None and terrain is not None:
                valid = (
                    is_valid_start(terrain)
                    if placement_mode == "start"
                    else is_valid_goal(terrain)
                )
                if valid:
                    border_color = (
                        COLOR_START if placement_mode == "start" else COLOR_GOAL
                    )
                    brightness = 0.6 + pulse * 0.4
                    border_color = tuple(
                        min(255, int(c * brightness)) for c in border_color
                    )  # type: ignore
                    border_width = max(1, int(1 + pulse * 3))
                    pygame.draw.polygon(surface, border_color, points, border_width)

            # Confirmed start
            if node == start_node:
                line_w = max(2, int(camera.scale * 0.08))
                pygame.draw.polygon(surface, COLOR_START, points, line_w)
                cx = sum(p[0] for p in points) / len(points)
                cy = sum(p[1] for p in points) / len(points)
                draw_corner_lines(
                    surface, points, (cx, cy), COLOR_START, line_width=line_w
                )

            # Confirmed goal
            if node == goal_node:
                line_w = max(2, int(camera.scale * 0.08))
                pygame.draw.polygon(surface, COLOR_GOAL, points, line_w)
                cx = sum(p[0] for p in points) / len(points)
                cy = sum(p[1] for p in points) / len(points)
                draw_corner_lines(
                    surface, points, (cx, cy), COLOR_GOAL, line_width=line_w
                )

        # --- Pass 3: Draw search visualization ---
        if search_result is not None:
            # Draw visited rings
            for i in range(visited_index):
                node = search_result.visited[i]
                wx, wy = node.world_position.x, node.world_position.y
                sx, sy = camera.world_to_screen(wx, wy)
                cx, cy = int(sx), int(sy)

                match current_shape:
                    case Shape.SQUARE:
                        ring_outer = max(3, int(camera.scale * 0.40))
                        ring_width = max(1, int(camera.scale * 0.16))
                    case Shape.HEXAGON:
                        ring_outer = max(3, int(camera.scale * 0.65))
                        ring_width = max(1, int(camera.scale * 0.20))
                    case Shape.TRIANGLE:
                        ring_outer = max(3, int(camera.scale * 0.25))
                        ring_width = max(1, int(camera.scale * 0.09))
                    case _:
                        ring_outer = max(3, int(camera.scale * 0.30))
                        ring_width = max(1, int(camera.scale * 0.08))

                is_frontier = i == visited_index - 1

                if is_frontier:
                    glow_outer = ring_outer + int(pulse * ring_outer * 0.3)
                    glow_color = (
                        min(255, int(180 * (0.6 + pulse * 0.4))),
                        min(255, int(80 * (0.6 + pulse * 0.4))),
                        min(255, int(220 * (0.6 + pulse * 0.4))),
                    )
                    pygame.draw.circle(
                        surface, glow_color, (cx, cy), glow_outer, ring_width + 1
                    )
                else:
                    pygame.draw.circle(
                        surface, (140, 80, 180), (cx, cy), ring_outer, ring_width
                    )

            # Draw path once visualization is done
            if (
                visualization_done
                and search_result.success
                and len(search_result.path) > 1
            ):
                path = search_result.path
                for i in range(len(path) - 1):
                    a = path[i]
                    b = path[i + 1]
                    ax, ay = camera.world_to_screen(
                        a.world_position.x, a.world_position.y
                    )
                    bx, by = camera.world_to_screen(
                        b.world_position.x, b.world_position.y
                    )

                    # Draw line
                    line_width = max(2, int(camera.scale * 0.12))
                    pygame.draw.line(
                        surface,
                        (0, 220, 220),
                        (int(ax), int(ay)),
                        (int(bx), int(by)),
                        line_width,
                    )

                    # Draw arrowhead at midpoint
                    mx = (ax + bx) / 2
                    my = (ay + by) / 2
                    dx = bx - ax
                    dy = by - ay
                    length = sqrt(dx * dx + dy * dy)
                    if length > 0:
                        dx /= length
                        dy /= length
                        arrow_size = max(8, int(camera.scale * 0.4))
                        # Arrowhead points
                        tip = (int(mx + dx * arrow_size), int(my + dy * arrow_size))
                        left = (
                            int(mx - dy * arrow_size * 0.5 - dx * arrow_size * 0.5),
                            int(my + dx * arrow_size * 0.5 - dy * arrow_size * 0.5),
                        )
                        right = (
                            int(mx + dy * arrow_size * 0.5 - dx * arrow_size * 0.5),
                            int(my - dx * arrow_size * 0.5 - dy * arrow_size * 0.5),
                        )
                        pygame.draw.polygon(surface, (0, 220, 220), [tip, left, right])

        surface.set_clip(None)

    def scale_event(event):
        screen_w, screen_h = screen.get_size()
        sx = INTERNAL_WIDTH / screen_w
        sy = INTERNAL_HEIGHT / screen_h
        if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            scaled_event = pygame.event.Event(
                event.type,
                {
                    **event.__dict__,
                    "pos": (int(event.pos[0] * sx), int(event.pos[1] * sy)),
                },
            )
            return scaled_event
        if event.type == pygame.MOUSEMOTION:
            scaled_event = pygame.event.Event(
                event.type,
                {
                    **event.__dict__,
                    "pos": (int(event.pos[0] * sx), int(event.pos[1] * sy)),
                    "rel": (int(event.rel[0] * sx), int(event.rel[1] * sy)),
                },
            )
            return scaled_event
        return event

    def get_scaled_mouse_pos():
        raw = _original_get_pos()
        screen_w, screen_h = screen.get_size()
        return (
            int(raw[0] * INTERNAL_WIDTH / screen_w),
            int(raw[1] * INTERNAL_HEIGHT / screen_h),
        )

    on_grid_ready(
        set_grid,
        set_terrain,
        set_result,
        set_flood_fill_result,
        set_error,
        set_start,
        set_goal,
    )
    _original_get_pos = pygame.mouse.get_pos
    pygame.mouse.get_pos = get_scaled_mouse_pos  # type: ignore

    running = True
    while running:
        time_delta = clock.tick(60) / 1000.0
        pulse_timer = (pulse_timer + time_delta) % MAX_PULSE_TIMER
        pulse = (math.sin(pulse_timer * 3.0) + 1) / 2

        raw_mouse = pygame.mouse.get_pos()
        screen_w, screen_h = screen.get_size()
        scale_x = INTERNAL_WIDTH / screen_w
        scale_y = INTERNAL_HEIGHT / screen_h
        mouse_x = raw_mouse[0] * scale_x
        mouse_y = raw_mouse[1] * scale_y

        if search_result is not None and not visualization_done:
            if instant_mode:
                visited_index = len(search_result.visited)
                visualization_done = True
            else:
                steps_per_second = speed_slider.get_current_value()
                step_timer += time_delta
                steps = int(step_timer * steps_per_second)
                if steps > 0:
                    visited_index = min(
                        visited_index + steps, len(search_result.visited)
                    )
                    step_timer -= steps / steps_per_second
                    if visited_index >= len(search_result.visited):
                        visualization_done = True

        if is_on_canvas(mouse_x, mouse_y) and not show_help:
            tooltip_node = get_node_at_screen(mouse_x, mouse_y)
        else:
            tooltip_node = None

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_f:
                    is_fullscreen = not is_fullscreen
                    if is_fullscreen:
                        monitor_size = pygame.display.get_desktop_sizes()[0]
                        screen = pygame.display.set_mode(monitor_size, pygame.NOFRAME)
                    else:
                        screen = pygame.display.set_mode(
                            (INTERNAL_WIDTH, INTERNAL_HEIGHT), pygame.RESIZABLE
                        )
                if event.key == pygame.K_h:
                    toggle_help()
                if event.key == pygame.K_r and not show_help:
                    if search_result is not None:
                        visited_index = 0
                        visualization_done = False
                        step_timer = 0.0
                if event.key == pygame.K_SPACE and not show_help:
                    current_algorithm_name = algorithm_dropdown.selected_option[0]
                    current_heuristic_name = heuristic_dropdown.selected_option[0]
                    run_flood_fill = flood_fill_checkbox.is_checked
                    dismiss_popup()
                    on_run(
                        current_algorithm_name, current_heuristic_name, run_flood_fill
                    )
                if event.key == pygame.K_s and not show_help:
                    if placement_mode == "start":
                        placement_mode = None
                        start_node = None
                    else:
                        placement_mode = "start"
                    results_history.clear()
                    search_result = None
                    visited_index = 0
                    visualization_done = False
                if event.key == pygame.K_g and not show_help:
                    if placement_mode == "goal":
                        placement_mode = None
                        goal_node = None
                    else:
                        placement_mode = "goal"
                    results_history.clear()
                    search_result = None
                    visited_index = 0
                    visualization_done = False

            if not show_help:
                if event.type == pygame.MOUSEWHEEL and is_on_canvas(mouse_x, mouse_y):
                    if event.y > 0:
                        camera.zoom(ZOOM_IN_FACTOR, mouse_x, mouse_y)
                    elif event.y < 0:
                        camera.zoom(ZOOM_OUT_FACTOR, mouse_x, mouse_y)

                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button in (2, 3) and is_on_canvas(mouse_x, mouse_y):
                        camera.start_pan(mouse_x, mouse_y)
                    if event.button == 1 and is_on_canvas(mouse_x, mouse_y):
                        handle_canvas_click(mouse_x, mouse_y)

                if event.type == pygame.MOUSEMOTION:
                    camera.update_pan(mouse_x, mouse_y)

                if event.type == pygame.MOUSEBUTTONUP:
                    if event.button in (2, 3):
                        camera.end_pan()

            if event.type == pygame_gui.UI_BUTTON_PRESSED:
                if event.ui_element == exit_button:
                    running = False
                if event.ui_element == generate_button:
                    dismiss_popup()
                    validate_and_generate()
                    results_history.clear()
                if event.ui_element == populate_button:
                    dismiss_popup()
                    validate_and_populate()
                    results_history.clear()
                if event.ui_element == help_button:
                    toggle_help()
                if event.ui_element == close_help_button:
                    toggle_help()
                if event.ui_element == set_start_button:
                    dismiss_popup()
                    if placement_mode == "start":
                        placement_mode = None
                        start_node = None
                    else:
                        placement_mode = "start"
                    results_history.clear()
                    search_result = None
                    visited_index = 0
                    visualization_done = False
                if event.ui_element == set_goal_button:
                    dismiss_popup()
                    if placement_mode == "goal":
                        placement_mode = None
                        goal_node = None
                    else:
                        placement_mode = "goal"
                    results_history.clear()
                    search_result = None
                    visited_index = 0
                    visualization_done = False
                if event.ui_element == instant_button:
                    instant_mode = not instant_mode
                    instant_button.set_text(
                        "Mode: Instant" if instant_mode else "Mode: Stepped"
                    )
                if event.ui_element == run_button:
                    dismiss_popup()
                    current_algorithm_name = algorithm_dropdown.selected_option[0]
                    current_heuristic_name = heuristic_dropdown.selected_option[0]
                    run_flood_fill = flood_fill_checkbox.is_checked
                    on_run(
                        current_algorithm_name, current_heuristic_name, run_flood_fill
                    )
                if event.ui_element == replay_button:
                    if search_result is not None:
                        visited_index = 0
                        visualization_done = False
                        step_timer = 0.0

            if active_popup is not None:
                active_popup.handle_event(event)

            manager.process_events(scale_event(event))

        for key in flash_timers:
            if flash_timers[key] > 0:
                flash_timers[key] -= time_delta

        current_speed = int(speed_slider.get_current_value())
        speed_label.set_text(f"{current_speed}")

        manager.update(time_delta)

        # --- Draw ---
        internal_surface.fill(COLOR_BACKGROUND)

        pygame.draw.rect(
            internal_surface,
            COLOR_CANVAS,
            pygame.Rect(0, 0, CANVAS_WIDTH, INTERNAL_HEIGHT),
        )
        pygame.draw.rect(
            internal_surface,
            COLOR_SIDEBAR,
            pygame.Rect(CANVAS_WIDTH, 0, SIDEBAR_WIDTH, INTERNAL_HEIGHT),
        )
        pygame.draw.line(
            internal_surface,
            COLOR_DIVIDER,
            (CANVAS_WIDTH, 0),
            (CANVAS_WIDTH, INTERNAL_HEIGHT),
            2,
        )

        draw_panel(internal_surface, panel_font, "Grid", grid_panel_rect)
        draw_panel(internal_surface, panel_font, "Terrain", terrain_panel_rect)
        draw_panel(internal_surface, panel_font, "Setup", setup_panel_rect)
        draw_panel(internal_surface, panel_font, "Algorithm", algorithm_panel_rect)
        draw_panel(internal_surface, panel_font, "Control", control_panel_rect)
        draw_grid(internal_surface, pulse)
        draw_results_table(internal_surface, panel_font)

        if show_help:
            close_rect = draw_help_overlay(
                internal_surface, overlay_title_font, overlay_key_font, manager
            )
            close_help_button.set_position((close_rect.x, close_rect.y))

        if flash_timers["width"] > 0:
            pygame.draw.rect(
                internal_surface,
                (220, 60, 60),
                width_input.get_abs_rect(),
                2,
                border_radius=4,
            )
        if flash_timers["height"] > 0:
            pygame.draw.rect(
                internal_surface,
                (220, 60, 60),
                height_input.get_abs_rect(),
                2,
                border_radius=4,
            )

        if active_popup is not None and active_popup.visible:
            active_popup.draw(internal_surface)

        manager.draw_ui(internal_surface)

        if tooltip_node is not None:
            coords = (tooltip_node.grid_position.x, tooltip_node.grid_position.y)
            terrain = terrain_map.get(coords)
            draw_tooltip(
                internal_surface,
                overlay_key_font,
                tooltip_node,
                terrain,
                biome_modifier,
                mouse_x,
                mouse_y,
            )

        scaled = pygame.transform.smoothscale(internal_surface, screen.get_size())
        screen.blit(scaled, (0, 0))
        pygame.display.flip()

    pygame.quit()
