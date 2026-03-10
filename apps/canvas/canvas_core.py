"""
Canvas Engine - Extracted from interaction_canvas.ipynb
=======================================================
Self-contained gesture-controlled canvas system.
All drawing, shapes, layers, and interaction logic.
"""

import cv2
import numpy as np
import mediapipe as mp
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Any
from enum import Enum, auto
from collections import deque
import time
import math
import copy
import json
import os


# =============================================================================
# CONFIGURATION
# =============================================================================

class CanvasConfig:
    CANVAS_WIDTH = 1280
    CANVAS_HEIGHT = 720
    BACKGROUND_COLOR = (30, 30, 30)
    MAX_HANDS = 1
    DETECTION_CONFIDENCE = 0.7
    TRACKING_CONFIDENCE = 0.7
    PINCH_THRESHOLD = 0.05
    FIST_THRESHOLD = 0.15
    FINGER_EXTENDED_THRESHOLD = 0.15
    GESTURE_DEBOUNCE_FRAMES = 3
    SMOOTHING_WINDOW = 5
    POSITION_SMOOTHING_FACTOR = 0.3
    SELECTION_RADIUS = 50
    STROKE_WIDTH = 3
    PREVIEW_ALPHA = 0.5
    PRESSURE_MIN_THICKNESS = 1
    PRESSURE_MAX_THICKNESS = 15
    PRESSURE_SMOOTHING = 0.4
    PRESSURE_ENABLED = True
    SWIPE_MIN_DISTANCE = 0.08
    SWIPE_MAX_DURATION = 0.5
    ROTATION_SENSITIVITY = 2.0
    FRAME_SKIP_STABLE_COUNT = 5
    FRAME_SKIP_ENABLED = True
    LOW_CONFIDENCE_THRESHOLD = 0.6
    EDGE_WARNING_MARGIN = 0.08
    MAX_LAYERS = 5
    TUTORIAL_DURATION = 5.0
    SAVE_DIR = "canvas_saves"


# =============================================================================
# DATA STRUCTURES & ENUMS
# =============================================================================

class GestureType(Enum):
    IDLE = auto()
    DRAW = auto()
    SELECT = auto()
    GRAB = auto()
    PINCH = auto()
    POINT = auto()
    SPLIT = auto()
    THUMBS_UP = auto()
    SWIPE_LEFT = auto()
    SWIPE_RIGHT = auto()
    NONE = auto()

class ToolType(Enum):
    SELECT = auto()
    PEN = auto()
    ERASER = auto()
    SHAPES_2D = auto()
    SHAPES_3D = auto()
    LINE = auto()
    RESIZE = auto()
    KNIFE = auto()
    MOVE = auto()

class InteractionMode(Enum):
    IDLE = auto()
    DRAWING = auto()
    ERASING = auto()
    SELECTING = auto()
    MOVING = auto()
    SCALING = auto()
    SHAPE_PREVIEW = auto()
    CUTTING = auto()
    ROTATING = auto()

class ShapeType(Enum):
    FREEHAND = auto()
    CIRCLE = auto()
    HALF_CIRCLE = auto()
    RECTANGLE = auto()
    TRIANGLE = auto()
    PENTAGON = auto()
    HEXAGON = auto()
    STAR = auto()
    ELLIPSE = auto()
    DIAMOND = auto()
    LINE = auto()
    POLYGON = auto()
    ARC = auto()
    CUBE = auto()
    CYLINDER = auto()
    CONE = auto()
    SPHERE = auto()
    PYRAMID = auto()
    PRISM = auto()

SHAPES_2D_LIST = [
    ShapeType.CIRCLE, ShapeType.RECTANGLE, ShapeType.TRIANGLE,
    ShapeType.PENTAGON, ShapeType.HEXAGON, ShapeType.STAR,
    ShapeType.ELLIPSE, ShapeType.DIAMOND,
]
SHAPES_3D_LIST = [
    ShapeType.CUBE, ShapeType.CYLINDER, ShapeType.CONE,
    ShapeType.SPHERE, ShapeType.PYRAMID, ShapeType.PRISM,
]

SHAPE_DISPLAY_NAMES = {
    ShapeType.CIRCLE: "Circle", ShapeType.RECTANGLE: "Rect",
    ShapeType.TRIANGLE: "Tri", ShapeType.PENTAGON: "Pent",
    ShapeType.HEXAGON: "Hex", ShapeType.STAR: "Star",
    ShapeType.ELLIPSE: "Ellipse", ShapeType.DIAMOND: "Diamond",
    ShapeType.CUBE: "Cube", ShapeType.CYLINDER: "Cyl",
    ShapeType.CONE: "Cone", ShapeType.SPHERE: "Sphere",
    ShapeType.PYRAMID: "Pyra", ShapeType.PRISM: "Prism",
}

class ObjectState(Enum):
    IDLE = auto()
    SELECTED = auto()
    MOVING = auto()
    SCALING = auto()
    CUTTING = auto()
    ROTATING = auto()

@dataclass
class Point:
    x: float
    y: float
    pressure: float = 1.0

    def to_tuple(self) -> Tuple[int, int]:
        return (int(self.x), int(self.y))

    def distance_to(self, other: 'Point') -> float:
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)

@dataclass
class HandData:
    hand_id: int
    landmarks: List[Tuple[float, float, float]]
    bbox: Tuple[int, int, int, int]
    confidence: float
    handedness: str
    fingertip_positions: Dict[str, Point] = field(default_factory=dict)

@dataclass
class GestureData:
    gesture_type: GestureType
    confidence: float
    parameters: Dict[str, Any] = field(default_factory=dict)
    hand_id: int = 0

@dataclass
class CanvasObject:
    obj_id: int
    shape_type: ShapeType
    points: List[Point]
    color: Tuple[int, int, int] = (255, 255, 255)
    thickness: int = 3
    state: ObjectState = ObjectState.IDLE
    position: Point = field(default_factory=lambda: Point(0, 0))
    scale: float = 1.0
    rotation: float = 0.0
    layer_id: int = 0
    center: Optional[Point] = None
    radius: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None
    start_angle: float = 0.0
    end_angle: float = 360.0
    vertices: Optional[List[Point]] = None

@dataclass
class Stroke:
    points: List[Point]
    color: Tuple[int, int, int] = (255, 255, 255)
    thickness: int = 3
    layer_id: int = 0

@dataclass
class Layer:
    layer_id: int
    name: str
    visible: bool = True
    opacity: float = 1.0


# =============================================================================
# UI TOOLBAR SYSTEM
# =============================================================================

@dataclass
class ToolButton:
    tool: ToolType
    icon: str
    x: int
    y: int
    width: int = 60
    height: int = 60
    is_hovered: bool = False
    is_selected: bool = False
    color: Tuple[int, int, int] = (80, 80, 80)
    hover_color: Tuple[int, int, int] = (120, 120, 120)
    selected_color: Tuple[int, int, int] = (0, 150, 255)

@dataclass
class ShapePickerItem:
    shape_type: ShapeType
    label: str
    x: int = 0
    y: int = 0
    width: int = 55
    height: int = 40
    is_hovered: bool = False
    is_selected: bool = False


