from dataclasses import dataclass, field
from typing import Any


@dataclass
class HandState:
    visible: bool = False
    landmarks: list[dict] = field(default_factory=list)
    confidence: float = 0.0


@dataclass
class FrameContext:
    frame: Any = None
    hand_state: HandState = field(default_factory=HandState)
    gesture_result: Any = None
    raw_target: tuple[int, int] | None = None
    cursor_pos: tuple[int, int] = (0, 0)
