#!/usr/bin/python
import numpy as np
import math
import os
import matplotlib.pyplot as plt
from ref import pro_data_dir


"""
########################################################################################################################
#### Resonance Finding Script
#### Written by Jake Connors 24 Jan 2020, v2 10 March 2020
#### Consumes an array of complex s21 transmission data
#### Removes absolute gain, gain slope and group delay from data
#### Smooths data using a savitsky-golay filter to reduce noise in derivatives
#### Optionally removes baseline ripple using a wider savitsky-golay filter
#### Takes complex 1st derivative of s21 data w.r.t. frequency
#### Finds component of 1st derivative in the amplitude and phase directions given s21 position
#### Searches for maxima of Qt~f/2*ds21/df*theta-hat above a given threshold and minimum spacing to identify resonances
#### Returns a list of resonant frequencies and optionally writes this to a text file
########################################################################################################################
"""


