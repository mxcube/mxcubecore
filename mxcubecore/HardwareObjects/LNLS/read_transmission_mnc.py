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
import math

from epics import PV


def read_input():
    # Read inputs from terminal
    ap = argparse.ArgumentParser()
    ap.add_argument("-e", "--energy", required=True, type=float, help="Energy of the x-ray beam [keV]")
    args = vars(ap.parse_args())
    return args

def read_transmission(energy):
    # Expressions (interpolation) for calculations of MU (linear attenuation coeficient [cm^-1]) for each material in function of the beam energy.
    # The data used to obtain the expressions (curve fitting) are from  "https://physics.nist.gov/PhysRefData/FFast/html/form.html"
    # This attenuation coeficients can be verified and optimised after experimental validation at the beamline.
    MU_Al = (78657.01011 * math.exp(-energy/0.65969)) + (6406.36151 * math.exp(-energy/1.63268)) + (492.29999 * math.exp(-energy/4.42554)) + (3.2588)
    MU_Ti = (28062.17632 * math.exp(-energy/1.88062)) + (6354120 * math.exp(-energy/0.49973)) + (2257.91488 * math.exp(-energy/5.28296)) + (17.4342)
    MU_Cu = (1147850000 * math.exp(-energy/0.56933)) + (2582.7593 * math.exp(-energy/8.40671)) + (30628.08291 * math.exp(-energy/2.98937)) + (22.4187)
    MU_Au = (42783.04258 * math.exp(-energy/5.39244)) + (399.59714)
    MU_Zr = (11143.28458 * math.exp(-energy/5.87029)) + (102.27474)
    MU_EMPTY = 0.0

    foils_pv = {'F1_Al':(8, MU_Al, PV('MNC:B:RIO01:9425A:bi11'), PV('MNC:B:RIO01:9425A:bi12')),
                'F2_Al':(10, MU_Al, PV('MNC:B:RIO01:9425A:bi10'), PV('MNC:B:RIO01:9425A:bi13')),
                'F3_Al':(20, MU_Al, PV('MNC:B:RIO01:9425A:bi9'), PV('MNC:B:RIO01:9425A:bi14')),
                'F4_Al':(80, MU_Al, PV('MNC:B:RIO01:9425A:bi8'), PV('MNC:B:RIO01:9425A:bi15')),
                'F5_Al':(160, MU_Al, PV('MNC:B:RIO01:9425A:bi7'), PV('MNC:B:RIO01:9425A:bi16')),
                'F6_Al':(320, MU_Al, PV('MNC:B:RIO01:9425A:bi6'), PV('MNC:B:RIO01:9425A:bi17')),
                'F7_Al':(800, MU_Al, PV('MNC:B:RIO01:9425A:bi5'), PV('MNC:B:RIO01:9425A:bi18')),
                'F8_Al':(1500, MU_Al, PV('MNC:B:RIO01:9425A:bi4'), PV('MNC:B:RIO01:9425A:bi19')),
                'F9_Ti':(8, MU_Ti, PV('MNC:B:RIO01:9425A:bi3'), PV('MNC:B:RIO01:9425A:bi20')),
                'F10_Cu':(10, MU_Cu, PV('MNC:B:RIO01:9425A:bi2'), PV('MNC:B:RIO01:9425A:bi21')),
                'F11_Au':(5, MU_Au, PV('MNC:B:RIO01:9425A:bi1'), PV('MNC:B:RIO01:9425A:bi22')),
                'F12_Zr':(25, MU_Zr, PV('MNC:B:RIO01:9425A:bi0'), PV('MNC:B:RIO01:9425A:bi23'))}

    # check what foils are in the the beam and calculate MU*x and then calculate transmission

    # the commented lines bellow works for the attenuator expected logic (0 for foil out and 1 for foil in).
    # as the current logic is inverted (1 is foil out and 0 is foil in) use the uncommented lines.
    foils_in = []
    for foil in foils_pv.keys():
        # if foils_pv[foil][2].get() == 1 and foils_pv[foil][3].get() == 0:
        if foils_pv[foil][2].get() == 0 and foils_pv[foil][3].get() == 1:
            atten_mu_x = float(foils_pv[foil][0] * 1.0E-4) * foils_pv[foil][1]
            foils_in.append(atten_mu_x)
            status = 0
        # elif foils_pv[foil][2].get() == 0 and foils_pv[foil][3].get() == 1:
        elif foils_pv[foil][2].get() == 1 and foils_pv[foil][3].get() == 0:
            status = 0
        else:
            status = 1

    MU_x = sum(foils_in)
    transmission = 1.0 * (math.exp(-MU_x))

    return transmission, status


def main():
    energy = read_input()['energy']
    T = read_transmission(energy)
    transmission = round(T[0] * 100, 2)
    foil_status = T[1]

if __name__ == "__main__":
    main()
