import time
import xml.etree.cElementTree as et

try:
    from urllib import urlopen
except ImportError:
    from urllib.request import urlopen


def get_image(url):
    f = urlopen(url)
    img = f.read()
    return img


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


def get_processing_plan(barcode, crims_url):
    try:
        url = (
            crims_url
            + "/htxlab/index.php?option=com_crimswebservices"
            + "&format=raw&task=getbarcodextalinfos&barcode=%s&action=insitu" % barcode
        )
        f = urlopen(url)
        xml = f.read()

        import xml.etree.cElementTree as et

        tree = et.fromstring(xml)

        processing_plan = ProcessingPlan()
        plate = tree.findall("Plate")[0]

        processing_plan.plate.barcode = plate.find("Barcode").text
        processing_plan.plate.plate_type = plate.find("PlateType").text

        for x in plate.findall("Xtal"):
            xtal = CrimsXtal()
            xtal.crystal_uuid = x.find("CrystalUUID").text
            xtal.label = x.find("Label").text
            xtal.login = x.find("Login").text
            xtal.sample = x.find("Sample").text
            xtal.id_sample = int(x.find("idSample").text)
            xtal.column = int(x.find("Column").text)
            xtal.row = x.find("Row").text
            xtal.shelf = int(x.find("Shelf").text)
            xtal.comments = x.find("Comments").text
            xtal.offset_x = float(x.find("offsetX").text) / 100.0
            xtal.offset_y = float(x.find("offsetY").text) / 100.0
            xtal.image_url = x.find("IMG_URL").text
            xtal.image_date = x.find("IMG_Date").text
            xtal.image_rotation = float(x.find("ImageRotation").text)
            xtal.summary_url = x.find("SUMMARY_URL").text
            processing_plan.plate.xtal_list.append(xtal)
        return processing_plan
    except Exception:
        return
