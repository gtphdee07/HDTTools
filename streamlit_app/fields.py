"""Field-list config for each wizard module's review step, mirroring
`web/src/mockData.ts`'s `MODULES` so both frontends show the same fields
extracted the same way. Kept as a plain tuple list (name, label, type) -
same shape as the TS `FieldDef`."""

from __future__ import annotations

FIELDS: dict[str, list[tuple[str, str, str]]] = {
    "truck": [
        ("manufacturer", "Manufacturer", "text"),
        ("gvwr_lb", "GVWR (lb)", "number"),
        ("front_gawr_lb", "Front GAWR (lb)", "number"),
        ("rear_gawr_lb", "Rear GAWR (lb)", "number"),
        ("standalone_weight_lb", "Stand-alone Weight (lb, optional)", "number"),
    ],
    "trailer": [
        ("manufacturer", "Manufacturer", "text"),
        ("gvwr_lb", "GVWR (lb)", "number"),
        ("gawr_per_axle_lb", "GAWR per axle (lb)", "number"),
        ("axle_count", "Axle Count (optional, defaults to 2)", "number"),
        ("uvw_lb", "Unloaded Weight / UVW (lb)", "number"),
    ],
    "scale": [
        ("location_name", "Scale Location", "text"),
        ("steer_axle_lb", "Steer Axle (lb)", "number"),
        ("drive_axle_lb", "Drive Axle (lb)", "number"),
        ("trailer_axle_lb", "Trailer Axle(s) (lb)", "number"),
        ("gross_weight_lb", "Gross Weight (lb)", "number"),
    ],
}

TITLES: dict[str, str] = {
    "truck": "Truck Compliance Label",
    "trailer": "Trailer Compliance Label",
    "scale": "CAT Scale Ticket",
}
