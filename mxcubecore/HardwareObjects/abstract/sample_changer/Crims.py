import logging
from io import BytesIO
from typing import List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import requests
from defusedxml import ElementTree
from PIL import Image, UnidentifiedImageError


def get_image(url: str) -> Optional[bytes]:
    try:
        return urlopen(url).read()
    except (URLError, HTTPError) as e:
        logging.getLogger("user_level_log").warning(
            "Failed to fetch image from %s: %s", url, e
        )
        return None


def get_image_size(url: str) -> Tuple[int, int]:
    try:
        img_data = requests.get(url, timeout=900).content
        with Image.open(BytesIO(img_data)) as im:
            return im.size
    except (requests.RequestException, UnidentifiedImageError, OSError) as e:
        logging.getLogger("user_level_log").warning(
            "Failed to get image size from %s: %s", url, e
        )
        return (0, 0)


class CrimsXtal:
    def __init__(self, *args):
        self.crystal_uuid = ""
        self.pin_id = ""
        self.login = ""
        self.sample = ""
        self.column = 0
        self.id_sample = 0
        self.id_trial = 0
        self.row = ""
        self.shelf = 0
        self.comments = ""
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.shape = ""
        self.image_url = ""
        self.image_rotation = 0.0
        self.image_height = 0.0
        self.image_width = 0.0
        self.image_date = ""
        self.summary_url = ""

    def get_address(self) -> str:
        return f"{self.row}{self.column:02d}-{self.shelf}"

    def get_image(self) -> Optional[bytes]:
        if self.image_url:
            try:
                secure_url = self.image_url.replace("http://", "https://", 1)
                return urlopen(secure_url).read()
            except (URLError, HTTPError) as e:
                logging.getLogger("user_level_log").warning(
                    "Failed to load image from %s: %s", self.image_url, e
                )
        return None

    def get_image_size(self) -> Tuple[int, int]:
        return get_image_size(self.image_url)

    def get_summary_url(self) -> Optional[str]:
        return self.summary_url or None


class Plate:
    def __init__(self, *args):
        self.barcode: str = ""
        self.plate_type: str = ""
        self.xtal_list: List[CrimsXtal] = []


class ProcessingPlan:
    def __init__(self, *args):
        self.plate = Plate()


def get_processing_plan(
    barcode: str, crims_url: str, crims_user_agent: str, harvester_key: str
) -> Optional[ProcessingPlan]:
    try:
        url = f"{crims_url}{barcode}/plans/xml"

        headers = {
            "User-Agent": crims_user_agent,
            "harvester-key": harvester_key,
        }

        req = Request(url, headers=headers)

        with urlopen(req) as response:
            xml_content = response.read()

        tree = ElementTree.fromstring(xml_content)

        plate_elem = tree.find("Plate")

        processing_plan = ProcessingPlan()
        processing_plan.plate.barcode = plate_elem.findtext("Barcode", "")
        processing_plan.plate.plate_type = plate_elem.findtext("PlateType", "")
        for drop in plate_elem.findall("Drop"):
            if drop.find("Pin"):
                try:
                    xtal = CrimsXtal()
                    xtal.pin_id = drop.find("Pin").find("PinUUID").text
                    xtal.crystal_uuid = (
                        drop.find("Pin").find("Xtal").find("CrystalUUID").text
                    )
                    xtal.sample = drop.find("Sample").text
                    xtal.id_sample = int(drop.find("idSample").text)
                    xtal.column = int(drop.find("Column").text)
                    xtal.row = drop.find("Row").text
                    xtal.shelf = int(drop.find("Shelf").text)
                    xtal.offset_x = (
                        float(drop.find("Pin").find("Xtal").find("X").text) / 100.0
                    )
                    xtal.offset_y = (
                        float(drop.find("Pin").find("Xtal").find("Y").text) / 100.0
                    )
                    xtal.shape = drop.find("Pin").find("Shape").text
                    xtal.image_url = drop.find("IMG_URL").text

                    xtal.image_height = get_image_size(drop.find("IMG_URL").text)[0]
                    xtal.image_width = get_image_size(drop.find("IMG_URL").text)[1]

                    xtal.image_date = drop.find("IMG_Date").text
                    xtal.image_rotation = float(drop.find("ImageRotation").text)
                    processing_plan.plate.xtal_list.append(xtal)
                except (ValueError, TypeError) as e:
                    logging.getLogger("user_level_log").warning(
                        "Error parsing crystal info: %s", e
                    )
                    continue
        return processing_plan
    except (URLError, HTTPError, ElementTree.ParseError) as e:
        logging.getLogger("user_level_log").warning(
            "Error getting processing plan from  %s : %s", url, e
        )
        return None


def send_data_collection_info_to_crims(
    crims_url: str,
    crystaluuid: str,
    datacollectiongroupid: str,
    dcid: str,
    proposal: str,
    rest_token: str,
    crims_key: str,
) -> bool:
    """Send Data collected to CRIMS
    Return (bool): Whether the request failed (false) or proceed (true)
    """
    url = (
        f"{crims_url}{crystaluuid}/dcgroupid/{datacollectiongroupid}/dcid/"
        f"{dcid}/mx/{proposal}/token/{rest_token}?janitor_key={crims_key}"
    )
    try:
        response = requests.get(url, timeout=900)
        logging.getLogger("user_level_log").info(
            "Request to %s Proceed: %s", url, response.text
        )
        return True
    except requests.RequestException as e:
        logging.getLogger("user_level_log").warning("Request to %s failed: %s", url, e)
        return False
