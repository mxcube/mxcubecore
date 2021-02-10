#!/usr/bin/env python3
# -*- coding: utf-8 -*-
 
"""Transmission control for MANACA.
   Attenuator: ABS-300-12-C-DN-DN40 Flanges.
   Foils: #1, 8 um Al;
          #2, 10 um Al;
          #3, 20 um Al;
          #4, 80 um Al;
          #5, 160 um Al;
          #6, 320 um Al;
          #7, 800 um Al;
          #8, 1500 um Al;
          #9, 8 um Ti;
          #10, 10 um Cu
          #11, 5 um Au;
          #12, 25 um Zr.
    Here we use the Beer-Lambert law to calculate the transmission/attenuation: I = I0 * e^-(MU * d)
    were I is the transmitted (final) beam intensity, I0 is the incident (initial) beam intensity,
    MU is the linear attenuation coeficient (cm^-1) and d is the thickness of the foil (cm).
"""
import argparse
from epics import PV
import itertools
import math
import time


def read_input():
    # Read inputs from terminal
    ap = argparse.ArgumentParser()
    ap.add_argument("-e", "--energy", required=True, type=float, help="Energy of the x-ray beam [keV]")
    ap.add_argument("-t", "--transmission", required=True, type=float, help="Transmission to be set, [%]")
    args = vars(ap.parse_args())
    return args

