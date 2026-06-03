class Camera:
    def __init__(self, canvas_width: int, canvas_height: int):
        self.canvas_width = canvas_width
        self.canvas_height = canvas_height

        self.scale = 20.0  # pixels per world unit
        self.offset_x = 0.0  # pixels
        self.offset_y = 0.0  # pixels

        self._panning = False
        self._pan_start_mouse = (0, 0)
        self._pan_start_offset = (0, 0)

    def world_to_screen(self, wx: float, wy: float) -> tuple[float, float]:
        """Convert a world coordinate to screen (canvas) pixel position."""
        sx = wx * self.scale + self.offset_x
        sy = wy * self.scale + self.offset_y
        return sx, sy

    def screen_to_world(self, sx: float, sy: float) -> tuple[float, float]:
        """Convert a screen (canvas) pixel position to world coordinate."""
        wx = (sx - self.offset_x) / self.scale
        wy = (sy - self.offset_y) / self.scale
        return wx, wy

    def zoom(self, factor: float, mouse_x: float, mouse_y: float):
        """Zoom in or out, keeping the point under the cursor fixed."""
        # World position under cursor before zoom
        wx, wy = self.screen_to_world(mouse_x, mouse_y)

        self.scale *= factor
        self.scale = max(4.0, min(self.scale, 200.0))  # clamp zoom range

        # Adjust offset so the same world point stays under cursor
        self.offset_x = mouse_x - wx * self.scale
        self.offset_y = mouse_y - wy * self.scale

    def start_pan(self, mouse_x: float, mouse_y: float):
        """Begin a pan operation."""
        self._panning = True
        self._pan_start_mouse = (mouse_x, mouse_y)
        self._pan_start_offset = (self.offset_x, self.offset_y)

    def update_pan(self, mouse_x: float, mouse_y: float):
        """Update pan while mouse is held."""
        if not self._panning:
            return
        dx = mouse_x - self._pan_start_mouse[0]
        dy = mouse_y - self._pan_start_mouse[1]
        self.offset_x = self._pan_start_offset[0] + dx
        self.offset_y = self._pan_start_offset[1] + dy

    def end_pan(self):
        """End a pan operation."""
        self._panning = False

    def center_on_grid(self, grid_pixel_width: float, grid_pixel_height: float):
        """Center the grid in the canvas."""
        self.offset_x = (self.canvas_width - grid_pixel_width) / 2
        self.offset_y = (self.canvas_height - grid_pixel_height) / 2
