import pygame
import pygame_gui


class Popup:
    """A closable popup overlay for displaying search results."""

    def __init__(
        self,
        manager: pygame_gui.UIManager,
        title: str,
        lines: list[str],
        success: bool,
        canvas_width: int,
        internal_width: int,
        internal_height: int,
        widget_height: int,
        font: pygame.font.Font,
        title_font: pygame.font.Font,
    ):
        self.visible = True
        self.success = success
        self.font = font
        self.title_font = title_font
        self.lines = lines
        self.title = title
        self.canvas_width = canvas_width
        self.internal_width = internal_width
        self.internal_height = internal_height
        self.widget_height = widget_height

        # Layout
        self.overlay_w = int(internal_width * 0.18)
        self.line_height = font.get_height() + int(internal_height * 0.008)
        self.padding = int(internal_height * 0.02)
        self.overlay_h = (
            int(internal_height * 0.08)
            + len(lines) * self.line_height
            + int(internal_height * 0.06)
        )
        self.overlay_x = int(internal_width * 0.01)  # top left with small margin
        self.overlay_y = int(internal_height * 0.01)  # top with small margin

        # Close button
        close_w = int(self.overlay_w * 0.4)
        close_x = self.overlay_x + (self.overlay_w - close_w) // 2
        close_y = self.overlay_y + self.overlay_h - int(widget_height * 1.5)

        self.close_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(close_x, close_y, close_w, widget_height),
            text="Close",
            manager=manager,
        )

    def handle_event(self, event) -> bool:
        """Returns True if the popup consumed the event."""
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.close_button:
                self.dismiss()
                return True
        return False

    def dismiss(self):
        self.visible = False
        self.close_button.hide()

    def draw(self, surface: pygame.Surface):
        if not self.visible:
            return

        # Title color based on success
        title_color = (100, 200, 100) if self.success else (200, 80, 80)
        border_color = (60, 120, 60) if self.success else (120, 60, 60)

        # Background
        pygame.draw.rect(
            surface,
            (15, 15, 15),
            pygame.Rect(self.overlay_x, self.overlay_y, self.overlay_w, self.overlay_h),
            border_radius=8,
        )

        # Border
        pygame.draw.rect(
            surface,
            border_color,
            pygame.Rect(self.overlay_x, self.overlay_y, self.overlay_w, self.overlay_h),
            2,
            border_radius=8,
        )

        # Title
        title_surf = self.title_font.render(self.title, True, title_color)
        title_rect = title_surf.get_rect(
            centerx=self.overlay_x + self.overlay_w // 2,
            y=self.overlay_y + int(self.internal_height * 0.02),
        )
        surface.blit(title_surf, title_rect)

        # Divider
        divider_y = self.overlay_y + int(self.internal_height * 0.055)
        pygame.draw.line(
            surface,
            border_color,
            (self.overlay_x + int(self.overlay_w * 0.05), divider_y),
            (self.overlay_x + int(self.overlay_w * 0.95), divider_y),
            1,
        )

        # Lines
        entries_y = self.overlay_y + int(self.internal_height * 0.065)
        for i, line in enumerate(self.lines):
            text_surf = self.font.render(line, True, (180, 180, 180))
            surface.blit(
                text_surf,
                (
                    self.overlay_x + int(self.overlay_w * 0.08),
                    entries_y + i * self.line_height,
                ),
            )
