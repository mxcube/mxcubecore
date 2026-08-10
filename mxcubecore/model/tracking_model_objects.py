from typing import Optional

from icat_plus_client.models.item import Item


class LoadedPuck(Item):
    puck_name: Optional[str] = None
    parcel_name: Optional[str] = None
    parcel_id: Optional[str] = None
