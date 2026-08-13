"""Data structures returned by the image-reading functions."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(kw_only=True)
class TireSpec:
    tire: str | None = None
    rim: str | None = None
    cold_pressure_kpa: float | None = None
    cold_pressure_psi: float | None = None
    dual: bool = False


@dataclass(kw_only=True)
class ScaleTicketData:
    source_image: str
    ticket_number: str | None = None
    weigh_number: str | None = None
    date: str | None = None
    time: str | None = None
    scale_number: str | None = None
    location_name: str | None = None
    location_address: str | None = None
    city: str | None = None
    state: str | None = None
    steer_axle_lb: float | None = None
    drive_axle_lb: float | None = None
    trailer_axle_lb: float | None = None
    gross_weight_lb: float | None = None
    company: str | None = None
    commodity: str | None = None
    tractor_number: str | None = None
    trailer_number: str | None = None


@dataclass(kw_only=True)
class TruckTagData:
    vehicle_name: str
    source_image: str
    manufacturer: str | None = None
    date: str | None = None
    vin: str | None = None
    vehicle_type: str | None = None
    gvwr_kg: float | None = None
    gvwr_lb: float | None = None
    front_gawr_kg: float | None = None
    front_gawr_lb: float | None = None
    rear_gawr_kg: float | None = None
    rear_gawr_lb: float | None = None
    standalone_weight_lb: float | None = None
    front_tire: TireSpec
    rear_tire: TireSpec


@dataclass(kw_only=True)
class TrailerTagData:
    vehicle_name: str
    source_image: str
    manufacturer: str | None = None
    date: str | None = None
    vin: str | None = None
    vehicle_type: str | None = None
    gvwr_kg: float | None = None
    gvwr_lb: float | None = None
    gawr_per_axle_kg: float | None = None
    gawr_per_axle_lb: float | None = None
    uvw_kg: float | None = None
    uvw_lb: float | None = None
    axle_count: int | None = None
    tire: TireSpec
