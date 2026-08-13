"""Pydantic request/response models for the RigCheck API."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel


class TireSpecOut(BaseModel):
    tire: str | None = None
    rim: str | None = None
    cold_pressure_kpa: float | None = None
    cold_pressure_psi: float | None = None
    dual: bool = False


class TruckTagOut(BaseModel):
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
    front_tire: TireSpecOut
    rear_tire: TireSpecOut


class TrailerTagOut(BaseModel):
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
    tire: TireSpecOut


class ScaleTicketOut(BaseModel):
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


class RigOut(BaseModel):
    id: int
    truck_name: str
    trailer_name: str


class BreakdownItemOut(BaseModel):
    label: str
    tone: Literal["success", "warning"]
    badgeLabel: str
    pct: int
    barColor: str
    actualLabel: str
    limitLabel: str
    note: str | None = None


class VerdictOut(BaseModel):
    headline: str
    subline: str
    bandBg: str
    icon: str


class CheckOut(BaseModel):
    id: int
    rig_id: int
    truck_name: str
    trailer_name: str
    date: str
    verdict: Literal["pass", "fail"]
    breakdown: list[BreakdownItemOut]


class CheckCreateRequest(BaseModel):
    rig_id: int
    truck: dict[str, Any]
    trailer: dict[str, Any]
    scale: dict[str, Any]


class CheckCreateResponse(BaseModel):
    id: int
    date: str
    verdict: Literal["pass", "fail"]
    breakdownItems: list[BreakdownItemOut]
    verdictInfo: VerdictOut