def get_transmission(energy, transmission):
    transmission = transmission/100
    # Expressions (interpolation) for calculations of MU (linear attenuation coeficient [cm^-1]) for each material in function of the beam energy. 
    # The data used to obtain the expressions (curve fitting) are from  "https://physics.nist.gov/PhysRefData/FFast/html/form.html"
    # This attenuation coeficients can be verified and optimised after experimental validation at the beamline.
    MU_Al = (78657.01011 * math.exp(-energy/0.65969)) + (6406.36151 * math.exp(-energy/1.63268)) + (492.29999 * math.exp(-energy/4.42554)) + (3.2588)
    MU_Ti = (28062.17632 * math.exp(-energy/1.88062)) + (6354120 * math.exp(-energy/0.49973)) + (2257.91488 * math.exp(-energy/5.28296)) + (17.4342)
    MU_Cu = (1147850000 * math.exp(-energy/0.56933)) + (2582.7593 * math.exp(-energy/8.40671)) + (30628.08291 * math.exp(-energy/2.98937)) + (22.4187)
    MU_Au = (42783.04258 * math.exp(-energy/5.39244)) + (399.59714)
    MU_Zr = (11143.28458 * math.exp(-energy/5.87029)) + (102.27474)
    MU_EMPTY = 0.0
    # Foils in ABS-attenuator. The dictionary gives the foil position and material in the key (e.g. 'F1_Al', position 1 occuped by an aluminium foil),
    # and the thickness [um] in the value. The list gives the positions and materials, similar to the dictionary, and it is used in the combination. 
    foils_dict = {'F0_EMPTY':0, 'F1_Al':8, 'F2_Al':10, 'F3_Al':20, 'F4_Al':80, 'F5_Al':160, 'F6_Al':320, 'F7_Al':800,
                  'F8_Al':1500, 'F9_Ti':8, 'F10_Cu':10, 'F11_Au':5, 'F12_Zr':25}

    attenuator_position = ['F0_EMPTY', 'F1_Al', 'F2_Al', 'F3_Al', 'F4_Al', 'F5_Al', 'F6_Al', 'F7_Al', 'F8_Al',
                           'F9_Ti', 'F10_Cu', 'F11_Au', 'F12_Zr']
    # conditions to use only the continous part of the absorption spectra and not the edge region. It can be optimised after experimental validation.
    if energy < 6.5:
        attenuator_position = attenuator_position[0:9]
    elif 6.5 <= energy < 9.5 :
        attenuator_position = attenuator_position[0:10]
    elif 9.5 <= energy < 15.0 :
        attenuator_position = attenuator_position[0:11]
    elif 15.0 <= energy < 18.5 :
        attenuator_position = attenuator_position[0:12]
    elif energy >= 18.5:
        attenuator_position = attenuator_position[0:13]
    
    foils_comb = []
    atten_coef_sum = []
    
    # calculate the all possible unique combinations
    for i in range(1, len(attenuator_position)+1):
        product = itertools.combinations(attenuator_position, i)
        for item in product:
            foils_comb.append(list(item))
    # calculate the product of MU (cm^-1) * thickness (cm) for each material (MU * d)
    # and sum the products to obtain the total (final) attenuation for each possible combination.
    # and put the results (total attenuation) in a list. 
    comb_sum = []
    for item in foils_comb:
        comb_tmp = []
        for sub_item in item:
            if '_Al' in sub_item:
                atten_mu_x = float(foils_dict[sub_item] * 1.0E-4) * MU_Al
                comb_tmp.append(atten_mu_x)
            elif '_Ti' in sub_item:
                atten_mu_x = float(foils_dict[sub_item] * 1.0E-4) * MU_Ti
                comb_tmp.append(atten_mu_x)
            elif '_Cu' in sub_item:
                atten_mu_x = float(foils_dict[sub_item] * 1.0E-4) * MU_Cu
                comb_tmp.append(atten_mu_x)
            elif '_Au' in sub_item:
                atten_mu_x = float(foils_dict[sub_item] * 1.0E-4) * MU_Au
                comb_tmp.append(atten_mu_x)
            elif '_Zr' in sub_item:
                atten_mu_x = float(foils_dict[sub_item] * 1.0E-4) * MU_Zr
                comb_tmp.append(atten_mu_x)
            elif '_EMPTY' in sub_item:
                atten_mu_x = float(foils_dict[sub_item] * 1.0E-4) * MU_EMPTY
                comb_tmp.append(atten_mu_x)

        comb_sum.append(sum(comb_tmp))

    # create a dictionary to correlate the combinations of foils (value) with the total attenuation (key)
    FOILS = dict(zip(comb_sum, foils_comb))
    # calculate the transmission for each combination using the product calculated before (the keys of FOILS)
    FOILS_T = {1.0 * (math.exp(-k)) : v for k, v in FOILS.items()}
    # find the closest transmission that is possible to obtain with the foils on ABS-300.
    closest_transmission = min(FOILS_T.keys(), key=lambda k:abs(float(k)-transmission))
    # get the foil combination for the closest transmission found
    filter_combination = FOILS_T[closest_transmission]

    return transmission, closest_transmission, filter_combination


