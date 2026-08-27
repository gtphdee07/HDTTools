import cv2
import numpy as np
from PIL import Image


def order_quad_points(quad: list[tuple[int, int]]) -> list[tuple[int, int]]:
    pts = np.array(quad, dtype=np.float32)
    total = pts.sum(axis=1)
    diff = pts[:, 1] - pts[:, 0]

    top_left = pts[np.argmin(total)]
    bottom_right = pts[np.argmax(total)]
    top_right = pts[np.argmin(diff)]
    bottom_left = pts[np.argmax(diff)]

    return [(int(round(p[0])), int(round(p[1]))) for p in (top_left, top_right, bottom_right, bottom_left)]


def pad_quad(quad: list[tuple[int, int]], margin_fraction: float = 0.05) -> list[tuple[int, int]]:
    center_x = sum(point[0] for point in quad) / len(quad)
    center_y = sum(point[1] for point in quad) / len(quad)
    scale = 1 + margin_fraction

    return [
        (
            int(round(center_x + (x - center_x) * scale)),
            int(round(center_y + (y - center_y) * scale)),
        )
        for x, y in quad
    ]


def warp_to_quad(image: Image.Image, quad: list[tuple[int, int]]) -> Image.Image:
    top_left, top_right, bottom_right, bottom_left = order_quad_points(quad)

    width_top = np.hypot(top_right[0] - top_left[0], top_right[1] - top_left[1])
    width_bottom = np.hypot(bottom_right[0] - bottom_left[0], bottom_right[1] - bottom_left[1])
    height_left = np.hypot(bottom_left[0] - top_left[0], bottom_left[1] - top_left[1])
    height_right = np.hypot(bottom_right[0] - top_right[0], bottom_right[1] - top_right[1])

    out_width = max(1, int(round(max(width_top, width_bottom))))
    out_height = max(1, int(round(max(height_left, height_right))))

    src = np.array([top_left, top_right, bottom_right, bottom_left], dtype=np.float32)
    dst = np.array(
        [[0, 0], [out_width - 1, 0], [out_width - 1, out_height - 1], [0, out_height - 1]],
        dtype=np.float32,
    )
    matrix = cv2.getPerspectiveTransform(src, dst)

    arr = np.array(image.convert("RGB"))
    warped = cv2.warpPerspective(arr, matrix, (out_width, out_height))
    return Image.fromarray(warped)
