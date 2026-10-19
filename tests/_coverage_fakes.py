"""Fake JaCoCo HTML for the Android JVM decision-logic coverage tests (#130).

Same shape as the real report (confirmed against
android/app/build/reports/coverage/test/debug on 2026-10-18): a top-level
index.html linking each package page, and one index.html per package with
an el_class row per class. Class names are simple names within the package.
"""

from __future__ import annotations

import html
from pathlib import Path


def class_row(name: str, missed: int, covered: int) -> str:
    if missed == 0 and covered == 0:
        bar = '<td class="bar" id="b0"/>'
    else:
        imgs = ""
        if missed:
            imgs += (
                '<img src="../jacoco-resources/redbar.gif" width="4" height="10" '
                f'title="{missed:,}" alt="{missed:,}"/>'
            )
        if covered:
            imgs += (
                '<img src="../jacoco-resources/greenbar.gif" width="9" height="10" '
                f'title="{covered:,}" alt="{covered:,}"/>'
            )
        bar = f'<td class="bar" id="b0">{imgs}</td>'
    return (
        f'<tr><td id="a0"><a href="{name}.html" class="el_class">{html.escape(name)}</a></td>'
        f'{bar}<td class="ctr2" id="c0">0%</td></tr>'
    )


def package_page(rows: list[tuple[str, int, int]]) -> str:
    body = "".join(class_row(*row) for row in rows)
    return f"<html><body><table><tbody>{body}</tbody></table></body></html>"


def write_fake_jvm_report(root: Path, packages: dict[str, list[tuple[str, int, int]]]) -> Path:
    """Write a fake JVM report dir: {package: [(class name, missed, covered)]}."""
    root.mkdir(parents=True, exist_ok=True)
    links = "".join(
        f'<tr><td><a href="{pkg}/index.html" class="el_package">{pkg}</a></td></tr>'
        for pkg in packages
    )
    (root / "index.html").write_text(
        f"<html><body><table><tbody>{links}</tbody></table></body></html>", encoding="utf-8"
    )
    for pkg, rows in packages.items():
        (root / pkg).mkdir(exist_ok=True)
        (root / pkg / "index.html").write_text(package_page(rows), encoding="utf-8")
    return root
