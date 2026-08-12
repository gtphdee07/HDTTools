from .database import DEFAULT_DB_PATH, save_scale_ticket, save_trailer_tag, save_truck_tag
from .models import ScaleTicketData, TireSpec, TrailerTagData, TruckTagData
from .scale_ticket import read_scale_ticket
from .trailer_tag import read_trailer_tag
from .truck_tag import read_truck_tag

__all__ = [
    "DEFAULT_DB_PATH",
    "ScaleTicketData",
    "TireSpec",
    "TrailerTagData",
    "TruckTagData",
    "read_scale_ticket",
    "read_trailer_tag",
    "read_truck_tag",
    "save_scale_ticket",
    "save_trailer_tag",
    "save_truck_tag",
]


def main() -> None:
    print("Hello from hdttools!")
