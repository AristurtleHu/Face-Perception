"""Stimulus rendering and layout utilities for visual search experiment."""

from __future__ import annotations

from functools import lru_cache
from math import cos, pi, sin
from pathlib import Path
from typing import Literal, cast

from PIL import Image
import pygame


def _resolve_existing_path(path: Path) -> Path:
    """Resolve an image path with fallbacks for frozen and source runs."""
    if path.exists():
        return path

    # When packaged with PyInstaller, data files may be missing from the bundle
    # but still available next to the launched executable or in the working dir.
    cwd_candidate = Path.cwd() / path
    if cwd_candidate.exists():
        return cwd_candidate

    if path.parts and "docs" in path.parts:
        docs_index = path.parts.index("docs")
        relative = Path(*path.parts[docs_index:])
        cwd_docs_candidate = Path.cwd() / relative
        if cwd_docs_candidate.exists():
            return cwd_docs_candidate

    return path


@lru_cache(maxsize=1024)
def load_surface(path_str: str, mask_path_str: str | None = None) -> pygame.Surface:
    """Load image file with optional mask into pygame surface with caching."""
    path = _resolve_existing_path(Path(path_str))
    image = Image.open(path).convert("RGBA")

    if mask_path_str is not None:
        mask_path = _resolve_existing_path(Path(mask_path_str))
        mask = Image.open(mask_path).convert("L")
        if mask.size != image.size:
            mask = mask.resize(image.size, Image.Resampling.LANCZOS)
        image.putalpha(mask)

    surface = pygame.image.fromstring(
        image.tobytes(), image.size, cast(Literal["RGBA"], image.mode.upper())
    )
    return surface.convert_alpha()


def make_fixation_surface(
    screen_size: tuple[int, int],
    color: tuple[int, int, int],
    background: tuple[int, int, int],
) -> pygame.Surface:
    """Create a fixation cross centered on screen."""
    width, height = screen_size
    surface = pygame.Surface((width, height))
    surface.fill(background)

    center_x = width // 2
    center_y = height // 2
    half_len = 17
    half_weight = 4

    # Draw hollow cross
    pygame.draw.rect(
        surface,
        color,
        pygame.Rect(
            center_x - half_len + 1, center_y - half_len + 1, half_len * 2, half_len * 2
        ),
    )
    pygame.draw.rect(
        surface,
        background,
        pygame.Rect(
            center_x - half_len + 1,
            center_y - half_len + 1,
            half_len - half_weight,
            half_len * 2,
        ),
    )
    pygame.draw.rect(
        surface,
        background,
        pygame.Rect(
            center_x + half_weight,
            center_y - half_len + 1,
            half_len - half_weight + 1,
            half_len * 2,
        ),
    )
    pygame.draw.rect(
        surface,
        background,
        pygame.Rect(
            center_x - half_len + 1,
            center_y - half_len + 1,
            half_len * 2,
            half_len - half_weight,
        ),
    )
    pygame.draw.rect(
        surface,
        background,
        pygame.Rect(
            center_x - half_len + 1,
            center_y + half_weight,
            half_len * 2,
            half_len - half_weight + 1,
        ),
    )
    return surface


def build_grid_offsets(
    stim_width: int = 120, stim_space: int = 12
) -> list[tuple[int, int]]:
    """Generate grid positions for 16-item stimulus array."""
    coords = [
        int(value)
        for value in [
            *(
                (((stim_width + stim_space) * n) - (stim_space / 2)) * -1
                for n in [4, 3, 2, 1]
            ),
            *(((stim_width + stim_space) * n) + (stim_space / 2) for n in [0, 1, 2, 3]),
        ]
    ]
    return [(x, y) for y in coords for x in coords]


def build_circle_offsets(set_size: int, radius: int) -> list[tuple[int, int]]:
    """Generate evenly-spaced circular positions."""
    theta = (2 * pi) / set_size
    return [
        (
            int(round(cos(index * theta) * radius)),
            int(round(sin(index * theta) * radius)),
        )
        for index in range(1, set_size + 1)
    ]


def build_circle_layouts(radius: int = 400) -> dict[int, list[tuple[int, int]]]:
    return {set_size: build_circle_offsets(set_size, radius) for set_size in (4, 8, 16)}


def centered_rect(surface: pygame.Surface, center: tuple[int, int]) -> pygame.Rect:
    """Return rect centered at given position."""
    rect = surface.get_rect()
    rect.center = center
    return rect


def blit_centered(
    destination: pygame.Surface, source: pygame.Surface, center: tuple[int, int]
) -> None:
    """Draw source surface centered at given position on destination."""
    destination.blit(source, centered_rect(source, center))


def render_multiline_text(
    font: pygame.font.Font, text: str, color: tuple[int, int, int]
) -> list[pygame.Surface]:
    """Render each line of text as separate surface."""
    return [font.render(line, True, color) for line in text.splitlines()]