def set_foils(filter_combination):
    
    # declare a list with available foils and a dictionary with epics PV class (FOIL ACT, FOIL IN, FOIL OUT) for each foil
    attenuator_position = ['F1_Al', 'F2_Al', 'F3_Al', 'F4_Al', 'F5_Al', 'F6_Al', 'F7_Al', 'F8_Al',
                           'F9_Ti', 'F10_Cu', 'F11_Au', 'F12_Zr']
    
    foils_pv = {'F1_Al':(PV('MNC:B:RIO01:9474C:bo0'), PV('MNC:B:RIO01:9425A:bi11'), PV('MNC:B:RIO01:9425A:bi12')),
                 'F2_Al':(PV('MNC:B:RIO01:9474C:bo1'), PV('MNC:B:RIO01:9425A:bi10'), PV('MNC:B:RIO01:9425A:bi13')),
                 'F3_Al':(PV('MNC:B:RIO01:9474C:bo2'), PV('MNC:B:RIO01:9425A:bi9'), PV('MNC:B:RIO01:9425A:bi14')),
                 'F4_Al':(PV('MNC:B:RIO01:9474C:bo3'), PV('MNC:B:RIO01:9425A:bi8'), PV('MNC:B:RIO01:9425A:bi15')),
                 'F5_Al':(PV('MNC:B:RIO01:9474C:bo4'), PV('MNC:B:RIO01:9425A:bi7'), PV('MNC:B:RIO01:9425A:bi16')),
                 'F6_Al':(PV('MNC:B:RIO01:9474C:bo5'), PV('MNC:B:RIO01:9425A:bi6'), PV('MNC:B:RIO01:9425A:bi17')),
                 'F7_Al':(PV('MNC:B:RIO01:9474C:bo6'), PV('MNC:B:RIO01:9425A:bi5'), PV('MNC:B:RIO01:9425A:bi18')),
                 'F8_Al':(PV('MNC:B:RIO01:9474C:bo7'), PV('MNC:B:RIO01:9425A:bi4'), PV('MNC:B:RIO01:9425A:bi19')),
                 'F9_Ti':(PV('MNC:B:RIO01:9474D:bo0'), PV('MNC:B:RIO01:9425A:bi3'), PV('MNC:B:RIO01:9425A:bi20')),
                 'F10_Cu':(PV('MNC:B:RIO01:9474D:bo1'), PV('MNC:B:RIO01:9425A:bi2'), PV('MNC:B:RIO01:9425A:bi21')),
                 'F11_Au':(PV('MNC:B:RIO01:9474D:bo2'), PV('MNC:B:RIO01:9425A:bi1'), PV('MNC:B:RIO01:9425A:bi22')),
                 'F12_Zr':(PV('MNC:B:RIO01:9474D:bo3'), PV('MNC:B:RIO01:9425A:bi0'), PV('MNC:B:RIO01:9425A:bi23'))}

    # setup the foils: check foil status, put the foils in the 'filter_combination' and remove the others
    
    wt = 0.1
    
    # the commented lines bellow works for the attenuator expected logic (0 for foil out and 1 for foil in).
    # as the current logic is inverted (1 is foil out and 0 is foil in) use the uncommented lines.

    for foil in attenuator_position:
        if foil in filter_combination:
            # if foils_pv[foil][1].get() == 0 and foils_pv[foil][2].get() == 1:
            if foils_pv[foil][1].get() == 1 and foils_pv[foil][2].get() == 0:
                # foils_pv[foil][0].put(1)
                foils_pv[foil][0].put(0)
                status = 0
                time.sleep(wt)
            # elif foils_pv[foil][1].get() == 1 and foils_pv[foil][2].get() == 0:
            elif foils_pv[foil][1].get() == 0 and foils_pv[foil][2].get() == 1:
                status = 0
            elif foils_pv[foil][1].get() == foils_pv[foil][2].get():
                status = 1
                break
        else:
            # if foils_pv[foil][1].get() == 0 and foils_pv[foil][2].get() == 1:
            if foils_pv[foil][1].get() == 1 and foils_pv[foil][2].get() == 0:
                status = 0
            # elif foils_pv[foil][1].get() == 1 and foils_pv[foil][2].get() == 0:
            elif foils_pv[foil][1].get() == 0 and foils_pv[foil][2].get() == 1:
                # foils_pv[foil][0].put(0)
                foils_pv[foil][0].put(1)
                status = 0
                time.sleep(wt)
            elif foils_pv[foil][1].get() == foils_pv[foil][2].get():
                status = 1
                break
    
    return status


def main():
    energy = read_input()['energy']
    transmission = read_input()['transmission']
    transmission_setup = get_transmission(energy, transmission)
    # transmission required by the user
    user_transmission = transmission_setup[0] * 100
    # real transmission got with calculated foil combination 
    actual_transmission = round(transmission_setup[1] * 100, 2)
    # calculated foil combination to get the required transmission
    filter_combination = transmission_setup[2]
    # put the foils and check if the they were correctly positioned (status:0 = ok; 1 = fail)
    foil_status = set_foils(filter_combination)

if __name__ == "__main__":
    main()
