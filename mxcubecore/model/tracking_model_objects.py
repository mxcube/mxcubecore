from typing import Optional

from pyicat_plus.client.models import ParcelItem


class LoadedPuck(ParcelItem):
    puck_name: Optional[str] = None
    parcel_name: Optional[str] = None
    parcel_id: Optional[str] = None
