import time
import urllib


def getImage(barcode, inspection,row, col, shelf):
    #print (barcode, inspection,row, col, shelf)
    url = "https://embl.fr/htxlab/index.php?option=com_getbarcodextalinfos&task=getImage&format=raw&barcode=%s&inspection=%d&row=%s&column=%d&shelf=%d" %  (barcode, inspection,row, col, shelf)    
    f = urllib.urlopen(url)           
    img=f.read() 
    return img

def getProcessingPlanXML(barcode):
    #url = "https://embl.fr/htxlab/index.php?option=com_getbarcodextalinfos&task=getBarcodeXtalInfos&barcode=%s" % barcode
    #Crims V3
    url = "https://embl.fr/htxlabj3/index.php?option=com_getbarcodextalinfos&task=getBarcodeXtalInfos&format=xml&barcode=%s" % barcode
    #print "Opening URL: " + url
    f = urllib.urlopen(url)        
    #print "Reading: " + barcode
    xml = f.read()  
    #print "Received: " + xml
    return xml


class Xtal:
    def __init__(self, *args):
        self.CrystalUUID=""
        self.PinID=""
        self.Login=""
        self.Sample=""
        self.Column=0
        self.idSample=0
        self.idTrial=0
        self.Row=""
        self.Shelf=0
        self.Comments=""
        self.offsetX=0.0
        self.offsetY=0.0
        self.IMG_URL=""
        self.ImageRotation=0.0
        self.SUMMARY_URL=""
        
        
    def getAddress(self):
        return "%s%02d-%d" % (self.Row,self.Column,self.Shelf)

    def getImage(self):
        if (len(self.IMG_URL)==0):
            return None
        if (self.IMG_URL.startswith("http://")):
           self.IMG_URL = "https://" + self.IMG_URL[7];
        #print "Fetching: " + self.IMG_URL
        f = urllib.urlopen(self.IMG_URL)           
        
        img=f.read() 
        return img

    def getSummaryURL(self):
        if (len(self.SUMMARY_URL)==0):
            return None
        return self.SUMMARY_URL
        
class Plate:
    def __init__(self, *args):
        self.Barcode=""
        self.PlateType=""
        self.Xtal=[]

class ProcessingPlan:
    def __init__(self, *args):
        self.Plate=Plate()
 
def getProcessingPlan(barcode):
    try:    
        sxml = getProcessingPlanXML(barcode)
 
        import xml.etree.cElementTree as et
        tree=et.fromstring(sxml)

        pp=ProcessingPlan()
        plate = tree.findall("Plate")[0]

        pp.Plate.Barcode = plate.find("Barcode").text
        pp.Plate.PlateType = plate.find("PlateType").text

        for x in plate.findall("Xtal"):
            xtal=Xtal()
            xtal.CrystalUUID=x.find("CrystalUUID").text
            xtal.PinID=x.find("Label").text
            xtal.Login=x.find("Login").text
            xtal.Sample=x.find("Sample").text
            xtal.Column=int(x.find("Column").text)
            xtal.idSample=int(x.find("idSample").text)
            xtal.idTrial=int(x.find("idTrial").text)
            xtal.Row=x.find("Row").text
            xtal.Shelf=int(x.find("Shelf").text)
            xtal.Comments=x.find("Comments").text
            xtal.offsetX=float(x.find("offsetX").text)
            xtal.offsetY=float(x.find("offsetY").text)
            xtal.IMG_URL=x.find("IMG_URL").text
            xtal.ImageRotation=float(x.find("ImageRotation").text)
            xtal.SUMMARY_URL=x.find("SUMMARY_URL").text
            pp.Plate.Xtal.append(xtal)
        return pp
    except:
        return None




if __name__ == "__main__":
    pp= getProcessingPlan("JZ005209")
    img=getImage("JZ005209",1,'C',12,1)
    print pp
    print pp.Plate
    
    
        
        
    
        
