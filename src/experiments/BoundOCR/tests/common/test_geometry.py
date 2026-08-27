import cv2
import numpy as np
import pytest
from PIL import Image

from experiments.BoundOCR.common.geometry import order_quad_points, pad_quad, warp_to_quad


def test_order_quad_points_normalizes_arbitrary_input_order():
    tl, tr, br, bl = (10, 20), (110, 20), (110, 80), (10, 80)
    scrambled = [br, tl, bl, tr]

    ordered = order_quad_points(scrambled)

    assert ordered == [tl, tr, br, bl]


def test_pad_quad_expands_outward_from_centroid():
    quad = [(100, 100), (200, 100), (200, 200), (100, 200)]

    padded = pad_quad(quad, margin_fraction=0.1)

    expected = [(95, 95), (205, 95), (205, 205), (95, 205)]
    for actual_point, expected_point in zip(padded, expected):
        assert actual_point[0] == pytest.approx(expected_point[0], abs=1)
        assert actual_point[1] == pytest.approx(expected_point[1], abs=1)


def test_warp_to_quad_deskews_a_rotated_rectangle_and_preserves_orientation():
    width, height, angle = 300, 200, 15.0
    canvas_size = 600
    offset_x, offset_y = 150, 200

    canvas = np.zeros((canvas_size, canvas_size), dtype=np.uint8)
    corners = np.array(
        [
            [offset_x, offset_y],
            [offset_x + width, offset_y],
            [offset_x + width, offset_y + height],
            [offset_x, offset_y + height],
        ],
        dtype=np.float32,
    )
    cv2.fillConvexPoly(canvas, corners.astype(np.int32), 255)

    marker_size = 30
    cv2.rectangle(
        canvas,
        (offset_x, offset_y),
        (offset_x + marker_size, offset_y + marker_size),
        0,
        thickness=-1,
    )

    center = (canvas_size / 2, canvas_size / 2)
    rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated_canvas = cv2.warpAffine(canvas, rotation_matrix, (canvas_size, canvas_size))

    homogeneous_corners = np.hstack([corners, np.ones((4, 1), dtype=np.float32)])
    rotated_corners = rotation_matrix.dot(homogeneous_corners.T).T
    quad = [(int(round(x)), int(round(y))) for x, y in rotated_corners]

    image = Image.fromarray(rotated_canvas).convert("RGB")

    warped = warp_to_quad(image, quad)
    warped_arr = np.array(warped.convert("L"))

    assert abs(warped.width - width) <= 5
    assert abs(warped.height - height) <= 5

    top_left_patch = warped_arr[5:15, 5:15]
    bottom_right_patch = warped_arr[-15:-5, -15:-5]
    assert top_left_patch.mean() < 100
    assert bottom_right_patch.mean() > 150
