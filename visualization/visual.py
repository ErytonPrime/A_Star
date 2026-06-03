import pygame
import pygame_gui
from typing import cast
from visualization.camera import Camera
from topology.grid import Shape
from math import sqrt
from world_content.terrain import TerrainType, TERRAIN_COLORS
from world_content.biome import Biome

terrain_map: dict[tuple[int, int], TerrainType] = {}

# Layout constants
INTERNAL_WIDTH = 1600
INTERNAL_HEIGHT = 900
SIDEBAR_WIDTH = 300
CANVAS_WIDTH = INTERNAL_WIDTH - SIDEBAR_WIDTH

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

# Grid input constraints
MIN_WIDTH = 2
MIN_HEIGHT = 1
MAX_SIZE = 999

# Zoom
ZOOM_IN_FACTOR = 1.1
ZOOM_OUT_FACTOR = 1 / ZOOM_IN_FACTOR

# Help content — add new controls here as the project grows
HELP_ENTRIES = [
    ("Scroll Wheel", "Zoom in / out"),
    ("Right / Middle Drag", "Pan the canvas"),
    ("F", "Toggle borderless fullscreen"),
    ("H", "Toggle this help menu"),
]

# Biome display names
BIOME_NAMES = {biome: biome.name.capitalize() for biome in Biome}
BIOME_BY_NAME = {v: k for k, v in BIOME_NAMES.items()}


def get_square_points(
    sx: float, sy: float, scale: float, gap: float
) -> list[tuple[float, float]]:
    s = scale - gap
    return [
        (sx, sy),
        (sx + s, sy),
        (sx + s, sy + s),
        (sx, sy + s),
    ]


def get_hex_points(
    sx: float, sy: float, scale: float, gap: float
) -> list[tuple[float, float]]:
    """Flat-top hexagon centered at (sx, sy)."""
    r = scale - gap
    return [
        (sx + r, sy),
        (sx + r / 2, sy + r * sqrt(3) / 2),
        (sx - r / 2, sy + r * sqrt(3) / 2),
        (sx - r, sy),
        (sx - r / 2, sy - r * sqrt(3) / 2),
        (sx + r / 2, sy - r * sqrt(3) / 2),
    ]


def get_triangle_points(
    sx: float, sy: float, scale: float, gap: float, pointing_up: bool
) -> list[tuple[float, float]]:
    """Equilateral triangle, pointing up or down."""
    s = scale - gap * 2
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


def draw_panel(surface, font, title, rect):
    pygame.draw.rect(surface, COLOR_PANEL_BORDER, rect, 1, border_radius=6)
    label = font.render(f" {title} ", True, COLOR_PANEL_LABEL, COLOR_SIDEBAR)
    surface.blit(label, (rect.x + 10, rect.y - 10))


