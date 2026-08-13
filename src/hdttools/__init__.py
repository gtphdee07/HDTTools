from .database import DEFAULT_DB_PATH, save_scale_ticket, save_trailer_tag, save_truck_tag
from .models import ScaleTicketData, TireSpec, TrailerTagData, TruckTagData

__all__ = [
    "DEFAULT_DB_PATH",
    "ScaleTicketData",
    "TireSpec",
    "TrailerTagData",
    "TruckTagData",
    "save_scale_ticket",
    "save_trailer_tag",
    "save_truck_tag",
]

# The desktop CLI readers pull in tkinter (file_picker/review_form) and the
# Anthropic SDK transitively. tkinter isn't always present on headless/minimal
# Python builds (e.g. some Docker/Streamlit Cloud images) - importing the
# package root shouldn't hard-fail there just because it can't offer these.
try:
    from .scale_ticket import read_scale_ticket
    from .trailer_tag import read_trailer_tag
    from .truck_tag import read_truck_tag
except ImportError:
    pass
else:
    __all__ += ["read_scale_ticket", "read_trailer_tag", "read_truck_tag"]


def main() -> None:
    print("Hello from hdttools!")
