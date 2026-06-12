import pygame
import pygame_gui
from math import sqrt
from typing import Callable
from world_content.terrain import TerrainType, TERRAIN_COLORS
from world_content.biome import Biome, get_composition
from topology.grid import Shape


BUDGET = 100


def get_square_points(sx, sy, size):
    half = size / 2
    return [
        (sx - half, sy - half),
        (sx + half, sy - half),
        (sx + half, sy + half),
        (sx - half, sy + half),
    ]


def get_hex_points(sx, sy, size):
    r = size
    return [
        (sx + r, sy),
        (sx + r / 2, sy + r * sqrt(3) / 2),
        (sx - r / 2, sy + r * sqrt(3) / 2),
        (sx - r, sy),
        (sx - r / 2, sy - r * sqrt(3) / 2),
        (sx + r / 2, sy - r * sqrt(3) / 2),
    ]


def get_triangle_points(sx, sy, size, pointing_up=True):
    s = size
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


class CompositionEditor:
    def __init__(
        self,
        manager: pygame_gui.UIManager,
        biome: Biome,
        current_shape: Shape,
        canvas_width: int,
        internal_width: int,
        internal_height: int,
        widget_height: int,
        font: pygame.font.Font,
        title_font: pygame.font.Font,
        on_confirm: Callable[[dict[TerrainType, float]], None],
        current_composition: dict[TerrainType, float] | None = None,
    ):
        self.manager = manager
        self.biome = biome
        self.current_shape = current_shape
        self.canvas_width = canvas_width
        self.internal_width = internal_width
        self.internal_height = internal_height
        self.widget_height = widget_height
        self.font = font
        self.title_font = title_font
        self.on_confirm = on_confirm
        self.visible = True

        # Load biome composition as starting values scaled to budget
        base_composition = get_composition(biome)
        self.terrains = list(base_composition.keys())
        if current_composition is not None:
            self.values = {
                t: round(current_composition.get(t, 0) * BUDGET) for t in self.terrains
            }
        else:
            self.values = {t: round(v * BUDGET) for t, v in base_composition.items()}

        # Normalize to exactly BUDGET
        diff = BUDGET - sum(self.values.values())
        if diff != 0:
            self.values[self.terrains[0]] += diff

        # Layout
        padding = int(internal_height * 0.015)
        tile_size = widget_height
        row_h = widget_height + int(internal_height * 0.008)
        name_width = int(internal_width * 0.1)
        slider_width = int(internal_width * 0.2)
        value_width = int(internal_width * 0.03)

        self.overlay_w = (
            tile_size
            + padding
            + name_width
            + padding
            + slider_width
            + padding
            + value_width
            + padding * 2
        )
        self.overlay_h = (
            int(internal_height * 0.08)  # title + budget
            + len(self.terrains) * row_h
            + int(internal_height * 0.06)  # confirm button
            + padding * 2
        )
        self.overlay_x = (canvas_width - self.overlay_w) // 2
        self.overlay_y = (internal_height - self.overlay_h) // 2

        # Build sliders
        self.sliders: dict[TerrainType, pygame_gui.elements.UIHorizontalSlider] = {}
        self.value_labels: dict[TerrainType, pygame_gui.elements.UILabel] = {}

        entries_start_y = self.overlay_y + int(internal_height * 0.09)
        slider_x = self.overlay_x + padding + tile_size + padding + name_width + padding
        label_x = slider_x + slider_width + padding

        for i, terrain in enumerate(self.terrains):
            row_y = entries_start_y + i * row_h

            slider = pygame_gui.elements.UIHorizontalSlider(
                relative_rect=pygame.Rect(slider_x, row_y, slider_width, widget_height),
                start_value=self.values[terrain],
                value_range=(0, BUDGET),
                manager=manager,
            )
            self.sliders[terrain] = slider

            label = pygame_gui.elements.UILabel(
                relative_rect=pygame.Rect(label_x, row_y, value_width, widget_height),
                text=str(self.values[terrain]),
                manager=manager,
            )
            self.value_labels[terrain] = label

        # Confirm button
        confirm_w = int(self.overlay_w * 0.5)
        confirm_x = self.overlay_x + (self.overlay_w - confirm_w) // 2
        confirm_y = self.overlay_y + self.overlay_h - int(widget_height * 1.5)

        self.confirm_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(confirm_x, confirm_y, confirm_w, widget_height),
            text="Confirm & Populate",
            manager=manager,
        )

        # Store layout constants for drawing
        self.padding = padding
        self.tile_size = tile_size
        self.row_h = row_h
        self.name_width = name_width
        self.entries_start_y = entries_start_y

    @property
    def budget_used(self) -> int:
        return sum(self.values.values())

    @property
    def budget_remaining(self) -> int:
        return BUDGET - self.budget_used

    def handle_event(self, event) -> bool:
        if not self.visible:
            return False

        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.confirm_button:
                self._confirm()
                return True

        if event.type == pygame_gui.UI_HORIZONTAL_SLIDER_MOVED:
            for terrain, slider in self.sliders.items():
                if event.ui_element == slider:
                    self._on_slider_moved(terrain, int(slider.get_current_value()))
                    return True

        return False

    def _on_slider_moved(self, terrain: TerrainType, new_value: int):
        old_value = self.values[terrain]
        delta = new_value - old_value

        if delta > self.budget_remaining:
            # Clamp to available budget
            new_value = old_value + self.budget_remaining
            self.sliders[terrain].set_current_value(new_value)

        self.values[terrain] = new_value
        self.value_labels[terrain].set_text(str(new_value))

    def _confirm(self):
        # Convert integer values back to floats summing to 1.0
        total = sum(self.values.values())
        if total == 0:
            return
        composition = {t: v / total for t, v in self.values.items() if v > 0}
        self.on_confirm(composition)
        self.dismiss()

    def dismiss(self):
        self.visible = False
        for slider in self.sliders.values():
            slider.hide()
        for label in self.value_labels.values():
            label.hide()
        self.confirm_button.hide()

    def draw(self, surface: pygame.Surface):
        if not self.visible:
            return

        # Background
        pygame.draw.rect(
            surface,
            (15, 15, 15),
            pygame.Rect(self.overlay_x, self.overlay_y, self.overlay_w, self.overlay_h),
            border_radius=8,
        )
        pygame.draw.rect(
            surface,
            (80, 80, 85),
            pygame.Rect(self.overlay_x, self.overlay_y, self.overlay_w, self.overlay_h),
            2,
            border_radius=8,
        )

        # Title
        title_text = f"Edit Composition: {self.biome.name.capitalize()}"
        title_surf = self.title_font.render(title_text, True, (220, 220, 220))
        title_rect = title_surf.get_rect(
            centerx=self.overlay_x + self.overlay_w // 2,
            y=self.overlay_y + int(self.internal_height * 0.02),
        )
        surface.blit(title_surf, title_rect)

        # Budget bar
        budget_y = self.overlay_y + int(self.internal_height * 0.05)
        remaining = self.budget_remaining
        fraction = remaining / BUDGET

        # Budget color: green → yellow → red
        if fraction > 0.5:
            t = (fraction - 0.5) * 2
            color = (int(255 * (1 - t)), 200, 0)
        else:
            t = fraction * 2
            color = (200, int(200 * t), 0)

        budget_text = f"Budget: {remaining} / {BUDGET}"
        budget_surf = self.font.render(budget_text, True, color)
        surface.blit(budget_surf, (self.overlay_x + self.padding, budget_y))

        # Divider
        divider_y = self.overlay_y + int(self.internal_height * 0.075)
        pygame.draw.line(
            surface,
            (80, 80, 85),
            (self.overlay_x + int(self.overlay_w * 0.05), divider_y),
            (self.overlay_x + int(self.overlay_w * 0.95), divider_y),
            1,
        )

        # Terrain rows
        for i, terrain in enumerate(self.terrains):
            row_y = self.entries_start_y + i * self.row_h
            tile_x = self.overlay_x + self.padding + self.tile_size // 2
            tile_y = row_y + self.widget_height // 2

            # Draw terrain tile
            color = TERRAIN_COLORS.get(terrain, (100, 110, 130))
            tile_size = self.tile_size * 0.4

            match self.current_shape:
                case Shape.SQUARE:
                    points = get_square_points(tile_x, tile_y, tile_size)
                case Shape.HEXAGON:
                    points = get_hex_points(tile_x, tile_y, tile_size * 0.5)
                case Shape.TRIANGLE:
                    points = get_triangle_points(tile_x, tile_y, tile_size)
                case _:
                    points = get_square_points(tile_x, tile_y, tile_size)

            points = [(int(x), int(y)) for x, y in points]
            pygame.draw.polygon(surface, color, points)
            pygame.draw.polygon(surface, (80, 80, 85), points, 1)

            # Terrain name
            name = terrain.name.replace("_", " ").title()
            name_surf = self.font.render(name, True, (180, 180, 180))
            name_x = self.overlay_x + self.padding + self.tile_size + self.padding
            surface.blit(
                name_surf,
                (name_x, row_y + (self.widget_height - name_surf.get_height()) // 2),
            )
