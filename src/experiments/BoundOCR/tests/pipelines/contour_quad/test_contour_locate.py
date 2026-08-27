from PIL import Image, ImageDraw

from experiments.BoundOCR.pipelines.contour_quad.contour_locate import locate_label


def _rectangle_image(size=(800, 600), rect=(200, 150, 600, 450)):
    image = Image.new("L", size, color=0)
    draw = ImageDraw.Draw(image)
    draw.rectangle(rect, fill=255)
    return image.convert("RGB")


def test_locate_label_finds_a_clean_synthetic_rectangle():
    rect = (200, 150, 600, 450)
    image = _rectangle_image(rect=rect)

    quad = locate_label(image)

    assert quad is not None
    xs = [point[0] for point in quad]
    ys = [point[1] for point in quad]
    assert abs(min(xs) - rect[0]) <= 5
    assert abs(max(xs) - rect[2]) <= 5
    assert abs(min(ys) - rect[1]) <= 5
    assert abs(max(ys) - rect[3]) <= 5


def test_locate_label_picks_the_real_label_quad_over_a_cluttered_larger_contour():
    # Mirrors the real 20260824_141530.jpg spike finding (see
    # ClaudePlans/2026-08-26-boundocr-redstage-test-plan.md): the single
    # largest-area contour in that photo was a 7-corner non-label shape,
    # while a smaller, clean 4-corner contour was the real label. Larger
    # area alone must not win over corner-count/shape plausibility.
    image = Image.new("L", (1000, 1000), color=0)
    draw = ImageDraw.Draw(image)

    draw.polygon(
        [(30, 30), (600, 60), (650, 400), (800, 750), (400, 950), (60, 700), (20, 300)],
        fill=255,
    )
    rect = (700, 50, 950, 250)
    draw.rectangle(rect, fill=255)

    quad = locate_label(image.convert("RGB"))

    assert quad is not None
    xs = [point[0] for point in quad]
    ys = [point[1] for point in quad]
    assert min(xs) >= rect[0] - 5
    assert max(xs) <= rect[2] + 5
    assert min(ys) >= rect[1] - 5
    assert max(ys) <= rect[3] + 5


def test_locate_label_returns_none_when_nothing_plausible_is_found():
    image = Image.new("RGB", (400, 400), color=(128, 128, 128))

    quad = locate_label(image)

    assert quad is None
