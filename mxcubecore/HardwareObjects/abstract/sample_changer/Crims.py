import xml.etree.cElementTree as et

import requests
from PIL import Image
from io import BytesIO

import urllib


def get_image(url):
    f = urlopen(url)
    img = f.read()
    return img


def get_image_size(url):
    img_data = requests.get(url).content    
    im = Image.open(BytesIO(img_data))
    return (im.size)

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
        self.summary_url = ""

    def get_address(self):
        return "%s%02d-%d" % (self.row, self.column, self.shelf)

    def get_image(self):
        if len(self.image_url) > 0:
            try:
                if self.image_url.startswith("http://"):
                    self.image_url = "https://" + self.image_url[7]
                image_string = urlopen(self.image_url).read()
                return image_string
            except Exception:
                return
    
    def get_image_size(self):
        img_data = requests.get(self.image_url).content    
        im = Image.open(BytesIO(img_data))
        return (im.size)

    def get_summary_url(self):
        if len(self.summary_url == 0):
            return None
        return self.summary_url

class Plate:
    def __init__(self, *args):
        self.barcode = ""
        self.plate_type = ""
        self.xtal_list = []


class ProcessingPlan:
    def __init__(self, *args):
        self.plate = Plate()


def get_processing_plan(barcode, crims_url, harvester_key):
    processing_plan = None
    try:
        xml = None
        url = crims_url
        url = (
            crims_url
            + barcode
            + "/plans/xml"
        )

        headers = { 
            'User-Agent' : "Mozilla/5.0 (Windows NT 6.1; Win64; x64",
            'harvester-key' : harvester_key,       
         }

        req = urllib.request.Request(url, data=None, headers=headers)

        with urllib.request.urlopen(req) as response:
            xml = response.read()

        tree = et.fromstring(xml)

        processing_plan = ProcessingPlan()
        plate = tree.findall("Plate")[0]

        processing_plan.plate.barcode = plate.find("Barcode").text
        processing_plan.plate.plate_type = plate.find("PlateType").text
        for x in plate.findall("Drop"):
            if (x.find("Pin")):
                xtal = CrimsXtal()
                xtal.pin_id = x.find("Pin").find("PinUUID").text
                xtal.crystal_uuid = x.find("Pin").find("Xtal").find("CrystalUUID").text
                # xtal.label = x.find("Label").text
                # xtal.login = plate.find("Login").text
                xtal.sample = x.find("Sample").text
                xtal.id_sample = int(x.find("idSample").text)
                xtal.column = int(x.find("Column").text)
                xtal.row = x.find("Row").text
                xtal.shelf = int(x.find("Shelf").text)
                # xtal.comments = x.find("Comments").text
                xtal.offset_x = float(x.find("Pin").find("Xtal").find("X").text) / 100.0
                xtal.offset_y = float(x.find("Pin").find("Xtal").find("Y").text) / 100.0
                xtal.shape = x.find("Pin").find("Shape").text
                xtal.image_url = x.find("IMG_URL").text

                xtal.image_height = get_image_size(x.find("IMG_URL").text)[0]
                xtal.image_width = get_image_size(x.find("IMG_URL").text)[1]

                xtal.image_date = x.find("IMG_Date").text
                xtal.image_rotation = float(x.find("ImageRotation").text)
                # xtal.summary_url = x.find("SUMMARY_URL").text
                processing_plan.plate.xtal_list.append(xtal)
        return processing_plan
    except Exception as ex:
        print("Error on getting processing plan because of:  %s" %str(ex))
        return processing_plan




def send_data_collection_info_to_crims(crims_url, crystaluuid, datacollectiongroupid, dcid, proposal, rest_token):
    try:
        url = crims_url
        url = (
            crims_url
            + str(crystaluuid)
            + "/dcgroupid/"
            + str(datacollectiongroupid)
            + "/dcid/"
            +  str(dcid)
            + "/mx/"
            + str(proposal)
            + "/token/"
            + str(rest_token)
            + "?janitor_key=kbonvRqc8"
        )
      
        data = {
            "crystal_uuid": str(crystaluuid),
            "datacollectionGroupId": str(datacollectiongroupid),
            "dcid":str(dcid),
            "mx": str(proposal),
            "token": str(rest_token),
        }
        response = requests.get(url, timeout=900)
        # response = post(url, data=data, timeout=900)
        print(response.text)
        # import pdb; pdb.set_trace()
        return response.text
    except Exception as ex:
        msg = "POST to %s failed reason %s" % (url, str(ex))
        return msg
