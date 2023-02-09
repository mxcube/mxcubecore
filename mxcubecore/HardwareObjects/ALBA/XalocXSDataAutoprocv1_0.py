#
#  Project: MXCuBE
#  https://github.com/mxcube.
#
#  This file is part of MXCuBE software.
#
#  MXCuBE is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  MXCuBE is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.

"""
[Name] XalocXSDataAutoprocInput
 
[Description]
Extending XSDataAutoprocInput to allow doAnomNonanom and xia2 with small molecule

[Signals]
- None
"""

from XSDataAutoprocv1_0 import XSDataAutoprocInput

class XalocXSDataAutoprocInput(XSDataAutoprocInput):
    
    def __init__(
        self,
        configuration=None,
        output_file=None,
        unit_cell=None,
        spacegroup=None,
        nres=None,
        low_resolution_limit=None,
        detector_max_res=None,
        data_collection_id=None,
        cc_half_cutoff=None,
        r_value_cutoff=None,
        isig_cutoff=None,
        completeness_cutoff=None,
        res_override=None,
        input_file=None,
        setDoAnomAndNonanom=None,
    ):
        XSDataAutoprocInput.__init__(
            self, 
            configuration=None,
            output_file=None,
            unit_cell=None,
            spacegroup=None,
            nres=None,
            low_resolution_limit=None,
            detector_max_res=None,
            data_collection_id=None,
            cc_half_cutoff=None,
            r_value_cutoff=None,
            isig_cutoff=None,
            completeness_cutoff=None,
            res_override=None,
            input_file=None,
        )

        if setDoAnomAndNonanom is None:
            self._doAnomAndNonanom = None
        elif setDoAnomAndNonanom.__class__.__name__ == "XSDataBoolean":
            self._doAnomAndNonanom = doAnomAndNonanom
        else:
            strMessage = "ERROR! XSDataInputControlAutoPROC constructor argument 'doAnomAndNonanom' is not XSDataBoolean but %s" % doAnomAndNonanom.__class__.__name__
            raise BaseException(strMessage)
            
    # Methods and properties for the 'doAnomAndNonanom' attribute,  recovered from previous mxcube version
    def getDoAnomAndNonanom(self): return self._doAnomAndNonanom
    def setDoAnomAndNonanom(self, doAnomAndNonanom):
        if doAnomAndNonanom is None:
            self._doAnomAndNonanom = None
        elif doAnomAndNonanom.__class__.__name__ == "XSDataBoolean":
            self._doAnomAndNonanom = doAnomAndNonanom
        else:
            strMessage = "ERROR! XSDataInputControlAutoPROC.setDoAnomAndNonanom argument is not XSDataBoolean but %s" % doAnomAndNonanom.__class__.__name__
            raise BaseException(strMessage)
    def delDoAnomAndNonanom(self): self._doAnomAndNonanom = None

    #def exportChildren(self, outfile, level, name_="XSDataAutoprocInput"):
        #if self._doAnomAndNonanom is not None:
          #self.doAnomAndNonanom.export(outfile, level, name_='doAnomAndNonanom')
        #XSDataAutoprocInput.exportChildren(self, outfile, level, name_)
        

    def exportChildren(self, outfile, level, name_="XSDataAutoprocInput"):
        XSDataAutoprocInput.exportChildren(self, outfile, level, name_)        
        if self._doAnomAndNonanom is not None:
            self._doAnomAndNonanom.export(outfile, level, name_='doAnomAndNonanom')
 
    doAnomAndNonanom = property(getDoAnomAndNonanom, setDoAnomAndNonanom, delDoAnomAndNonanom, "Property for doAnomAndNonanom")
