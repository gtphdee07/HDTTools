import cv2
import numpy as np

_MIN_AREA_FRACTION = 0.02


def locate_label(image) -> list[tuple[int, int]] | None:
    arr = np.array(image.convert("RGB"))
    frame_area = arr.shape[0] * arr.shape[1]

    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(cv2.GaussianBlur(gray, (5, 5), 0), 50, 150)
    edges = cv2.dilate(edges, np.ones((5, 5), np.uint8), iterations=1)

    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    candidates = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < _MIN_AREA_FRACTION * frame_area:
            continue
        peri = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
        candidates.append((len(approx), area, approx))

    if not candidates:
        return None

    # Exact-4-corner candidates always outrank any other corner count -
    # larger area alone must not win (see the 20260824_141530.jpg spike,
    # where the largest-area contour had 7 corners and was not the label).
    candidates.sort(key=lambda item: (0 if item[0] == 4 else 1, item[0], -item[1]))
    corners, _, best = candidates[0]

    if corners == 4:
        return [(int(point[0][0]), int(point[0][1])) for point in best]

    x, y, w, h = cv2.boundingRect(best)
    return [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
