from ref import usbvna_address, agilent8722es_address
from waferscreen.inst_control.vnas import AbstractVNA


class AbstractFluxSweep:
    """
    Manages the AbstractVNA and FluxRamp controllers
     Optimized for resonator measurements:
     1) long sweeps for scanning
     2) fast switching for many smaller sweeps 'on resonance'
    """
    def __init__(self, vna_address=agilent8722es_address, verbose=True):
        self.abstract_vna = AbstractVNA(vna_address=vna_address, verbose=verbose)