class UIToolbar:
    TOOL_ICONS = {
        ToolType.SELECT: "SEL", ToolType.PEN: "PEN", ToolType.ERASER: "ERS",
        ToolType.SHAPES_2D: "2D", ToolType.SHAPES_3D: "3D", ToolType.LINE: "LIN",
        ToolType.MOVE: "MOV", ToolType.RESIZE: "RSZ", ToolType.KNIFE: "CUT",
    }

    def __init__(self, x: int = 10, y: int = 80, button_size: int = 50, spacing: int = 5):
        self.x = x
        self.y = y
        self.button_size = button_size
        self.spacing = spacing
        self.buttons: List[ToolButton] = []
        self.selected_tool = ToolType.PEN
        self.hovered_tool: Optional[ToolType] = None
        self.selected_2d_shape: ShapeType = ShapeType.CIRCLE
        self.selected_3d_shape: ShapeType = ShapeType.CUBE
        self.shape_picker_items: List[ShapePickerItem] = []
        self.shape_panel_visible = False
        self.color_buttons: List[Tuple[int, int, int]] = [
            (255, 255, 255), (255, 80, 80), (80, 255, 80), (80, 80, 255),
            (255, 255, 80), (255, 80, 255), (80, 255, 255),
        ]
        self.selected_color_idx = 0
        self.brush_sizes = [2, 4, 6, 10, 15]
        self.selected_brush_idx = 1
        self._create_buttons()

    def _create_buttons(self):
        self.buttons.clear()
        current_y = self.y
        for tool in ToolType:
            btn = ToolButton(tool=tool, icon=self.TOOL_ICONS.get(tool, "?"),
                             x=self.x, y=current_y, width=self.button_size,
                             height=self.button_size, is_selected=(tool == self.selected_tool))
            self.buttons.append(btn)
            current_y += self.button_size + self.spacing

    def _build_shape_picker(self):
        self.shape_picker_items.clear()
        if self.selected_tool == ToolType.SHAPES_2D:
            shapes = SHAPES_2D_LIST
            selected = self.selected_2d_shape
        elif self.selected_tool == ToolType.SHAPES_3D:
            shapes = SHAPES_3D_LIST
            selected = self.selected_3d_shape
        else:
            self.shape_panel_visible = False
            return
        self.shape_panel_visible = True
        panel_x = self.x + self.button_size + 20
        panel_y = self.y
        for btn in self.buttons:
            if btn.tool == self.selected_tool:
                panel_y = btn.y
                break
        item_w, item_h = 55, 40
        cols = 2
        gap = 4
        for i, shape in enumerate(shapes):
            col = i % cols
            row = i // cols
            ix = panel_x + col * (item_w + gap)
            iy = panel_y + row * (item_h + gap)
            item = ShapePickerItem(shape_type=shape, label=SHAPE_DISPLAY_NAMES.get(shape, shape.name),
                                   x=ix, y=iy, width=item_w, height=item_h, is_selected=(shape == selected))
            self.shape_picker_items.append(item)

    def get_current_shape(self) -> ShapeType:
        if self.selected_tool == ToolType.SHAPES_2D:
            return self.selected_2d_shape
        elif self.selected_tool == ToolType.SHAPES_3D:
            return self.selected_3d_shape
        return ShapeType.RECTANGLE

    def hit_test(self, point: Point) -> Optional[ToolType]:
        for btn in self.buttons:
            if btn.x <= point.x <= btn.x + btn.width and btn.y <= point.y <= btn.y + btn.height:
                return btn.tool
        return None

    def hit_test_shape_picker(self, point: Point) -> Optional[ShapeType]:
        if not self.shape_panel_visible:
            return None
        for item in self.shape_picker_items:
            if item.x <= point.x <= item.x + item.width and item.y <= point.y <= item.y + item.height:
                return item.shape_type
        return None

    def hit_test_color(self, point: Point) -> Optional[int]:
        color_y = self.y + len(self.buttons) * (self.button_size + self.spacing) + 20
        color_size = 25
        for i, color in enumerate(self.color_buttons):
            cx = self.x + (i % 4) * (color_size + 3)
            cy = color_y + (i // 4) * (color_size + 3)
            if cx <= point.x <= cx + color_size and cy <= point.y <= cy + color_size:
                return i
        return None

    def update_hover(self, point: Optional[Point]):
        self.hovered_tool = None
        for btn in self.buttons:
            btn.is_hovered = False
        for item in self.shape_picker_items:
            item.is_hovered = False
        if point is not None:
            hovered = self.hit_test(point)
            if hovered is not None:
                self.hovered_tool = hovered
                for btn in self.buttons:
                    if btn.tool == hovered:
                        btn.is_hovered = True
            if self.shape_panel_visible:
                for item in self.shape_picker_items:
                    if item.x <= point.x <= item.x + item.width and item.y <= point.y <= item.y + item.height:
                        item.is_hovered = True

    def select_tool(self, tool: ToolType):
        self.selected_tool = tool
        for btn in self.buttons:
            btn.is_selected = (btn.tool == tool)
        if tool in (ToolType.SHAPES_2D, ToolType.SHAPES_3D):
            self._build_shape_picker()
        else:
            self.shape_panel_visible = False
            self.shape_picker_items.clear()

    def select_shape(self, shape_type: ShapeType):
        if shape_type in SHAPES_2D_LIST:
            self.selected_2d_shape = shape_type
        elif shape_type in SHAPES_3D_LIST:
            self.selected_3d_shape = shape_type
        self._build_shape_picker()

    def select_color(self, idx: int):
        if 0 <= idx < len(self.color_buttons):
            self.selected_color_idx = idx

    def get_current_color(self) -> Tuple[int, int, int]:
        return self.color_buttons[self.selected_color_idx]

    def get_current_brush_size(self) -> int:
        return self.brush_sizes[self.selected_brush_idx]

    def cycle_brush_size(self):
        self.selected_brush_idx = (self.selected_brush_idx + 1) % len(self.brush_sizes)

    def cycle_color(self):
        self.selected_color_idx = (self.selected_color_idx + 1) % len(self.color_buttons)

    @property
    def selected_color(self) -> Tuple[int, int, int]:
        return self.color_buttons[self.selected_color_idx]

    @property
    def brush_size(self) -> int:
        return self.brush_sizes[self.selected_brush_idx]

    @brush_size.setter
    def brush_size(self, value: int):
        if value in self.brush_sizes:
            self.selected_brush_idx = self.brush_sizes.index(value)
        else:
            self.brush_sizes.append(value)
            self.selected_brush_idx = len(self.brush_sizes) - 1

    def check_hover(self, x: int, y: int) -> bool:
        point = Point(x, y)
        bounds = self.get_toolbar_bounds()
        in_toolbar = (bounds[0] <= x <= bounds[0] + bounds[2] and bounds[1] <= y <= bounds[1] + bounds[3])
        in_shape_panel = False
        if self.shape_panel_visible and self.shape_picker_items:
            sp_bounds = self._get_shape_panel_bounds()
            in_shape_panel = (sp_bounds[0] <= x <= sp_bounds[0] + sp_bounds[2] and
                              sp_bounds[1] <= y <= sp_bounds[1] + sp_bounds[3])
        in_any = in_toolbar or in_shape_panel
        self.update_hover(point if in_any else None)
        return in_any

    def select_at(self, x: int, y: int) -> Optional[ToolType]:
        point = Point(x, y)
        if self.shape_panel_visible:
            shape = self.hit_test_shape_picker(point)
            if shape is not None:
                self.select_shape(shape)
                return self.selected_tool
        tool = self.hit_test(point)
        if tool is not None:
            self.select_tool(tool)
            return tool
        color_idx = self.hit_test_color(point)
        if color_idx is not None:
            self.select_color(color_idx)
        return None

    def _get_shape_panel_bounds(self) -> Tuple[int, int, int, int]:
        if not self.shape_picker_items:
            return (0, 0, 0, 0)
        min_x = min(i.x for i in self.shape_picker_items)
        min_y = min(i.y for i in self.shape_picker_items)
        max_x = max(i.x + i.width for i in self.shape_picker_items)
        max_y = max(i.y + i.height for i in self.shape_picker_items)
        return (min_x - 5, min_y - 25, max_x - min_x + 10, max_y - min_y + 30)

    def get_toolbar_bounds(self) -> Tuple[int, int, int, int]:
        toolbar_height = len(self.buttons) * (self.button_size + self.spacing) + 120
        return (self.x - 5, self.y - 10, self.button_size + 20, toolbar_height + 10)

    def render(self, canvas: np.ndarray):
        toolbar_height = len(self.buttons) * (self.button_size + self.spacing) + 120
        cv2.rectangle(canvas, (self.x - 5, self.y - 10),
                      (self.x + self.button_size + 15, self.y + toolbar_height), (40, 40, 40), -1)
        cv2.rectangle(canvas, (self.x - 5, self.y - 10),
                      (self.x + self.button_size + 15, self.y + toolbar_height), (80, 80, 80), 2)
        for btn in self.buttons:
            if btn.is_selected:
                color = btn.selected_color
            elif btn.is_hovered:
                color = btn.hover_color
            else:
                color = btn.color
            cv2.rectangle(canvas, (btn.x, btn.y), (btn.x + btn.width, btn.y + btn.height), color, -1)
            border_color = (255, 255, 255) if btn.is_selected else (100, 100, 100)
            cv2.rectangle(canvas, (btn.x, btn.y), (btn.x + btn.width, btn.y + btn.height),
                          border_color, 2 if btn.is_selected else 1)
            text_color = (255, 255, 255)
            icon_cx = btn.x + btn.width // 2
            icon_cy = btn.y + 18
            self._draw_tool_icon(canvas, btn.tool, icon_cx, icon_cy, text_color)
            cv2.putText(canvas, btn.icon, (btn.x + 8, btn.y + btn.height - 6),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.35, text_color, 1)
        if self.shape_panel_visible and self.shape_picker_items:
            self._render_shape_panel(canvas)
        color_y = self.y + len(self.buttons) * (self.button_size + self.spacing) + 10
        cv2.putText(canvas, "Colors:", (self.x, color_y), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (180, 180, 180), 1)
        color_y += 15
        color_size = 25
        for i, clr in enumerate(self.color_buttons):
            cx = self.x + (i % 4) * (color_size + 3)
            cy = color_y + (i // 4) * (color_size + 3)
            cv2.rectangle(canvas, (cx, cy), (cx + color_size, cy + color_size), clr, -1)
            if i == self.selected_color_idx:
                cv2.rectangle(canvas, (cx - 2, cy - 2), (cx + color_size + 2, cy + color_size + 2), (255, 255, 255), 2)
        size_y = color_y + (len(self.color_buttons) // 4 + 1) * (color_size + 3) + 10
        cv2.putText(canvas, f"Size: {self.get_current_brush_size()}", (self.x, size_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (180, 180, 180), 1)
        tool_label = self.selected_tool.name
        if self.selected_tool == ToolType.SHAPES_2D:
            tool_label = f"2D: {SHAPE_DISPLAY_NAMES.get(self.selected_2d_shape, '?')}"
        elif self.selected_tool == ToolType.SHAPES_3D:
            tool_label = f"3D: {SHAPE_DISPLAY_NAMES.get(self.selected_3d_shape, '?')}"
        cv2.putText(canvas, f"Tool: {tool_label}", (self.x, self.y - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 255), 1)

    def _render_shape_panel(self, canvas: np.ndarray):
        bounds = self._get_shape_panel_bounds()
        bx, by, bw, bh = bounds
        title = "2D Shapes" if self.selected_tool == ToolType.SHAPES_2D else "3D Shapes"
        cv2.rectangle(canvas, (bx, by), (bx + bw, by + bh), (35, 35, 50), -1)
        cv2.rectangle(canvas, (bx, by), (bx + bw, by + bh), (100, 140, 200), 2)
        cv2.putText(canvas, title, (bx + 5, by + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 180, 255), 1)
        for item in self.shape_picker_items:
            if item.is_selected:
                bg = (0, 120, 200)
            elif item.is_hovered:
                bg = (90, 90, 110)
            else:
                bg = (60, 60, 75)
            cv2.rectangle(canvas, (item.x, item.y), (item.x + item.width, item.y + item.height), bg, -1)
            border = (255, 255, 255) if item.is_selected else (100, 100, 120)
            cv2.rectangle(canvas, (item.x, item.y), (item.x + item.width, item.y + item.height), border, 1)
            icx = item.x + 15
            icy = item.y + item.height // 2
            self._draw_shape_icon(canvas, item.shape_type, icx, icy, (200, 220, 255))
            cv2.putText(canvas, item.label, (item.x + 30, item.y + item.height // 2 + 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.28, (200, 200, 220), 1)

    def _draw_shape_icon(self, canvas, shape, cx, cy, color):
        s = 8
        if shape == ShapeType.CIRCLE:
            cv2.circle(canvas, (cx, cy), s, color, 1)
        elif shape == ShapeType.RECTANGLE:
            cv2.rectangle(canvas, (cx - s, cy - 6), (cx + s, cy + 6), color, 1)
        elif shape == ShapeType.TRIANGLE:
            pts = np.array([[cx, cy - s], [cx - s, cy + s], [cx + s, cy + s]], np.int32)
            cv2.polylines(canvas, [pts], True, color, 1)
        elif shape == ShapeType.PENTAGON:
            pts = self._regular_polygon_pts(cx, cy, s, 5)
            cv2.polylines(canvas, [pts], True, color, 1)
        elif shape == ShapeType.HEXAGON:
            pts = self._regular_polygon_pts(cx, cy, s, 6)
            cv2.polylines(canvas, [pts], True, color, 1)
        elif shape == ShapeType.STAR:
            pts = self._star_pts(cx, cy, s, s // 2, 5)
            cv2.polylines(canvas, [pts], True, color, 1)
        elif shape == ShapeType.ELLIPSE:
            cv2.ellipse(canvas, (cx, cy), (s, s // 2), 0, 0, 360, color, 1)
        elif shape == ShapeType.DIAMOND:
            pts = np.array([[cx, cy - s], [cx + s, cy], [cx, cy + s], [cx - s, cy]], np.int32)
            cv2.polylines(canvas, [pts], True, color, 1)
        elif shape == ShapeType.CUBE:
            o = s // 3
            cv2.rectangle(canvas, (cx - s + o, cy - s + o), (cx + 2, cy + 2), color, 1)
            cv2.rectangle(canvas, (cx - s, cy - s), (cx - o, cy - o), color, 1)
        elif shape == ShapeType.CYLINDER:
            cv2.ellipse(canvas, (cx, cy - s + 3), (s, 3), 0, 0, 360, color, 1)
            cv2.ellipse(canvas, (cx, cy + s - 3), (s, 3), 0, 0, 180, color, 1)
            cv2.line(canvas, (cx - s, cy - s + 3), (cx - s, cy + s - 3), color, 1)
            cv2.line(canvas, (cx + s, cy - s + 3), (cx + s, cy + s - 3), color, 1)
        elif shape == ShapeType.CONE:
            cv2.line(canvas, (cx, cy - s), (cx - s, cy + s), color, 1)
            cv2.line(canvas, (cx, cy - s), (cx + s, cy + s), color, 1)
            cv2.ellipse(canvas, (cx, cy + s), (s, 3), 0, 0, 360, color, 1)
        elif shape == ShapeType.SPHERE:
            cv2.circle(canvas, (cx, cy), s, color, 1)
            cv2.ellipse(canvas, (cx, cy), (s, 3), 0, 0, 360, color, 1)
        elif shape == ShapeType.PYRAMID:
            cv2.line(canvas, (cx, cy - s), (cx - s, cy + s), color, 1)
            cv2.line(canvas, (cx, cy - s), (cx + s, cy + s), color, 1)
            cv2.line(canvas, (cx - s, cy + s), (cx + s, cy + s), color, 1)
        elif shape == ShapeType.PRISM:
            pts_f = np.array([[cx - s, cy + s], [cx, cy - s + 3], [cx + s, cy + s]], np.int32)
            cv2.polylines(canvas, [pts_f], True, color, 1)

    @staticmethod
    def _regular_polygon_pts(cx, cy, r, n):
        angles = [2 * math.pi * i / n - math.pi / 2 for i in range(n)]
        return np.array([(int(cx + r * math.cos(a)), int(cy + r * math.sin(a))) for a in angles], np.int32)

    @staticmethod
    def _star_pts(cx, cy, outer_r, inner_r, n):
        pts = []
        for i in range(2 * n):
            a = math.pi * i / n - math.pi / 2
            r = outer_r if i % 2 == 0 else inner_r
            pts.append((int(cx + r * math.cos(a)), int(cy + r * math.sin(a))))
        return np.array(pts, np.int32)

    def _draw_tool_icon(self, canvas, tool, cx, cy, color):
        s = 8
        if tool == ToolType.SELECT:
            pts = np.array([[cx, cy - s], [cx - 4, cy + s], [cx, cy + 4], [cx + 4, cy + s]], np.int32)
            cv2.polylines(canvas, [pts], True, color, 1)
        elif tool == ToolType.PEN:
            cv2.line(canvas, (cx - s, cy + s), (cx + s, cy - s), color, 2)
            cv2.circle(canvas, (cx - s, cy + s), 2, (0, 200, 255), -1)
        elif tool == ToolType.ERASER:
            cv2.rectangle(canvas, (cx - s, cy - 4), (cx + s, cy + 4), color, 1)
        elif tool == ToolType.SHAPES_2D:
            cv2.circle(canvas, (cx - 3, cy), 5, color, 1)
            cv2.rectangle(canvas, (cx + 1, cy - 4), (cx + s, cy + 5), color, 1)
        elif tool == ToolType.SHAPES_3D:
            o = 3
            cv2.rectangle(canvas, (cx - s + o, cy - s + o), (cx + 2, cy + 2), color, 1)
            cv2.rectangle(canvas, (cx - s, cy - s), (cx - o, cy - o), color, 1)
        elif tool == ToolType.LINE:
            cv2.line(canvas, (cx - s, cy + s), (cx + s, cy - s), color, 2)
        elif tool == ToolType.MOVE:
            cv2.arrowedLine(canvas, (cx, cy + s), (cx, cy - s), color, 1, tipLength=0.4)
            cv2.arrowedLine(canvas, (cx - s, cy), (cx + s, cy), color, 1, tipLength=0.4)
        elif tool == ToolType.RESIZE:
            cv2.arrowedLine(canvas, (cx, cy + s), (cx, cy - s), color, 1, tipLength=0.35)
            cv2.arrowedLine(canvas, (cx, cy - s), (cx, cy + s), color, 1, tipLength=0.35)
        elif tool == ToolType.KNIFE:
            cv2.line(canvas, (cx - s, cy + s), (cx + s, cy - s), (0, 0, 255), 2)
            cv2.circle(canvas, (cx + s, cy - s), 3, color, -1)


# =============================================================================
# HAND TRACKING LAYER
# =============================================================================

class CanvasHandTracker:
    WRIST = 0
    THUMB_CMC, THUMB_MCP, THUMB_IP, THUMB_TIP = 1, 2, 3, 4
    INDEX_MCP, INDEX_PIP, INDEX_DIP, INDEX_TIP = 5, 6, 7, 8
    MIDDLE_MCP, MIDDLE_PIP, MIDDLE_DIP, MIDDLE_TIP = 9, 10, 11, 12
    RING_MCP, RING_PIP, RING_DIP, RING_TIP = 13, 14, 15, 16
    PINKY_MCP, PINKY_PIP, PINKY_DIP, PINKY_TIP = 17, 18, 19, 20

    FINGERTIP_INDICES = {'thumb': 4, 'index': 8, 'middle': 12, 'ring': 16, 'pinky': 20}

    def __init__(self):
        self.mp_hands = mp.solutions.hands
        self.hands = None

    def initialize(self) -> bool:
        try:
            self.hands = self.mp_hands.Hands(
                static_image_mode=False, max_num_hands=CanvasConfig.MAX_HANDS,
                min_detection_confidence=CanvasConfig.DETECTION_CONFIDENCE,
                min_tracking_confidence=CanvasConfig.TRACKING_CONFIDENCE)
            return True
        except Exception:
            return False

    def process_frame(self, frame: np.ndarray) -> List[HandData]:
        if self.hands is None:
            return []
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb_frame)
        hands_data = []
        if results.multi_hand_landmarks and results.multi_handedness:
            h, w, _ = frame.shape
            for idx, (hand_landmarks, handedness) in enumerate(
                    zip(results.multi_hand_landmarks, results.multi_handedness)):
                landmarks = []
                x_coords, y_coords = [], []
                for lm in hand_landmarks.landmark:
                    landmarks.append((lm.x, lm.y, lm.z))
                    x_coords.append(lm.x * w)
                    y_coords.append(lm.y * h)
                x_min, x_max = int(min(x_coords)), int(max(x_coords))
                y_min, y_max = int(min(y_coords)), int(max(y_coords))
                bbox = (x_min, y_min, x_max - x_min, y_max - y_min)
                hand_label = handedness.classification[0].label
                confidence = handedness.classification[0].score
                fingertips = {}
                for finger_name, tip_idx in self.FINGERTIP_INDICES.items():
                    lm = landmarks[tip_idx]
                    fingertips[finger_name] = Point(x=lm[0] * w, y=lm[1] * h, pressure=1.0 - lm[2])
                hands_data.append(HandData(hand_id=idx, landmarks=landmarks, bbox=bbox,
                                           confidence=confidence, handedness=hand_label,
                                           fingertip_positions=fingertips))
        return hands_data

    def get_finger_states(self, hand: HandData) -> Dict[str, bool]:
        landmarks = hand.landmarks
        finger_states = {}
        thumb_tip = landmarks[self.THUMB_TIP]
        thumb_ip = landmarks[self.THUMB_IP]
        if hand.handedness == "Right":
            finger_states['thumb'] = thumb_tip[0] < thumb_ip[0]
        else:
            finger_states['thumb'] = thumb_tip[0] > thumb_ip[0]
        for finger_name, tip_idx, pip_idx in [
            ('index', self.INDEX_TIP, self.INDEX_PIP),
            ('middle', self.MIDDLE_TIP, self.MIDDLE_PIP),
            ('ring', self.RING_TIP, self.RING_PIP),
            ('pinky', self.PINKY_TIP, self.PINKY_PIP),
        ]:
            finger_states[finger_name] = landmarks[tip_idx][1] < landmarks[pip_idx][1] - CanvasConfig.FINGER_EXTENDED_THRESHOLD * 0.1
        return finger_states

    def release(self):
        if self.hands is not None:
            self.hands.close()
            self.hands = None


# =============================================================================
# GESTURE RECOGNITION LAYER
# =============================================================================

class CanvasGestureRecognizer:
    def __init__(self, hand_tracker: CanvasHandTracker):
        self.hand_tracker = hand_tracker
        self.gesture_history: deque = deque(maxlen=CanvasConfig.GESTURE_DEBOUNCE_FRAMES)
        self.current_gesture = GestureType.NONE
        self.gesture_start_time = 0
        self.pinch_start_distance = None
        self._swipe_start_pos: Optional[Point] = None
        self._swipe_start_time: float = 0
        self._swipe_cooldown: float = 0
        self._prev_palm_angle: Optional[float] = None
        self._palm_angle_smoothed: float = 0.0
        self._thumbs_up_cooldown: float = 0

    def _detect_thumbs_up(self, finger_states, landmarks):
        if not finger_states['thumb']:
            return False
        if finger_states['index'] or finger_states['middle'] or finger_states['ring'] or finger_states['pinky']:
            return False
        return landmarks[4][1] < landmarks[3][1] - 0.02

    def _detect_swipe(self, hand, finger_states):
        now = time.time()
        if now < self._swipe_cooldown:
            return None
        if not (finger_states['index'] and finger_states['middle'] and
                not finger_states['ring'] and not finger_states['pinky']):
            self._swipe_start_pos = None
            return None
        idx = hand.fingertip_positions.get('index')
        mid = hand.fingertip_positions.get('middle')
        if not idx or not mid:
            return None
        current_pos = Point((idx.x + mid.x) / 2, (idx.y + mid.y) / 2)
        if self._swipe_start_pos is None:
            self._swipe_start_pos = current_pos
            self._swipe_start_time = now
            return None
        elapsed = now - self._swipe_start_time
        if elapsed > CanvasConfig.SWIPE_MAX_DURATION:
            self._swipe_start_pos = current_pos
            self._swipe_start_time = now
            return None
        dx = current_pos.x - self._swipe_start_pos.x
        dy = abs(current_pos.y - self._swipe_start_pos.y)
        if abs(dx) > CanvasConfig.SWIPE_MIN_DISTANCE and dy < abs(dx) * 0.5:
            self._swipe_cooldown = now + 1.0
            self._swipe_start_pos = None
            return GestureType.SWIPE_LEFT if dx < 0 else GestureType.SWIPE_RIGHT
        return None

    def get_palm_angle(self, landmarks):
        wrist = landmarks[0]
        middle_mcp = landmarks[9]
        dx = middle_mcp[0] - wrist[0]
        dy = middle_mcp[1] - wrist[1]
        return math.degrees(math.atan2(dy, dx))

    def get_palm_angle_delta(self, landmarks):
        angle = self.get_palm_angle(landmarks)
        if self._prev_palm_angle is None:
            self._prev_palm_angle = angle
            return 0.0
        delta = angle - self._prev_palm_angle
        if delta > 180: delta -= 360
        elif delta < -180: delta += 360
        self._prev_palm_angle = angle
        alpha = 0.3
        self._palm_angle_smoothed = alpha * delta + (1 - alpha) * self._palm_angle_smoothed
        return self._palm_angle_smoothed

    def recognize_gesture(self, hand: HandData) -> GestureData:
        finger_states = self.hand_tracker.get_finger_states(hand)
        landmarks = hand.landmarks
        extended_count = sum(1 for s in finger_states.values() if s)
        thumb_tip = Point(landmarks[4][0], landmarks[4][1])
        index_tip = Point(landmarks[8][0], landmarks[8][1])
        pinch_distance = thumb_tip.distance_to(index_tip)
        palm_angle = self.get_palm_angle(landmarks)
        palm_angle_delta = self.get_palm_angle_delta(landmarks)
        parameters = {'palm_angle': palm_angle, 'palm_angle_delta': palm_angle_delta}

        swipe_result = self._detect_swipe(hand, finger_states)
        if swipe_result is not None:
            return GestureData(gesture_type=swipe_result, confidence=0.95,
                               parameters=parameters, hand_id=hand.hand_id)
        if pinch_distance < CanvasConfig.PINCH_THRESHOLD:
            parameters['pinch_distance'] = pinch_distance
            parameters['pinch_center'] = Point((thumb_tip.x + index_tip.x) / 2,
                                               (thumb_tip.y + index_tip.y) / 2)
            return GestureData(gesture_type=GestureType.PINCH, confidence=1.0 - (pinch_distance / CanvasConfig.PINCH_THRESHOLD),
                               parameters=parameters, hand_id=hand.hand_id)
        elif self._detect_thumbs_up(finger_states, landmarks):
            now = time.time()
            if now >= self._thumbs_up_cooldown:
                self._thumbs_up_cooldown = now + 1.5
                return GestureData(gesture_type=GestureType.THUMBS_UP, confidence=0.9,
                                   parameters=parameters, hand_id=hand.hand_id)
            return GestureData(gesture_type=GestureType.IDLE, confidence=0.5,
                               parameters=parameters, hand_id=hand.hand_id)
        elif extended_count <= 1 and not finger_states['index']:
            wrist = landmarks[0]
            middle_mcp = landmarks[9]
            parameters['grab_center'] = Point((wrist[0] + middle_mcp[0]) / 2, (wrist[1] + middle_mcp[1]) / 2)
            return GestureData(gesture_type=GestureType.GRAB, confidence=0.9,
                               parameters=parameters, hand_id=hand.hand_id)
        elif (finger_states['index'] and not finger_states['middle'] and
              not finger_states['ring'] and not finger_states['pinky']):
            parameters['draw_point'] = hand.fingertip_positions['index']
            return GestureData(gesture_type=GestureType.DRAW, confidence=0.9,
                               parameters=parameters, hand_id=hand.hand_id)
        elif (finger_states['index'] and finger_states['middle'] and
              not finger_states['ring'] and not finger_states['pinky']):
            parameters['select_point'] = Point(
                (hand.fingertip_positions['index'].x + hand.fingertip_positions['middle'].x) / 2,
                (hand.fingertip_positions['index'].y + hand.fingertip_positions['middle'].y) / 2)
            return GestureData(gesture_type=GestureType.SELECT, confidence=0.85,
                               parameters=parameters, hand_id=hand.hand_id)
        elif extended_count >= 4:
            parameters['palm_center'] = Point((landmarks[0][0] + landmarks[9][0]) / 2,
                                              (landmarks[0][1] + landmarks[9][1]) / 2)
            return GestureData(gesture_type=GestureType.IDLE, confidence=0.7,
                               parameters=parameters, hand_id=hand.hand_id)
        return GestureData(gesture_type=GestureType.NONE, confidence=0.5,
                           parameters=parameters, hand_id=hand.hand_id)

    def apply_debounce(self, gesture: GestureData) -> GestureData:
        if gesture.gesture_type in (GestureType.SWIPE_LEFT, GestureType.SWIPE_RIGHT):
            return gesture
        self.gesture_history.append(gesture.gesture_type)
        if len(self.gesture_history) >= CanvasConfig.GESTURE_DEBOUNCE_FRAMES:
            gesture_counts = {}
            for g in self.gesture_history:
                gesture_counts[g] = gesture_counts.get(g, 0) + 1
            most_common = max(gesture_counts, key=gesture_counts.get)
            if gesture_counts[most_common] >= CanvasConfig.GESTURE_DEBOUNCE_FRAMES // 2 + 1:
                if most_common != self.current_gesture:
                    self.current_gesture = most_common
                    self.gesture_start_time = time.time()
        return GestureData(gesture_type=self.current_gesture, confidence=gesture.confidence,
                           parameters=gesture.parameters, hand_id=gesture.hand_id)

    def reset_palm_tracking(self):
        self._prev_palm_angle = None
        self._palm_angle_smoothed = 0.0


# =============================================================================
# COORDINATE MAPPING LAYER
# =============================================================================

class CoordinateMappingLayer:
    def __init__(self, camera_width=640, camera_height=480,
                 canvas_width=CanvasConfig.CANVAS_WIDTH, canvas_height=CanvasConfig.CANVAS_HEIGHT):
        self.camera_width = camera_width
        self.camera_height = camera_height
        self.canvas_width = canvas_width
        self.canvas_height = canvas_height
        self.position_history: Dict[str, deque] = {}
        self.smoothed_positions: Dict[str, Point] = {}
        self.margin_center = 0.05
        self.margin_edge = 0.015
        self.blend_zone = 0.15

    def _get_edge_proximity(self, norm_x, norm_y):
        min_dist = min(norm_x, 1.0 - norm_x, norm_y, 1.0 - norm_y)
        if min_dist >= self.blend_zone:
            return 0.0
        t = 1.0 - (min_dist / self.blend_zone)
        return t * t * (3.0 - 2.0 * t)

    def get_edge_factor(self, point: Point) -> float:
        return self._get_edge_proximity(point.x / self.camera_width, point.y / self.camera_height)

    def camera_to_canvas(self, point: Point) -> Point:
        norm_x = max(0.0, min(1.0, point.x / self.camera_width))
        norm_y = max(0.0, min(1.0, point.y / self.camera_height))
        # Mirror X so hand movement matches canvas direction (webcam is mirrored)
        norm_x = 1.0 - norm_x
        edge_factor = self._get_edge_proximity(norm_x, norm_y)
        margin_x = self.margin_center * (1.0 - edge_factor) + self.margin_edge * edge_factor
        margin_y = margin_x
        mapped_x = max(0.0, min(1.0, (norm_x - margin_x) / (1 - 2 * margin_x)))
        mapped_y = max(0.0, min(1.0, (norm_y - margin_y) / (1 - 2 * margin_y)))
        cx = max(0.0, min(float(self.canvas_width - 1), mapped_x * self.canvas_width))
        cy = max(0.0, min(float(self.canvas_height - 1), mapped_y * self.canvas_height))
        return Point(cx, cy, point.pressure)

    def apply_smoothing(self, point: Point, key: str = "default") -> Point:
        if key not in self.position_history:
            self.position_history[key] = deque(maxlen=CanvasConfig.SMOOTHING_WINDOW)
            self.smoothed_positions[key] = point
        self.position_history[key].append(point)
        alpha = CanvasConfig.POSITION_SMOOTHING_FACTOR
        prev = self.smoothed_positions[key]
        sx = max(0.0, min(float(self.canvas_width - 1), alpha * point.x + (1 - alpha) * prev.x))
        sy = max(0.0, min(float(self.canvas_height - 1), alpha * point.y + (1 - alpha) * prev.y))
        smoothed = Point(sx, sy, alpha * point.pressure + (1 - alpha) * prev.pressure)
        self.smoothed_positions[key] = smoothed
        return smoothed

    def map_and_smooth(self, point: Point, key: str = "default") -> Point:
        return self.apply_smoothing(self.camera_to_canvas(point), key)

    def reset_smoothing(self, key=None):
        if key is None:
            self.position_history.clear()
            self.smoothed_positions.clear()
        elif key in self.position_history:
            del self.position_history[key]
            del self.smoothed_positions[key]


# =============================================================================
# GEOMETRY HELPERS
# =============================================================================

def _regular_polygon_vertices(center, radius, n, rotation_deg=-90):
    pts = []
    offset = math.radians(rotation_deg)
    for i in range(n):
        angle = offset + 2 * math.pi * i / n
        pts.append(Point(center.x + radius * math.cos(angle), center.y + radius * math.sin(angle)))
    return pts

def _star_vertices(center, outer_r, inner_r=None, tips=5):
    if inner_r is None: inner_r = outer_r * 0.4
    pts = []
    offset = -math.pi / 2
    for i in range(tips * 2):
        r = outer_r if i % 2 == 0 else inner_r
        angle = offset + math.pi * i / tips
        pts.append(Point(center.x + r * math.cos(angle), center.y + r * math.sin(angle)))
    return pts

def _diamond_vertices(center, width, height):
    hw, hh = width / 2, height / 2
    return [Point(center.x, center.y - hh), Point(center.x + hw, center.y),
            Point(center.x, center.y + hh), Point(center.x - hw, center.y)]

def _cube_wireframe(center, size):
    s = size / 2
    dx, dy = s * 0.7, s * 0.4
    f = [Point(center.x - s, center.y - s), Point(center.x + s, center.y - s),
         Point(center.x + s, center.y + s), Point(center.x - s, center.y + s)]
    b = [Point(f[i].x + dx, f[i].y - dy) for i in range(4)]
    edges = []
    for i in range(4):
        edges.append([f[i], f[(i + 1) % 4]])
        edges.append([b[i], b[(i + 1) % 4]])
        edges.append([f[i], b[i]])
    return edges

def _cylinder_wireframe(center, radius, height):
    top_y = center.y - height / 2
    bot_y = center.y + height / 2
    return {
        'top_center': (int(center.x), int(top_y)),
        'bot_center': (int(center.x), int(bot_y)),
        'axes': (int(radius), int(radius * 0.35)),
        'left': ((int(center.x - radius), int(top_y)), (int(center.x - radius), int(bot_y))),
        'right': ((int(center.x + radius), int(top_y)), (int(center.x + radius), int(bot_y))),
    }

def _cone_wireframe(center, radius, height):
    bot_y = center.y + height / 2
    apex = (int(center.x), int(center.y - height / 2))
    return {
        'apex': apex,
        'base_center': (int(center.x), int(bot_y)),
        'axes': (int(radius), int(radius * 0.35)),
        'left': (apex, (int(center.x - radius), int(bot_y))),
        'right': (apex, (int(center.x + radius), int(bot_y))),
    }

def _pyramid_wireframe(center, base_size, height):
    apex = Point(center.x, center.y - height / 2)
    hs = base_size / 2
    by = center.y + height / 2
    base = [Point(center.x - hs, by - hs * 0.3), Point(center.x + hs, by - hs * 0.3),
            Point(center.x + hs * 0.6, by + hs * 0.3), Point(center.x - hs * 0.6, by + hs * 0.3)]
    edges = []
    for i in range(4):
        edges.append([base[i], base[(i + 1) % 4]])
        edges.append([base[i], apex])
    return edges

def _prism_wireframe(center, size, height):
    hs = size / 2
    hh = height / 2
    dx, dy = hs * 0.5, hs * 0.35
    f = [Point(center.x, center.y - hh - hs * 0.3),
         Point(center.x - hs, center.y - hh + hs * 0.5),
         Point(center.x + hs, center.y - hh + hs * 0.5)]
    b = [Point(p.x + dx, p.y + height) for p in f]
    edges = []
    for i in range(3):
        edges.append([f[i], f[(i + 1) % 3]])
        edges.append([b[i], b[(i + 1) % 3]])
        edges.append([f[i], b[i]])
    return edges

def _point_in_polygon(point, vertices):
    n = len(vertices)
    inside = False
    j = n - 1
    for i in range(n):
        yi, yj = vertices[i].y, vertices[j].y
        xi, xj = vertices[i].x, vertices[j].x
        if ((yi > point.y) != (yj > point.y)) and \
           (point.x < (xj - xi) * (point.y - yi) / (yj - yi + 1e-9) + xi):
            inside = not inside
        j = i
    return inside

def _segments_intersect(a1, a2, b1, b2):
    def cross(o, a, b):
        return (a.x - o.x) * (b.y - o.y) - (a.y - o.y) * (b.x - o.x)
    d1 = cross(b1, b2, a1)
    d2 = cross(b1, b2, a2)
    d3 = cross(a1, a2, b1)
    d4 = cross(a1, a2, b2)
    return ((d1 > 0 and d2 < 0) or (d1 < 0 and d2 > 0)) and \
           ((d3 > 0 and d4 < 0) or (d3 < 0 and d4 > 0))


# =============================================================================
# CANVAS STATE MANAGER
# =============================================================================

class LayerManager:
    def __init__(self, max_layers=CanvasConfig.MAX_LAYERS):
        self.layers: List[Layer] = [Layer(layer_id=0, name="Layer 1")]
        self.active_layer_id: int = 0
        self.max_layers = max_layers

    def add_layer(self):
        if len(self.layers) >= self.max_layers:
            return None
        new_id = max(l.layer_id for l in self.layers) + 1
        layer = Layer(layer_id=new_id, name=f"Layer {new_id + 1}")
        self.layers.append(layer)
        self.active_layer_id = new_id
        return layer

    def remove_layer(self, layer_id):
        if len(self.layers) <= 1:
            return False
        self.layers = [l for l in self.layers if l.layer_id != layer_id]
        if self.active_layer_id == layer_id:
            self.active_layer_id = self.layers[0].layer_id
        return True

    def toggle_visibility(self, layer_id):
        for l in self.layers:
            if l.layer_id == layer_id:
                l.visible = not l.visible
                break

    def cycle_active_layer(self):
        ids = [l.layer_id for l in self.layers]
        if not ids: return
        idx = ids.index(self.active_layer_id)
        self.active_layer_id = ids[(idx + 1) % len(ids)]

    def get_active_layer(self):
        for l in self.layers:
            if l.layer_id == self.active_layer_id:
                return l
        return self.layers[0]

    def get_visible_layer_ids(self):
        return {l.layer_id for l in self.layers if l.visible}


class CanvasStateManager:
    def __init__(self):
        self.objects: List[CanvasObject] = []
        self.strokes: List[Stroke] = []
        self.next_object_id = 0
        self.layer_manager = LayerManager()
        self.mode = InteractionMode.IDLE
        self.selected_object: Optional[CanvasObject] = None
        self.preview_object: Optional[CanvasObject] = None
        self.current_stroke: Optional[Stroke] = None
        self.stroke_color = (255, 255, 255)
        self.stroke_thickness = 3
        self._smoothed_pressure: float = 1.0
        self.eraser_radius = 20
        self.cut_start_point: Optional[Point] = None
        self.cut_end_point: Optional[Point] = None
        self.is_cutting = False
        self.interaction_start_point: Optional[Point] = None
        self.last_interaction_point: Optional[Point] = None
        self.shape_anchor: Optional[Point] = None
        self.preview_shape_type: Optional[ShapeType] = None
        self.undo_stack: List[Dict] = []
        self.redo_stack: List[Dict] = []
        self.max_undo = 50

    def _generate_id(self):
        obj_id = self.next_object_id
        self.next_object_id += 1
        return obj_id

    def _save_state(self):
        state = {'objects': copy.deepcopy(self.objects), 'strokes': copy.deepcopy(self.strokes)}
        self.undo_stack.append(state)
        if len(self.undo_stack) > self.max_undo:
            self.undo_stack.pop(0)
        self.redo_stack.clear()

    def undo(self):
        if self.undo_stack:
            self.redo_stack.append({'objects': copy.deepcopy(self.objects), 'strokes': copy.deepcopy(self.strokes)})
            state = self.undo_stack.pop()
            self.objects = state['objects']
            self.strokes = state['strokes']
            return True
        return False

    def redo(self):
        if self.redo_stack:
            self.undo_stack.append({'objects': copy.deepcopy(self.objects), 'strokes': copy.deepcopy(self.strokes)})
            state = self.redo_stack.pop()
            self.objects = state['objects']
            self.strokes = state['strokes']
            return True
        return False

    # Drawing
    def start_drawing(self, point, color, thickness):
        self._save_state()
        self.mode = InteractionMode.DRAWING
        self._smoothed_pressure = point.pressure
        actual_thickness = self._pressure_to_thickness(point.pressure) if CanvasConfig.PRESSURE_ENABLED else thickness
        self.current_stroke = Stroke(points=[point], color=color, thickness=actual_thickness,
                                     layer_id=self.layer_manager.active_layer_id)

    def continue_drawing(self, point):
        if self.current_stroke is not None and self.current_stroke.points:
            last = self.current_stroke.points[-1]
            if last.distance_to(point) > 2:
                alpha = CanvasConfig.PRESSURE_SMOOTHING
                self._smoothed_pressure = alpha * point.pressure + (1 - alpha) * self._smoothed_pressure
                point.pressure = self._smoothed_pressure
                self.current_stroke.points.append(point)

    def _pressure_to_thickness(self, pressure):
        t = max(0.0, min(1.0, pressure - 0.5))
        return max(1, int(CanvasConfig.PRESSURE_MIN_THICKNESS + t * (CanvasConfig.PRESSURE_MAX_THICKNESS - CanvasConfig.PRESSURE_MIN_THICKNESS)))

    def end_drawing(self):
        if self.current_stroke is not None and len(self.current_stroke.points) > 1:
            self.strokes.append(self.current_stroke)
        self.current_stroke = None
        self.mode = InteractionMode.IDLE

    # Eraser
    def erase_at(self, point, radius=None):
        if radius is None: radius = self.eraser_radius
        self.mode = InteractionMode.ERASING
        erased = False
        active_layer = self.layer_manager.active_layer_id
        to_remove = [s for s in self.strokes if s.layer_id == active_layer and any(sp.distance_to(point) < radius for sp in s.points)]
        if to_remove:
            self._save_state(); erased = True
            for s in to_remove:
                if s in self.strokes: self.strokes.remove(s)
        obj_remove = [o for o in self.objects if o.layer_id == active_layer and self._hit_test(o, point)]
        if obj_remove:
            if not erased: self._save_state()
            for o in obj_remove:
                if o in self.objects: self.objects.remove(o)

    # Shape preview
    def start_shape_preview(self, shape_type, anchor, color):
        self.mode = InteractionMode.SHAPE_PREVIEW
        self.preview_shape_type = shape_type
        self.shape_anchor = anchor
        self.stroke_color = color
        self.preview_object = None

    def update_shape_preview(self, current_point):
        if self.shape_anchor is None: return
        anchor = self.shape_anchor
        dist = anchor.distance_to(current_point)
        layer = self.layer_manager.active_layer_id
        color = self.stroke_color
        st = self.preview_shape_type

        if st == ShapeType.CIRCLE:
            self.preview_object = CanvasObject(obj_id=-1, shape_type=ShapeType.CIRCLE, points=[anchor], color=color, center=anchor, radius=dist, layer_id=layer)
        elif st == ShapeType.RECTANGLE:
            w = abs(current_point.x - anchor.x); h = abs(current_point.y - anchor.y)
            c = Point((anchor.x + current_point.x) / 2, (anchor.y + current_point.y) / 2)
            self.preview_object = CanvasObject(obj_id=-1, shape_type=ShapeType.RECTANGLE, points=[anchor, current_point], color=color, center=c, width=w, height=h, layer_id=layer)
        elif st == ShapeType.TRIANGLE:
            verts = _regular_polygon_vertices(anchor, dist, 3)
            self.preview_object = CanvasObject(obj_id=-1, shape_type=ShapeType.TRIANGLE, points=verts, color=color, center=anchor, radius=dist, vertices=verts, layer_id=layer)
        elif st == ShapeType.PENTAGON:
            verts = _regular_polygon_vertices(anchor, dist, 5)
            self.preview_object = CanvasObject(obj_id=-1, shape_type=ShapeType.PENTAGON, points=verts, color=color, center=anchor, radius=dist, vertices=verts, layer_id=layer)
        elif st == ShapeType.HEXAGON:
            verts = _regular_polygon_vertices(anchor, dist, 6)
            self.preview_object = CanvasObject(obj_id=-1, shape_type=ShapeType.HEXAGON, points=verts, color=color, center=anchor, radius=dist, vertices=verts, layer_id=layer)
        elif st == ShapeType.STAR:
            verts = _star_vertices(anchor, dist)
            self.preview_object = CanvasObject(obj_id=-1, shape_type=ShapeType.STAR, points=verts, color=color, center=anchor, radius=dist, vertices=verts, layer_id=layer)
        elif st == ShapeType.ELLIPSE:
            rx = abs(current_point.x - anchor.x); ry = abs(current_point.y - anchor.y)
            self.preview_object = CanvasObject(obj_id=-1, shape_type=ShapeType.ELLIPSE, points=[anchor], color=color, center=anchor, width=rx * 2, height=ry * 2, layer_id=layer)
        elif st == ShapeType.DIAMOND:
            w = abs(current_point.x - anchor.x) * 2; h = abs(current_point.y - anchor.y) * 2
            verts = _diamond_vertices(anchor, w, h)
            self.preview_object = CanvasObject(obj_id=-1, shape_type=ShapeType.DIAMOND, points=verts, color=color, center=anchor, width=w, height=h, vertices=verts, layer_id=layer)
        elif st == ShapeType.LINE:
            self.preview_object = CanvasObject(obj_id=-1, shape_type=ShapeType.LINE, points=[anchor, current_point], color=color, thickness=self.stroke_thickness, layer_id=layer)
        elif st == ShapeType.CUBE:
            self.preview_object = CanvasObject(obj_id=-1, shape_type=ShapeType.CUBE, points=[], color=color, center=anchor, radius=dist, layer_id=layer)
        elif st == ShapeType.CYLINDER:
            h = abs(current_point.y - anchor.y) * 2 if abs(current_point.y - anchor.y) > 10 else dist
            self.preview_object = CanvasObject(obj_id=-1, shape_type=ShapeType.CYLINDER, points=[], color=color, center=anchor, radius=dist * 0.5, height=h, layer_id=layer)
        elif st == ShapeType.CONE:
            h = abs(current_point.y - anchor.y) * 2 if abs(current_point.y - anchor.y) > 10 else dist
            self.preview_object = CanvasObject(obj_id=-1, shape_type=ShapeType.CONE, points=[], color=color, center=anchor, radius=dist * 0.5, height=h, layer_id=layer)
        elif st == ShapeType.SPHERE:
            self.preview_object = CanvasObject(obj_id=-1, shape_type=ShapeType.SPHERE, points=[], color=color, center=anchor, radius=dist, layer_id=layer)
        elif st == ShapeType.PYRAMID:
            self.preview_object = CanvasObject(obj_id=-1, shape_type=ShapeType.PYRAMID, points=[], color=color, center=anchor, radius=dist, height=dist, layer_id=layer)
        elif st == ShapeType.PRISM:
            h = abs(current_point.y - anchor.y) * 2 if abs(current_point.y - anchor.y) > 10 else dist
            self.preview_object = CanvasObject(obj_id=-1, shape_type=ShapeType.PRISM, points=[], color=color, center=anchor, radius=dist * 0.6, height=h, layer_id=layer)

    def finalize_shape(self):
        if self.preview_object is not None:
            self._save_state()
            self.preview_object.obj_id = self._generate_id()
            self.objects.append(self.preview_object)
            self.preview_object = None
        self.mode = InteractionMode.IDLE
        self.shape_anchor = None

    def cancel_shape(self):
        self.preview_object = None
        self.mode = InteractionMode.IDLE
        self.shape_anchor = None

    # Selection & hit test
    def find_object_at(self, point):
        visible = self.layer_manager.get_visible_layer_ids()
        for obj in reversed(self.objects):
            if obj.layer_id in visible and self._hit_test(obj, point):
                return obj
        return None

    def _hit_test(self, obj, point):
        sr = CanvasConfig.SELECTION_RADIUS
        if obj.vertices and obj.shape_type in (ShapeType.TRIANGLE, ShapeType.PENTAGON, ShapeType.HEXAGON,
                                                ShapeType.STAR, ShapeType.DIAMOND):
            if _point_in_polygon(point, obj.vertices): return True
            for i in range(len(obj.vertices)):
                a = obj.vertices[i]; b = obj.vertices[(i + 1) % len(obj.vertices)]
                if self._point_to_line_distance(point, a, b) < sr: return True
            return False
        if obj.shape_type in (ShapeType.CIRCLE, ShapeType.HALF_CIRCLE, ShapeType.SPHERE):
            if obj.center and obj.radius: return obj.center.distance_to(point) <= obj.radius + sr
        if obj.shape_type == ShapeType.ELLIPSE:
            if obj.center and obj.width and obj.height:
                rx, ry = obj.width / 2 + sr, obj.height / 2 + sr
                dx = point.x - obj.center.x; dy = point.y - obj.center.y
                return (dx * dx) / (rx * rx) + (dy * dy) / (ry * ry) <= 1.0
        if obj.shape_type == ShapeType.RECTANGLE:
            if obj.center and obj.width and obj.height:
                return abs(point.x - obj.center.x) <= obj.width / 2 + sr and abs(point.y - obj.center.y) <= obj.height / 2 + sr
        if obj.shape_type == ShapeType.LINE and len(obj.points) >= 2:
            return self._point_to_line_distance(point, obj.points[0], obj.points[1]) < sr
        if obj.shape_type in (ShapeType.CUBE, ShapeType.CYLINDER, ShapeType.CONE, ShapeType.PYRAMID, ShapeType.PRISM):
            if obj.center and obj.radius:
                half = max(obj.radius, (obj.height or obj.radius) / 2) + sr
                return abs(point.x - obj.center.x) <= half and abs(point.y - obj.center.y) <= half
        return False

    def _point_to_line_distance(self, point, ls, le):
        dx = le.x - ls.x; dy = le.y - ls.y
        if dx == 0 and dy == 0: return point.distance_to(ls)
        t = max(0, min(1, ((point.x - ls.x) * dx + (point.y - ls.y) * dy) / (dx * dx + dy * dy)))
        return math.sqrt((point.x - (ls.x + t * dx))**2 + (point.y - (ls.y + t * dy))**2)

    def select_object(self, obj):
        self.deselect_all()
        obj.state = ObjectState.SELECTED
        self.selected_object = obj
        self.mode = InteractionMode.SELECTING

    def deselect_all(self):
        for obj in self.objects: obj.state = ObjectState.IDLE
        self.selected_object = None

    # Move
    def start_moving(self, point):
        if self.selected_object:
            self.mode = InteractionMode.MOVING
            self.interaction_start_point = point
            self.last_interaction_point = point
            self.selected_object.state = ObjectState.MOVING

    def continue_moving(self, point):
        if self.selected_object and self.last_interaction_point:
            dx = point.x - self.last_interaction_point.x
            dy = point.y - self.last_interaction_point.y
            if self.selected_object.center:
                self.selected_object.center.x += dx; self.selected_object.center.y += dy
            for p in self.selected_object.points: p.x += dx; p.y += dy
            if self.selected_object.vertices:
                for v in self.selected_object.vertices: v.x += dx; v.y += dy
            self.last_interaction_point = point

    def end_moving(self):
        if self.selected_object: self.selected_object.state = ObjectState.SELECTED
        self.mode = InteractionMode.SELECTING if self.selected_object else InteractionMode.IDLE

    # Scaling
    def start_scaling(self, pinch_y):
        if self.selected_object:
            self.mode = InteractionMode.SCALING
            self.selected_object.state = ObjectState.SCALING
            self._last_pinch_y = pinch_y
            self._pinch_velocity_history = deque(maxlen=5)
            self._scale_sensitivity = 0.005

    def continue_scaling(self, pinch_y):
        if self.selected_object and hasattr(self, '_last_pinch_y'):
            delta = self._last_pinch_y - pinch_y
            self._last_pinch_y = pinch_y
            self._pinch_velocity_history.append(delta)
            smooth_delta = sum(self._pinch_velocity_history) / len(self._pinch_velocity_history) if len(self._pinch_velocity_history) >= 2 else delta
            scale_change = smooth_delta * self._scale_sensitivity
            current_scale = self.selected_object.scale
            new_scale = max(0.1, min(10.0, current_scale + scale_change))
            ratio = new_scale / current_scale if current_scale > 0 else 1.0
            if self.selected_object.radius is not None: self.selected_object.radius *= ratio
            if self.selected_object.width is not None: self.selected_object.width *= ratio
            if self.selected_object.height is not None: self.selected_object.height *= ratio
            if self.selected_object.vertices and self.selected_object.center:
                cx, cy = self.selected_object.center.x, self.selected_object.center.y
                for v in self.selected_object.vertices: v.x = cx + (v.x - cx) * ratio; v.y = cy + (v.y - cy) * ratio
            self.selected_object.scale = new_scale

    def end_scaling(self):
        if self.selected_object: self.selected_object.state = ObjectState.SELECTED
        self.mode = InteractionMode.SELECTING if self.selected_object else InteractionMode.IDLE

    # Rotation
    def start_rotating(self):
        if self.selected_object:
            self.mode = InteractionMode.ROTATING
            self.selected_object.state = ObjectState.ROTATING

    def continue_rotating(self, angle_delta):
        if self.selected_object:
            self.selected_object.rotation += angle_delta * CanvasConfig.ROTATION_SENSITIVITY
            self.selected_object.rotation %= 360.0
            if self.selected_object.vertices and self.selected_object.center:
                rad = math.radians(angle_delta * CanvasConfig.ROTATION_SENSITIVITY)
                cos_a, sin_a = math.cos(rad), math.sin(rad)
                cx, cy = self.selected_object.center.x, self.selected_object.center.y
                for v in self.selected_object.vertices:
                    dx, dy = v.x - cx, v.y - cy
                    v.x = cx + dx * cos_a - dy * sin_a
                    v.y = cy + dx * sin_a + dy * cos_a

    def end_rotating(self):
        if self.selected_object: self.selected_object.state = ObjectState.SELECTED
        self.mode = InteractionMode.SELECTING if self.selected_object else InteractionMode.IDLE

    # Knife
    def start_cutting(self, point):
        self.mode = InteractionMode.CUTTING
        self.cut_start_point = point; self.cut_end_point = point; self.is_cutting = True

    def continue_cutting(self, point):
        if self.is_cutting: self.cut_end_point = point

    def end_cutting(self):
        if self.cut_start_point and self.cut_end_point:
            for obj in list(self.objects):
                if self._line_intersects_shape(self.cut_start_point, self.cut_end_point, obj):
                    self._cut_shape(obj)
        self.cut_start_point = None; self.cut_end_point = None
        self.is_cutting = False; self.mode = InteractionMode.IDLE

    def _line_intersects_shape(self, p1, p2, obj):
        if obj.vertices and obj.shape_type in (ShapeType.TRIANGLE, ShapeType.PENTAGON,
                                                ShapeType.HEXAGON, ShapeType.STAR, ShapeType.DIAMOND):
            n = len(obj.vertices)
            for i in range(n):
                if _segments_intersect(p1, p2, obj.vertices[i], obj.vertices[(i + 1) % n]): return True
            return False
        if obj.shape_type in (ShapeType.CIRCLE, ShapeType.SPHERE):
            if obj.center and obj.radius: return self._point_to_line_distance(obj.center, p1, p2) < obj.radius
        if obj.shape_type == ShapeType.RECTANGLE:
            if obj.center and obj.width and obj.height: return self._point_to_line_distance(obj.center, p1, p2) < max(obj.width, obj.height) / 2
        if obj.shape_type in (ShapeType.CUBE, ShapeType.CYLINDER, ShapeType.CONE, ShapeType.PYRAMID, ShapeType.PRISM):
            if obj.center and obj.radius:
                r = max(obj.radius, (obj.height or obj.radius) / 2)
                return self._point_to_line_distance(obj.center, p1, p2) < r
        return False

    def _cut_shape(self, obj):
        self._save_state()
        cut_angle = math.degrees(math.atan2(self.cut_end_point.y - self.cut_start_point.y,
                                             self.cut_end_point.x - self.cut_start_point.x))
        if obj.shape_type == ShapeType.CIRCLE and obj.center and obj.radius:
            half1 = CanvasObject(obj_id=self._generate_id(), shape_type=ShapeType.HALF_CIRCLE, points=[],
                                 color=obj.color, thickness=obj.thickness, center=Point(obj.center.x, obj.center.y),
                                 radius=obj.radius, start_angle=cut_angle, end_angle=cut_angle + 180, layer_id=obj.layer_id)
            half2 = CanvasObject(obj_id=self._generate_id(), shape_type=ShapeType.HALF_CIRCLE, points=[],
                                 color=obj.color, thickness=obj.thickness, center=Point(obj.center.x, obj.center.y),
                                 radius=obj.radius, start_angle=cut_angle + 180, end_angle=cut_angle + 360, layer_id=obj.layer_id)
            if obj in self.objects: self.objects.remove(obj)
            self.objects.extend([half1, half2])
        elif obj.shape_type == ShapeType.RECTANGLE and obj.center and obj.width and obj.height:
            is_h = abs(self.cut_end_point.x - self.cut_start_point.x) > abs(self.cut_end_point.y - self.cut_start_point.y)
            if is_h:
                c1 = Point(obj.center.x, obj.center.y - obj.height / 4)
                c2 = Point(obj.center.x, obj.center.y + obj.height / 4)
                halves = [CanvasObject(obj_id=self._generate_id(), shape_type=ShapeType.RECTANGLE, points=[], color=obj.color, center=c1, width=obj.width, height=obj.height / 2, layer_id=obj.layer_id),
                          CanvasObject(obj_id=self._generate_id(), shape_type=ShapeType.RECTANGLE, points=[], color=obj.color, center=c2, width=obj.width, height=obj.height / 2, layer_id=obj.layer_id)]
            else:
                c1 = Point(obj.center.x - obj.width / 4, obj.center.y)
                c2 = Point(obj.center.x + obj.width / 4, obj.center.y)
                halves = [CanvasObject(obj_id=self._generate_id(), shape_type=ShapeType.RECTANGLE, points=[], color=obj.color, center=c1, width=obj.width / 2, height=obj.height, layer_id=obj.layer_id),
                          CanvasObject(obj_id=self._generate_id(), shape_type=ShapeType.RECTANGLE, points=[], color=obj.color, center=c2, width=obj.width / 2, height=obj.height, layer_id=obj.layer_id)]
            if obj in self.objects: self.objects.remove(obj)
            self.objects.extend(halves)

    # Save/Load
    def save_canvas_png(self, canvas_image, filename=None):
        os.makedirs(CanvasConfig.SAVE_DIR, exist_ok=True)
        if filename is None: filename = f"canvas_{time.strftime('%Y%m%d_%H%M%S')}.png"
        filepath = os.path.join(CanvasConfig.SAVE_DIR, filename)
        cv2.imwrite(filepath, canvas_image)
        return filepath

    def save_canvas_json(self, filename=None):
        os.makedirs(CanvasConfig.SAVE_DIR, exist_ok=True)
        if filename is None: filename = f"canvas_{time.strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(CanvasConfig.SAVE_DIR, filename)
        data = {'objects': [], 'strokes': [],
                'layers': [{'id': l.layer_id, 'name': l.name, 'visible': l.visible} for l in self.layer_manager.layers]}
        for obj in self.objects:
            data['objects'].append({
                'shape_type': obj.shape_type.name, 'color': list(obj.color), 'thickness': obj.thickness,
                'scale': obj.scale, 'rotation': obj.rotation, 'layer_id': obj.layer_id,
                'center': [obj.center.x, obj.center.y] if obj.center else None,
                'radius': obj.radius, 'width': obj.width, 'height': obj.height,
                'start_angle': obj.start_angle, 'end_angle': obj.end_angle,
                'points': [[p.x, p.y, p.pressure] for p in obj.points],
                'vertices': [[v.x, v.y] for v in obj.vertices] if obj.vertices else None})
        for stroke in self.strokes:
            data['strokes'].append({
                'color': list(stroke.color), 'thickness': stroke.thickness, 'layer_id': stroke.layer_id,
                'points': [[p.x, p.y, p.pressure] for p in stroke.points]})
        with open(filepath, 'w') as f: json.dump(data, f, indent=2)
        return filepath

    def clear_canvas(self):
        self._save_state()
        self.objects.clear(); self.strokes.clear()
        self.deselect_all(); self.mode = InteractionMode.IDLE

    def delete_selected(self):
        if self.selected_object:
            self._save_state()
            if self.selected_object in self.objects: self.objects.remove(self.selected_object)
            self.selected_object = None; self.mode = InteractionMode.IDLE


# =============================================================================
# RENDERING ENGINE
# =============================================================================

class CanvasRenderingEngine:
    def __init__(self, width=CanvasConfig.CANVAS_WIDTH, height=CanvasConfig.CANVAS_HEIGHT):
        self.width = width
        self.height = height
        self.background = self._create_background()

    def _create_background(self):
        bg = np.full((self.height, self.width, 3), CanvasConfig.BACKGROUND_COLOR, dtype=np.uint8)
        grid_color = (50, 50, 50)
        for x in range(0, self.width, 50):
            cv2.line(bg, (x, 0), (x, self.height), grid_color, 1)
        for y in range(0, self.height, 50):
            cv2.line(bg, (0, y), (self.width, y), grid_color, 1)
        return bg

    def render(self, state, toolbar=None, camera_frame=None, cursor=None,
               current_tool=None, fps=0.0, show_camera=True, camera_opacity=0.3,
               gesture_confidence=1.0, edge_factor=0.0, notification=""):
        canvas = self.background.copy()
        if show_camera and camera_frame is not None:
            camera_resized = cv2.resize(camera_frame, (self.width, self.height))
            canvas = cv2.addWeighted(canvas, 1 - camera_opacity, camera_resized, camera_opacity, 0)
        visible_layers = state.layer_manager.get_visible_layer_ids()
        for stroke in state.strokes:
            if stroke.layer_id in visible_layers: self._render_stroke(canvas, stroke)
        if state.current_stroke: self._render_stroke(canvas, state.current_stroke)
        for obj in state.objects:
            if obj.layer_id in visible_layers: self._render_object(canvas, obj)
        if state.preview_object: self._render_object(canvas, state.preview_object, preview=True)
        if state.is_cutting and state.cut_start_point and state.cut_end_point:
            cv2.line(canvas, state.cut_start_point.to_tuple(), state.cut_end_point.to_tuple(), (0, 0, 255), 2, cv2.LINE_AA)
        if toolbar: toolbar.render(canvas)
        if cursor: self._render_cursor(canvas, cursor, current_tool, state.mode)
        self._render_status(canvas, state, toolbar, fps)
        if notification:
            text_size = cv2.getTextSize(notification, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
            x = (self.width - text_size[0]) // 2
            cv2.rectangle(canvas, (x - 15, 35), (x + text_size[0] + 15, 70), (40, 40, 40), -1)
            cv2.rectangle(canvas, (x - 15, 35), (x + text_size[0] + 15, 70), (100, 200, 100), 2)
            cv2.putText(canvas, notification, (x, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (100, 255, 100), 2)
        return canvas

    def _render_stroke(self, canvas, stroke):
        if len(stroke.points) < 2: return
        if CanvasConfig.PRESSURE_ENABLED and len(stroke.points) > 2:
            for i in range(len(stroke.points) - 1):
                p1 = stroke.points[i]; p2 = stroke.points[i + 1]
                pressure = (p1.pressure + p2.pressure) / 2.0
                thickness = max(1, int(stroke.thickness * max(0.3, min(2.0, pressure))))
                cv2.line(canvas, p1.to_tuple(), p2.to_tuple(), stroke.color, thickness, cv2.LINE_AA)
        else:
            points = np.array([p.to_tuple() for p in stroke.points], dtype=np.int32)
            cv2.polylines(canvas, [points], False, stroke.color, stroke.thickness, cv2.LINE_AA)

    def _render_object(self, canvas, obj, preview=False):
        color = obj.color
        thickness = obj.thickness if obj.thickness else 3
        if preview: thickness = max(1, thickness - 1)
        if obj.state in (ObjectState.SELECTED, ObjectState.ROTATING):
            self._render_selection_outline(canvas, obj)
        st = obj.shape_type
        if st == ShapeType.CIRCLE and obj.center and obj.radius:
            r = max(1, int(obj.radius))
            cv2.circle(canvas, obj.center.to_tuple(), r, color, thickness, cv2.LINE_AA)
            if not preview:
                overlay = canvas.copy(); cv2.circle(overlay, obj.center.to_tuple(), r, color, -1, cv2.LINE_AA)
                cv2.addWeighted(overlay, 0.3, canvas, 0.7, 0, canvas)
        elif st == ShapeType.HALF_CIRCLE and obj.center and obj.radius:
            c = obj.center.to_tuple(); r = max(1, int(obj.radius))
            cv2.ellipse(canvas, c, (r, r), 0, int(obj.start_angle), int(obj.end_angle), color, thickness, cv2.LINE_AA)
        elif st == ShapeType.RECTANGLE and obj.center and obj.width and obj.height:
            hw = int(obj.width / 2); hh = int(obj.height / 2)
            pt1 = (int(obj.center.x - hw), int(obj.center.y - hh))
            pt2 = (int(obj.center.x + hw), int(obj.center.y + hh))
            cv2.rectangle(canvas, pt1, pt2, color, thickness)
            if not preview:
                overlay = canvas.copy(); cv2.rectangle(overlay, pt1, pt2, color, -1)
                cv2.addWeighted(overlay, 0.3, canvas, 0.7, 0, canvas)
        elif st in (ShapeType.TRIANGLE, ShapeType.PENTAGON, ShapeType.HEXAGON,
                     ShapeType.STAR, ShapeType.DIAMOND, ShapeType.POLYGON):
            verts = obj.vertices if obj.vertices else obj.points
            if verts and len(verts) >= 3:
                pts = np.array([v.to_tuple() for v in verts], dtype=np.int32)
                cv2.polylines(canvas, [pts], True, color, thickness, cv2.LINE_AA)
                if not preview:
                    overlay = canvas.copy(); cv2.fillPoly(overlay, [pts], color)
                    cv2.addWeighted(overlay, 0.3, canvas, 0.7, 0, canvas)
        elif st == ShapeType.ELLIPSE and obj.center and obj.width and obj.height:
            axes = (max(1, int(obj.width / 2)), max(1, int(obj.height / 2)))
            cv2.ellipse(canvas, obj.center.to_tuple(), axes, 0, 0, 360, color, thickness, cv2.LINE_AA)
            if not preview:
                overlay = canvas.copy(); cv2.ellipse(overlay, obj.center.to_tuple(), axes, 0, 0, 360, color, -1, cv2.LINE_AA)
                cv2.addWeighted(overlay, 0.3, canvas, 0.7, 0, canvas)
        elif st == ShapeType.LINE and len(obj.points) >= 2:
            cv2.line(canvas, obj.points[0].to_tuple(), obj.points[1].to_tuple(), color, thickness, cv2.LINE_AA)
        elif st == ShapeType.CUBE and obj.center and obj.radius:
            for edge in _cube_wireframe(obj.center, obj.radius * 2):
                cv2.line(canvas, edge[0].to_tuple(), edge[1].to_tuple(), color, thickness, cv2.LINE_AA)
        elif st == ShapeType.CYLINDER and obj.center and obj.radius:
            h = obj.height if obj.height else obj.radius * 2
            info = _cylinder_wireframe(obj.center, obj.radius, h)
            cv2.ellipse(canvas, info['top_center'], info['axes'], 0, 0, 360, color, thickness, cv2.LINE_AA)
            cv2.ellipse(canvas, info['bot_center'], info['axes'], 0, 0, 360, color, thickness, cv2.LINE_AA)
            cv2.line(canvas, info['left'][0], info['left'][1], color, thickness, cv2.LINE_AA)
            cv2.line(canvas, info['right'][0], info['right'][1], color, thickness, cv2.LINE_AA)
        elif st == ShapeType.CONE and obj.center and obj.radius:
            h = obj.height if obj.height else obj.radius * 2
            info = _cone_wireframe(obj.center, obj.radius, h)
            cv2.ellipse(canvas, info['base_center'], info['axes'], 0, 0, 360, color, thickness, cv2.LINE_AA)
            cv2.line(canvas, info['left'][0], info['left'][1], color, thickness, cv2.LINE_AA)
            cv2.line(canvas, info['right'][0], info['right'][1], color, thickness, cv2.LINE_AA)
        elif st == ShapeType.SPHERE and obj.center and obj.radius:
            r = max(1, int(obj.radius))
            cv2.circle(canvas, obj.center.to_tuple(), r, color, thickness, cv2.LINE_AA)
            cv2.ellipse(canvas, obj.center.to_tuple(), (r, max(1, int(r * 0.35))), 0, 0, 360, color, max(1, thickness - 1), cv2.LINE_AA)
            cv2.ellipse(canvas, obj.center.to_tuple(), (max(1, int(r * 0.35)), r), 0, 0, 360, color, max(1, thickness - 1), cv2.LINE_AA)
        elif st == ShapeType.PYRAMID and obj.center and obj.radius:
            h = obj.height if obj.height else obj.radius * 2
            for edge in _pyramid_wireframe(obj.center, obj.radius * 2, h):
                cv2.line(canvas, edge[0].to_tuple(), edge[1].to_tuple(), color, thickness, cv2.LINE_AA)
        elif st == ShapeType.PRISM and obj.center and obj.radius:
            h = obj.height if obj.height else obj.radius * 2
            for edge in _prism_wireframe(obj.center, obj.radius * 2, h):
                cv2.line(canvas, edge[0].to_tuple(), edge[1].to_tuple(), color, thickness, cv2.LINE_AA)

    def _render_selection_outline(self, canvas, obj):
        hc = (0, 255, 255) if obj.state != ObjectState.ROTATING else (255, 128, 0)
        if obj.vertices and obj.shape_type in (ShapeType.TRIANGLE, ShapeType.PENTAGON, ShapeType.HEXAGON, ShapeType.STAR, ShapeType.DIAMOND, ShapeType.POLYGON):
            pts = np.array([v.to_tuple() for v in obj.vertices], dtype=np.int32)
            cv2.polylines(canvas, [pts], True, hc, 2, cv2.LINE_AA); return
        if obj.shape_type in (ShapeType.CIRCLE, ShapeType.HALF_CIRCLE, ShapeType.SPHERE):
            if obj.center and obj.radius: cv2.circle(canvas, obj.center.to_tuple(), int(obj.radius + 10), hc, 2, cv2.LINE_AA)
        elif obj.shape_type in (ShapeType.RECTANGLE, ShapeType.ELLIPSE):
            if obj.center and obj.width and obj.height:
                hw = int(obj.width / 2) + 10; hh = int(obj.height / 2) + 10
                cv2.rectangle(canvas, (int(obj.center.x - hw), int(obj.center.y - hh)),
                              (int(obj.center.x + hw), int(obj.center.y + hh)), hc, 2)
        elif obj.shape_type in (ShapeType.CUBE, ShapeType.CYLINDER, ShapeType.CONE, ShapeType.PYRAMID, ShapeType.PRISM):
            if obj.center and obj.radius:
                half = max(obj.radius, (obj.height or obj.radius * 2) / 2) + 10
                cv2.rectangle(canvas, (int(obj.center.x - half), int(obj.center.y - half)),
                              (int(obj.center.x + half), int(obj.center.y + half)), hc, 2)

    def _render_cursor(self, canvas, cursor, current_tool, mode):
        pos = cursor.to_tuple()
        if current_tool == ToolType.PEN:
            cv2.circle(canvas, pos, 5, (255, 255, 255), -1); cv2.circle(canvas, pos, 7, (100, 100, 100), 2)
        elif current_tool == ToolType.ERASER:
            cv2.circle(canvas, pos, 20, (255, 100, 100), 2)
            cv2.line(canvas, (pos[0] - 8, pos[1] - 8), (pos[0] + 8, pos[1] + 8), (255, 100, 100), 2)
            cv2.line(canvas, (pos[0] + 8, pos[1] - 8), (pos[0] - 8, pos[1] + 8), (255, 100, 100), 2)
        elif current_tool == ToolType.SELECT:
            cv2.line(canvas, (pos[0] - 15, pos[1]), (pos[0] + 15, pos[1]), (0, 255, 255), 2)
            cv2.line(canvas, (pos[0], pos[1] - 15), (pos[0], pos[1] + 15), (0, 255, 255), 2)
        elif current_tool == ToolType.KNIFE:
            cv2.line(canvas, (pos[0] - 10, pos[1] + 10), (pos[0] + 10, pos[1] - 10), (255, 0, 0), 3)
        elif current_tool in (ToolType.SHAPES_2D, ToolType.SHAPES_3D, ToolType.LINE):
            cv2.circle(canvas, pos, 8, (255, 200, 0), -1); cv2.circle(canvas, pos, 12, (255, 200, 0), 2)
        else:
            cv2.circle(canvas, pos, 10, (200, 200, 200), 2)

    def _render_status(self, canvas, state, toolbar, fps):
        x_off = self.width - 220; y = 30
        cv2.putText(canvas, f"FPS: {fps:.1f}", (x_off, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        y += 20
        cv2.putText(canvas, f"Objects: {len(state.objects)}  Strokes: {len(state.strokes)}", (x_off, y), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1)
        y += 18
        active = state.layer_manager.get_active_layer()
        cv2.putText(canvas, f"Layer: {active.name} ({len(state.layer_manager.layers)})", (x_off, y), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 200, 255), 1)
        y += 18
        cv2.putText(canvas, f"Undo: {len(state.undo_stack)}  Redo: {len(state.redo_stack)}", (x_off, y), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1)
        instructions = [
            "Point finger = tool | Pinch = select toolbar | Fist = cycle tool",
            "Thumbs up = color | Swipe L/R = Undo/Redo | Open palm = idle"
        ]
        for i, text in enumerate(instructions):
            cv2.putText(canvas, text, (self.width // 2 - 280, self.height - 40 + i * 18),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.35, (120, 120, 120), 1)


# =============================================================================
# INTERACTION CONTROLLER  (integration layer)
# =============================================================================

class CanvasInteractionController:
    """
    Self-contained controller: coordinates hand tracking, gesture recognition,
    coordinate mapping, canvas state management, and rendering.
    Accepts a BGR frame and returns a rendered canvas image (numpy array).
    """

    def __init__(self, canvas_width=None, canvas_height=None):
        w = canvas_width or CanvasConfig.CANVAS_WIDTH
        h = canvas_height or CanvasConfig.CANVAS_HEIGHT
        CanvasConfig.CANVAS_WIDTH = w
        CanvasConfig.CANVAS_HEIGHT = h
        self.hand_tracker = CanvasHandTracker()
        self.hand_tracker.initialize()
        self.gesture_recognizer = CanvasGestureRecognizer(self.hand_tracker)
        self.coord_mapper = CoordinateMappingLayer(canvas_width=w, canvas_height=h)
        self.canvas_state = CanvasStateManager()
        self.renderer = CanvasRenderingEngine(w, h)
        self.toolbar = UIToolbar()
        self.previous_gesture = GestureType.NONE
        self.gesture_just_started = False
        self.cursor_over_toolbar = False
        self.shape_start_point = None
        self.stable_gesture_count = 0
        self.skip_processing = False
        self.notification_text = ""
        self.notification_time = 0
        self.notification_duration = 2.0
        self._frame_times = deque(maxlen=30)
        self._last_frame_time = time.time()

    def cleanup(self):
        self.hand_tracker.release()

    def _show_notification(self, text, duration=2.0):
        self.notification_text = text
        self.notification_time = time.time()
        self.notification_duration = duration

    def _get_notification(self):
        if self.notification_text and time.time() - self.notification_time < self.notification_duration:
            return self.notification_text
        return None

    def process_frame(self, frame: np.ndarray) -> np.ndarray:
        """Process a BGR camera frame and return the rendered canvas image."""
        now = time.time()
        self._frame_times.append(now - self._last_frame_time)
        self._last_frame_time = now
        fps = 1.0 / (sum(self._frame_times) / len(self._frame_times)) if self._frame_times else 0

        hands_data = self.hand_tracker.process_frame(frame)
        gesture = None
        cursor = None
        gesture_confidence = 0.5
        edge_factor = 0.0

        if hands_data:
            hand = hands_data[0]
            raw_gesture = self.gesture_recognizer.recognize_gesture(hand)
            gesture = self.gesture_recognizer.apply_debounce(raw_gesture)
            gesture_confidence = gesture.confidence
            self.gesture_just_started = (gesture.gesture_type != self.previous_gesture)

            if CanvasConfig.FRAME_SKIP_ENABLED:
                if gesture.gesture_type == self.previous_gesture and gesture.gesture_type == GestureType.IDLE:
                    self.stable_gesture_count += 1
                else:
                    self.stable_gesture_count = 0
                self.skip_processing = self.stable_gesture_count > CanvasConfig.FRAME_SKIP_STABLE_COUNT

            if not self.skip_processing:
                index_pos = hand.fingertip_positions.get('index')
                if index_pos:
                    cursor_raw = Point(index_pos.x, index_pos.y)
                    edge_factor = self.coord_mapper.get_edge_factor(cursor_raw)
                    cursor = self.coord_mapper.map_and_smooth(cursor_raw, "cursor")
                    self.cursor_over_toolbar = self.toolbar.check_hover(int(cursor_raw.x), int(cursor_raw.y))

                    if self.cursor_over_toolbar and gesture.gesture_type in (GestureType.PINCH, GestureType.SELECT):
                        point = Point(cursor_raw.x, cursor_raw.y)
                        shape_picked = self.toolbar.hit_test_shape_picker(point)
                        if shape_picked is not None:
                            self.toolbar.select_shape(shape_picked)
                            self._show_notification(f"Shape: {SHAPE_DISPLAY_NAMES.get(shape_picked, shape_picked.name)}")
                        else:
                            tool = self.toolbar.hit_test(point)
                            color_idx = self.toolbar.hit_test_color(point)
                            if tool is not None:
                                self.toolbar.select_tool(tool)
                                self._show_notification(f"Tool: {tool.name}")
                                self._end_all_operations()
                            elif color_idx is not None:
                                self.toolbar.select_color(color_idx)
                                self._show_notification("Color changed")
                        self.previous_gesture = gesture.gesture_type
                    elif not self.cursor_over_toolbar:
                        self._handle_tool_action(gesture, hand, cursor)
        else:
            self._handle_no_hands()

        notification = self._get_notification()
        rendered = self.renderer.render(
            state=self.canvas_state, toolbar=self.toolbar, camera_frame=frame,
            cursor=cursor, current_tool=self.toolbar.selected_tool,
            fps=fps, gesture_confidence=gesture_confidence,
            edge_factor=edge_factor, notification=notification or "")
        return rendered

    def _handle_tool_action(self, gesture, hand, cursor):
        gesture_type = gesture.gesture_type
        current_tool = self.toolbar.selected_tool
        current_mode = self.canvas_state.mode
        draw_point = cursor
        raw_draw = gesture.parameters.get('draw_point')
        if raw_draw and gesture_type == GestureType.DRAW:
            draw_point = Point(cursor.x, cursor.y, raw_draw.pressure)

        if gesture_type == GestureType.SWIPE_LEFT:
            if self.canvas_state.undo(): self._show_notification("Undo")
            self.previous_gesture = gesture_type; return
        if gesture_type == GestureType.SWIPE_RIGHT:
            if self.canvas_state.redo(): self._show_notification("Redo")
            self.previous_gesture = gesture_type; return

        if gesture_type == GestureType.THUMBS_UP and self.gesture_just_started:
            self.toolbar.cycle_color()
            names = ["White", "Red", "Green", "Blue", "Yellow", "Magenta", "Cyan"]
            idx = self.toolbar.selected_color_idx
            self._show_notification(f"Color: {names[idx] if idx < len(names) else 'Color'}")
            self.previous_gesture = gesture_type; return

        if gesture_type == GestureType.IDLE:
            if current_mode == InteractionMode.ROTATING:
                self.canvas_state.end_rotating()
                self.gesture_recognizer.reset_palm_tracking()
            self._end_all_operations()
            self.previous_gesture = gesture_type; return

        if gesture_type == GestureType.GRAB and self.gesture_just_started:
            if current_mode not in (InteractionMode.MOVING, InteractionMode.SCALING, InteractionMode.ROTATING):
                if current_tool == ToolType.MOVE and self.canvas_state.selected_object:
                    pass
                else:
                    self._cycle_tool()
                    self.previous_gesture = gesture_type; return

        # Per-tool handlers
        if current_tool == ToolType.PEN:
            if gesture_type == GestureType.DRAW:
                if self.gesture_just_started or current_mode != InteractionMode.DRAWING:
                    self.canvas_state.start_drawing(draw_point, self.toolbar.selected_color, self.toolbar.brush_size)
                else:
                    self.canvas_state.continue_drawing(draw_point)
            elif gesture_type == GestureType.IDLE and current_mode == InteractionMode.DRAWING:
                self.canvas_state.end_drawing()

        elif current_tool == ToolType.ERASER:
            if gesture_type == GestureType.DRAW:
                self.canvas_state.erase_at(draw_point, radius=20)

        elif current_tool in (ToolType.SHAPES_2D, ToolType.SHAPES_3D):
            shape = self.toolbar.get_current_shape()
            if gesture_type in (GestureType.DRAW, GestureType.PINCH):
                if self.gesture_just_started or current_mode != InteractionMode.SHAPE_PREVIEW:
                    self.canvas_state.start_shape_preview(shape, cursor, self.toolbar.selected_color)
                else:
                    self.canvas_state.update_shape_preview(cursor)
            elif gesture_type == GestureType.IDLE and current_mode == InteractionMode.SHAPE_PREVIEW:
                self.canvas_state.finalize_shape()

        elif current_tool == ToolType.LINE:
            if gesture_type in (GestureType.DRAW, GestureType.PINCH):
                if self.gesture_just_started or current_mode != InteractionMode.SHAPE_PREVIEW:
                    self.canvas_state.start_shape_preview(ShapeType.LINE, cursor, self.toolbar.selected_color)
                else:
                    self.canvas_state.update_shape_preview(cursor)
            elif gesture_type == GestureType.IDLE and current_mode == InteractionMode.SHAPE_PREVIEW:
                self.canvas_state.finalize_shape()

        elif current_tool == ToolType.SELECT:
            if gesture_type in (GestureType.PINCH, GestureType.SELECT):
                if self.gesture_just_started:
                    obj = self.canvas_state.find_object_at(cursor)
                    if obj:
                        self.canvas_state.select_object(obj)
                    else:
                        self.canvas_state.deselect_all()
            elif gesture_type == GestureType.IDLE and self.canvas_state.selected_object and current_mode == InteractionMode.SELECTING:
                palm_delta = gesture.parameters.get('palm_angle_delta', 0)
                if abs(palm_delta) > 0.5:
                    if current_mode != InteractionMode.ROTATING:
                        self.canvas_state.start_rotating()
                    self.canvas_state.continue_rotating(palm_delta)

        elif current_tool == ToolType.MOVE:
            if gesture_type in (GestureType.GRAB, GestureType.DRAW):
                grab_center = gesture.parameters.get('grab_center')
                if grab_center:
                    canvas_point = Point(grab_center.x * CanvasConfig.CANVAS_WIDTH, grab_center.y * CanvasConfig.CANVAS_HEIGHT)
                    canvas_point = self.coord_mapper.apply_smoothing(canvas_point, "grab")
                else:
                    canvas_point = draw_point
                if self.gesture_just_started:
                    if not self.canvas_state.selected_object:
                        obj = self.canvas_state.find_object_at(canvas_point)
                        if obj: self.canvas_state.select_object(obj)
                    if self.canvas_state.selected_object:
                        self.canvas_state.start_moving(canvas_point)
                elif current_mode == InteractionMode.MOVING:
                    self.canvas_state.continue_moving(canvas_point)
            elif gesture_type == GestureType.IDLE and current_mode == InteractionMode.MOVING:
                self.canvas_state.end_moving()

        elif current_tool == ToolType.RESIZE:
            pinch_center = gesture.parameters.get('pinch_center')
            if gesture_type == GestureType.PINCH and pinch_center:
                canvas_point = Point(pinch_center.x * CanvasConfig.CANVAS_WIDTH, pinch_center.y * CanvasConfig.CANVAS_HEIGHT)
                canvas_point = self.coord_mapper.apply_smoothing(canvas_point, "pinch")
                if self.gesture_just_started:
                    if not self.canvas_state.selected_object:
                        obj = self.canvas_state.find_object_at(canvas_point)
                        if obj: self.canvas_state.select_object(obj)
                    if self.canvas_state.selected_object:
                        self.canvas_state.start_scaling(canvas_point.y)
                elif current_mode == InteractionMode.SCALING:
                    self.canvas_state.continue_scaling(canvas_point.y)
            elif gesture_type == GestureType.IDLE and current_mode == InteractionMode.SCALING:
                self.canvas_state.end_scaling()

        elif current_tool == ToolType.KNIFE:
            if gesture_type == GestureType.DRAW:
                if self.gesture_just_started or current_mode != InteractionMode.CUTTING:
                    self.canvas_state.start_cutting(draw_point)
                else:
                    self.canvas_state.continue_cutting(draw_point)
            elif gesture_type == GestureType.IDLE and current_mode == InteractionMode.CUTTING:
                self.canvas_state.end_cutting()

        self.previous_gesture = gesture_type

    def _end_all_operations(self):
        mode = self.canvas_state.mode
        if mode == InteractionMode.DRAWING: self.canvas_state.end_drawing()
        elif mode == InteractionMode.SHAPE_PREVIEW: self.canvas_state.finalize_shape()
        elif mode == InteractionMode.MOVING: self.canvas_state.end_moving()
        elif mode == InteractionMode.SCALING: self.canvas_state.end_scaling()
        elif mode == InteractionMode.CUTTING: self.canvas_state.end_cutting()
        elif mode == InteractionMode.ROTATING:
            self.canvas_state.end_rotating()
            self.gesture_recognizer.reset_palm_tracking()
        self.canvas_state.mode = InteractionMode.IDLE

    def _handle_no_hands(self):
        self._end_all_operations()
        self.previous_gesture = GestureType.NONE
        self.coord_mapper.reset_smoothing()
        self.cursor_over_toolbar = False
        self.gesture_recognizer.reset_palm_tracking()

    def _cycle_tool(self):
        tools = list(ToolType)
        current_idx = tools.index(self.toolbar.selected_tool)
        new_tool = tools[(current_idx + 1) % len(tools)]
        self.toolbar.select_tool(new_tool)
        self._show_notification(f"Tool: {new_tool.name}")
        self._end_all_operations()

    # Keyboard actions (called from Tkinter key bindings)
    def action_clear(self):
        self.canvas_state.clear_canvas()
        self._show_notification("Canvas cleared")

    def action_undo(self):
        if self.canvas_state.undo(): self._show_notification("Undo")

    def action_redo(self):
        if self.canvas_state.redo(): self._show_notification("Redo")

    def action_save_png(self):
        img = self.renderer.render(state=self.canvas_state, toolbar=self.toolbar, show_camera=False)
        path = self.canvas_state.save_canvas_png(img)
        self._show_notification(f"Saved: {os.path.basename(path)}")

    def action_save_json(self):
        path = self.canvas_state.save_canvas_json()
        self._show_notification(f"Saved: {os.path.basename(path)}")

    def action_new_layer(self):
        layer = self.canvas_state.layer_manager.add_layer()
        if layer: self._show_notification(f"New layer: {layer.name}")
        else: self._show_notification("Max layers reached")

    def action_cycle_layer(self):
        self.canvas_state.layer_manager.cycle_active_layer()
        active = self.canvas_state.layer_manager.get_active_layer()
        self._show_notification(f"Active: {active.name}")

    def action_toggle_layer_visibility(self):
        active = self.canvas_state.layer_manager.get_active_layer()
        self.canvas_state.layer_manager.toggle_visibility(active.layer_id)
        vis = "Visible" if active.visible else "Hidden"
        self._show_notification(f"Layer {active.name}: {vis}")

    def action_delete_selected(self):
        self.canvas_state.delete_selected()
        self._show_notification("Deleted")

    def action_cycle_color(self):
        self.toolbar.cycle_color()
        self._show_notification("Color changed")

    def action_cycle_brush(self):
        self.toolbar.cycle_brush_size()
        self._show_notification(f"Brush: {self.toolbar.brush_size}")
