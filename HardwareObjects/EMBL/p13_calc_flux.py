#!/usr/bin/env/ python
import os
import sys

from csv import reader
import numpy as np
from scipy.interpolate import interp1d
 
flux_table_filename = "/opt/embl-hh/etc/p13/app/mxCuBE2/HardwareObjects.xml/p13_flux_table.csv"

def read_file(file_name):
    flux_values = {}
    if os.path.exists(file_name):
        with open(file_name, 'rb') as csv_file:
            csv_reader = reader(csv_file, delimiter = ',')
            row = 0
            flux_values = {}
            for csv_line in csv_reader:
                if len(csv_line) == 1:
                    energy_arr = np.array([])
                    values_arr = np.array([])
                    mode_name = csv_line[0]
                else:
                    energy_arr = np.append(energy_arr, float(csv_line[0]))
                    for col in range(1, len(csv_line)):
                        values_arr = np.append(values_arr, float(csv_line[col]))
                flux_values[mode_name] = {'energy': energy_arr,
                                          'values' : values_arr}
            return flux_values
    else:
        print "File %s does not exist!" % file_name


def calculate_flux(aperture, energy, mode):
    values = read_file(flux_table_filename)
    if values:
        apertures = ['Out', '100', '70', '50', '30', '15', '10', '5']
        try:
           aperture_index = apertures.index(str(aperture))
        except ValueError:
           print "Aperture value %s is not in the list of apertures: %s.'" %(str(aperture), str(apertures))
           print "Out position will be used"
           aperture_index = 0

        if mode in values:
            x_arr = np.flipud(values[mode]['energy'])
            y_arr = np.flipud(values[mode]['values'].reshape(x_arr.size, len(apertures))[:,aperture_index])
            f = interp1d(x_arr, y_arr, kind='cubic')
            return float(f(energy))
        else:
            print "Mode %s not in the list of available modes: %s" %(mode, str(values.keys()))

if __name__ == '__main__' :
   if len(sys.argv) < 3:
       print "Not enough command line argument passed!"
       print "Pass aperture size, energy and mode (small, middle, large) to calculate flux"
   else:
       aper = sys.argv[1]
       energy = float(sys.argv[2])
       mode = sys.argv[3]
       flux = calculate_flux(aper, energy, mode)
       if flux:
           print "Input: aperture %s, energy %.4f, mode: %s. " %(aper, energy, mode)
           print "---------------------------------------------"
           print "Output: calculated flux = %f" %(flux)
            
