import os
from ref import usbvna_address, agilent8722es_address
from waferscreen.inst_control.vnas import AbstractVNA
from waferscreen.inst_control.srs import SRS_SIM928, SRS_Connect
from waferscreen.read.s21_metadata import MetaDataDict
from waferscreen.read.s21_inductor import s21_header, write_s21
from ref import flux_ramp_address, raw_data_dir


def ramp_name_parse(basename):
    res_num_str, current_uA_and_power_str = basename.rstrip('dBm.csv').lstrip("sdata_res_").split('_cur_')
    current_str, power_str = current_uA_and_power_str.split("uA_")
    if "m" == current_str[0]:
        current_uA = -1.0 * float(current_str[1:])
    else:
        current_uA = float(current_str)
    power_dBm = float(power_str)
    res_num = int(res_num_str)
    return power_dBm, current_uA, res_num


def ramp_name_create(power_dBm, current_uA, res_num):
    if current_uA >= 0:
        ind_filename = F"sdata_res_{res_num}_cur_{int(round(current_uA))}uA_{power_dBm}dBm.csv"
    else:
        ind_filename = F"sdata_res_{res_num}_cur_m{int(round(-1 * current_uA))}uA_{power_dBm}dBm.csv"
    return ind_filename


class AbstractFluxSweep:
    """
    Manages the AbstractVNA and FluxRamp controllers
     Optimized for resonator measurements:
     1) long sweeps for scanning
     2) fast switching for many smaller sweeps 'on resonance'
    """
    # one connection is shared by all instances of this class
    flux_ramp_srs_connect = SRS_Connect(address=flux_ramp_address)

    def __init__(self, rf_chain_letter, vna_address=agilent8722es_address, verbose=True, working_dir=None):
        test_letter = rf_chain_letter.lower().strip()
        if test_letter == "a":
            self.ramp = SRS_SIM928(srs_port=1, srs_connect=self.flux_ramp_srs_connect)
        elif test_letter == "b":
            self.ramp = SRS_SIM928(srs_port=2, srs_connect=self.flux_ramp_srs_connect)
        else:
            self.ramp = SRS_SIM928(srs_port=rf_chain_letter, srs_connect=self.flux_ramp_srs_connect)
        self.abstract_vna = AbstractVNA(vna_address=vna_address, verbose=verbose)
        self.abstract_vna.vna_init()
        if working_dir is None:
            self.working_dir = raw_data_dir
        else:
            self.working_dir = working_dir

    def __enter__(self):
        self.power_on()

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.end()

    def power_on(self):
        self.ramp.output_on()
        self.abstract_vna.power_on()

    def power_off(self):
        self.ramp.setvolt(voltage=0.0)
        self.ramp.output_off()
        self.abstract_vna.set_port_power_dBm(port_power_dBm=-70)
        self.abstract_vna.power_off()

    def close_connections(self):
        self.abstract_vna.close_connection()

    def end(self):
        self.power_off()
        self.close_connections()

    def ramp_survey(self, **kwargs):
        # initialize the data storage tools
        output_filename = kwargs['path']
        flux_ramp_voltage = kwargs['flux_ramp_mV']
        metadata_this_sweep = MetaDataDict()
        kwargs_keys = set(kwargs.keys())
        vna_settings_keys = kwargs_keys & self.abstract_vna.programmable_settings
        for kwargs_key in kwargs_keys - vna_settings_keys:
            metadata_this_sweep[kwargs_key] = kwargs[kwargs_key]
        # setting for the flux ramp
        if flux_ramp_voltage != self.ramp.last_set_voltage:
            self.ramp.setvolt(flux_ramp_voltage)
        # settings changes for the vna, abstractVNA checks to make sure the changes are needed before setting values
        vna_settings_dict = {vna_setting: kwargs[vna_setting] for vna_setting in vna_settings_keys}
        self.abstract_vna.update_settings(**vna_settings_dict)
        # preform the sweep
        freqs_GHz, s21real, s21imag, sweep_metadata = self.abstract_vna.vna_sweep()
        # write out sdata
        metadata_this_sweep.update(sweep_metadata)
        self.write(output_file=output_filename, freqs_ghz=freqs_GHz, s21_complex=s21real + 1j * s21imag,
                   metadata=metadata_this_sweep)

    @staticmethod
    def write(output_file, freqs_ghz, s21_complex, metadata):
        write_s21(output_file, freqs_ghz, s21_complex, metadata)


if __name__ == "__main__":
    static_vna_settings = {'num_freq_points': 1601, 'sweeptype': 'lin', 'if_bw_Hz': 1000, 'port_power_dBm': -50}
    static_metadata = {"test output": "True"}
    static_metadata.update(static_vna_settings)

    counter = 1
    afs = AbstractFluxSweep(rf_chain_letter="b")
    with afs:
        for fcenter_GHz, fspan_GHz, flux_ramp_mV in [(4, 0.1, 0.011), (8, 0.2, -0.011)]:
            dynamic_kwargs = {"fcenter_GHz": fcenter_GHz, "fspan_GHz": fspan_GHz, "flux_ramp_mV": flux_ramp_mV,
                              "path": os.path.join(raw_data_dir, F"test_output{counter}.txt")}
            static_metadata.update(dynamic_kwargs)
            afs.ramp_survey(**static_metadata)
            counter += 1