def draw_help_overlay(surface, title_font, key_font, manager):
    overlay_w = 500
    row_h = 36
    overlay_h = 80 + len(HELP_ENTRIES) * row_h + 60
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
    title = title_font.render("Controls", True, COLOR_OVERLAY_TITLE)
    title_rect = title.get_rect(centerx=overlay_x + overlay_w // 2, y=overlay_y + 20)
    surface.blit(title, title_rect)

    # Divider
    pygame.draw.line(
        surface,
        COLOR_OVERLAY_BORDER,
        (overlay_x + 20, overlay_y + 52),
        (overlay_x + overlay_w - 20, overlay_y + 52),
        1,
    )

    # Entries
    for i, (key, description) in enumerate(HELP_ENTRIES):
        row_y = overlay_y + 64 + i * row_h
        key_label = key_font.render(key, True, COLOR_OVERLAY_KEY)
        desc_label = key_font.render(description, True, COLOR_OVERLAY_TEXT)
        surface.blit(key_label, (overlay_x + 24, row_y))
        surface.blit(desc_label, (overlay_x + 220, row_y))

    # Return close button rect so we can position it correctly
    close_y = overlay_y + overlay_h - 50
    close_x = overlay_x + (overlay_w - 120) // 2
    return pygame.Rect(close_x, close_y, 120, 35)


def run(on_generate, on_populate, on_grid_ready, initial_width, initial_height):
    pygame.init()

    is_fullscreen = False
    show_help = True  # Show on startup
    screen = pygame.display.set_mode(
        (INTERNAL_WIDTH, INTERNAL_HEIGHT), pygame.RESIZABLE
    )
    pygame.display.set_caption("A-Star Visualizer")

    internal_surface = pygame.Surface((INTERNAL_WIDTH, INTERNAL_HEIGHT))
    clock = pygame.time.Clock()

    panel_font = pygame.font.SysFont("segoeui", 15)
    overlay_title_font = pygame.font.SysFont("segoeui", 22, bold=True)
    overlay_key_font = pygame.font.SysFont("segoeui", 16)

    manager = pygame_gui.UIManager((INTERNAL_WIDTH, INTERNAL_HEIGHT))

    camera = Camera(CANVAS_WIDTH, INTERNAL_HEIGHT)

    # --- Layout helpers ---
    padding = 20
    sidebar_x = CANVAS_WIDTH + padding
    widget_width = SIDEBAR_WIDTH - (padding * 2)
    label_width = 80
    input_x = sidebar_x + label_width + 5
    input_width = widget_width - label_width - 5

    # --- Grid panel ---
    grid_panel_rect = pygame.Rect(CANVAS_WIDTH + 10, 20, SIDEBAR_WIDTH - 20, 195)

    # Width row
    pygame_gui.elements.UILabel(
        relative_rect=pygame.Rect(sidebar_x, 45, label_width, 30),
        text="Width:",
        manager=manager,
    )
    width_input = pygame_gui.elements.UITextEntryLine(
        relative_rect=pygame.Rect(input_x, 45, input_width, 30),
        manager=manager,
    )
    width_input.set_text(str(initial_width))
    width_input.set_allowed_characters("numbers")

    # Height row
    pygame_gui.elements.UILabel(
        relative_rect=pygame.Rect(sidebar_x, 90, label_width, 30),
        text="Height:",
        manager=manager,
    )
    height_input = pygame_gui.elements.UITextEntryLine(
        relative_rect=pygame.Rect(input_x, 90, input_width, 30),
        manager=manager,
    )
    height_input.set_text(str(initial_height))
    height_input.set_allowed_characters("numbers")

    # Shape row
    pygame_gui.elements.UILabel(
        relative_rect=pygame.Rect(sidebar_x, 135, label_width, 30),
        text="Shape:",
        manager=manager,
    )
    shape_dropdown = pygame_gui.elements.UIDropDownMenu(
        options_list=["Square", "Hexagon", "Triangle"],
        starting_option="Square",
        relative_rect=pygame.Rect(input_x, 135, input_width, 30),
        manager=manager,
    )

    # Generate button
    generate_button = pygame_gui.elements.UIButton(
        relative_rect=pygame.Rect(sidebar_x, 180, widget_width, 35),
        text="Generate Grid",
        manager=manager,
    )

    # --- Terrain panel ---
    terrain_panel_top = 235
    terrain_panel_rect = pygame.Rect(
        CANVAS_WIDTH + 10, terrain_panel_top, SIDEBAR_WIDTH - 20, 185
    )

    pygame_gui.elements.UILabel(
        relative_rect=pygame.Rect(sidebar_x, terrain_panel_top + 25, label_width, 30),
        text="Biome:",
        manager=manager,
    )
    biome_dropdown = pygame_gui.elements.UIDropDownMenu(
        options_list=[BIOME_NAMES[b] for b in Biome],
        starting_option=BIOME_NAMES[Biome.PLAINS],
        relative_rect=pygame.Rect(input_x, terrain_panel_top + 25, input_width, 30),
        manager=manager,
    )

    pygame_gui.elements.UILabel(
        relative_rect=pygame.Rect(sidebar_x, terrain_panel_top + 65, label_width, 30),
        text="Seed:",
        manager=manager,
    )
    seed_input = pygame_gui.elements.UITextEntryLine(
        relative_rect=pygame.Rect(input_x, terrain_panel_top + 65, input_width, 30),
        manager=manager,
    )
    seed_input.set_text("42")
    seed_input.set_allowed_characters("numbers")

    populate_button = pygame_gui.elements.UIButton(
        relative_rect=pygame.Rect(sidebar_x, terrain_panel_top + 105, widget_width, 35),
        text="Populate Grid",
        manager=manager,
    )

    # --- Bottom buttons ---
    # Help button
    help_button = pygame_gui.elements.UIButton(
        relative_rect=pygame.Rect(sidebar_x, INTERNAL_HEIGHT - 110, widget_width, 40),
        text="? Help",
        manager=manager,
    )

    # Exit button
    exit_button = pygame_gui.elements.UIButton(
        relative_rect=pygame.Rect(sidebar_x, INTERNAL_HEIGHT - 60, widget_width, 40),
        text="End Script",
        manager=manager,
    )

    # Close help button — only visible when help is shown
    close_help_button = pygame_gui.elements.UIButton(
        relative_rect=pygame.Rect(0, 0, 120, 35),
        text="Close",
        manager=manager,
        visible=show_help,
    )

    # --- Flash state ---
    flash_timers = {"width": 0.0, "height": 0.0, "seed": 0.0}
    FLASH_DURATION = 0.5

    # --- Grid state ---
    current_grid = None
    current_shape = Shape.SQUARE
    terrain_map: dict[tuple[int, int], object] = {}

    def set_grid(grid):
        nonlocal current_grid, current_shape
        current_grid = grid
        current_shape = grid.shape

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

    def set_terrain(new_terrain_map):
        nonlocal terrain_map
        terrain_map = new_terrain_map

    on_grid_ready(set_grid, set_terrain)

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

    def toggle_help():
        nonlocal show_help
        show_help = not show_help
        if show_help:
            close_help_button.show()
        else:
            close_help_button.hide()

    def is_on_canvas(mx, my):
        return mx < CANVAS_WIDTH

    def draw_grid(surface):
        if current_grid is None:
            return

        surface.set_clip(pygame.Rect(0, 0, CANVAS_WIDTH, INTERNAL_HEIGHT))

        gap = max(1, camera.scale * 0.05)

        for node in current_grid.all_nodes():
            wx, wy = node.world_position.x, node.world_position.y
            sx, sy = camera.world_to_screen(wx, wy)

            coords = (node.grid_position.x, node.grid_position.y)
            terrain = terrain_map.get(coords)
            if terrain is not None:
                color = TERRAIN_COLORS[cast(TerrainType, terrain)]
            else:
                color = COLOR_NODE

            match current_shape:
                case Shape.SQUARE:
                    points = get_square_points(sx, sy, camera.scale, gap)

                case Shape.HEXAGON:
                    points = get_hex_points(sx, sy, camera.scale, gap)

                case Shape.TRIANGLE:
                    pointing_up = (node.grid_position.x + node.grid_position.y) % 2 == 1
                    points = get_triangle_points(sx, sy, camera.scale, gap, pointing_up)

                case _:
                    continue

            pygame.draw.polygon(surface, color, points)

        surface.set_clip(None)

    running = True
    while running:
        time_delta = clock.tick(60) / 1000.0

        raw_mouse = pygame.mouse.get_pos()
        screen_w, screen_h = screen.get_size()
        scale_x = INTERNAL_WIDTH / screen_w
        scale_y = INTERNAL_HEIGHT / screen_h
        mouse_x = raw_mouse[0] * scale_x
        mouse_y = raw_mouse[1] * scale_y

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

            if not show_help:
                if event.type == pygame.MOUSEWHEEL and is_on_canvas(mouse_x, mouse_y):
                    if event.y > 0:
                        camera.zoom(ZOOM_IN_FACTOR, mouse_x, mouse_y)
                    elif event.y < 0:
                        camera.zoom(ZOOM_OUT_FACTOR, mouse_x, mouse_y)

                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button in (2, 3) and is_on_canvas(mouse_x, mouse_y):
                        camera.start_pan(mouse_x, mouse_y)

                if event.type == pygame.MOUSEMOTION:
                    camera.update_pan(mouse_x, mouse_y)

                if event.type == pygame.MOUSEBUTTONUP:
                    if event.button in (2, 3):
                        camera.end_pan()

            if event.type == pygame_gui.UI_BUTTON_PRESSED:
                if event.ui_element == exit_button:
                    running = False
                if event.ui_element == generate_button:
                    validate_and_generate()
                if event.ui_element == populate_button:
                    validate_and_populate()
                if event.ui_element == help_button:
                    toggle_help()
                if event.ui_element == close_help_button:
                    toggle_help()

            manager.process_events(event)

        for key in flash_timers:
            if flash_timers[key] > 0:
                flash_timers[key] -= time_delta

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
        draw_grid(internal_surface)

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

        manager.draw_ui(internal_surface)

        scaled = pygame.transform.scale(internal_surface, screen.get_size())
        screen.blit(scaled, (0, 0))
        pygame.display.flip()

    pygame.quit()
