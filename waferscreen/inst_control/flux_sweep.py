import os
import time
import numpy as np
from ref import agilent8722es_address, today_str
from waferscreen.inst_control.vnas import AbstractVNA
from waferscreen.inst_control.srs import SRS_SIM928, SRS_Connect
from waferscreen.analyze.s21_metadata import MetaDataDict
from waferscreen.analyze.s21_io import write_s21, dirname_create
import waferscreen.inst_control.flux_sweep_config as fsc
import ref


def ramp_name_parse(basename):
    res_num_str, current_uA_and_power_utc_str = basename.rstrip('.csv').lstrip("sdata_res_").split('_cur_')
    current_str, power_utc_str = current_uA_and_power_utc_str.split("uA_")
    power_str, utc = power_utc_str.split("dBm_utc")
    if "m" == current_str[0]:
        current_uA = -1.0 * float(current_str[1:])
    else:
        current_uA = float(current_str)
    power_dBm = float(power_str)
    res_num = int(res_num_str)
    return power_dBm, current_uA, res_num, utc


def ramp_name_create(power_dBm, current_uA, res_num, utc):
    return F"sdata_res_{res_num}_cur_{int(round(current_uA))}uA_{power_dBm}dBm_utc{utc}.csv"


def dirname_create_raw(sweep_type="scan", res_id=None):
    path_str = dirname_create(output_basedir=fsc.output_base_dir, location=fsc.location,
                              wafer=fsc.wafer, date_str=today_str, sweep_type=sweep_type, res_id=res_id)
    raw_dir = os.path.join(path_str, "raw")
    if not os.path.isdir(raw_dir):
        os.mkdir(raw_dir)
    return raw_dir


class AbstractFluxSweep:
    """
    Manages the AbstractVNA and FluxRamp controllers
     Optimized for resonator measurements:
     1) long sweeps for scanning
     2) fast switching for many smaller sweeps 'on resonance'
    """
    # one connection is shared by all instances of this class
    flux_ramp_srs_connect = SRS_Connect(address=ref.flux_ramp_address)

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
            self.working_dir = ref.working_dir
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

    def step(self, **kwargs):
        # initialize the data storage tools
        flux_ramp_voltage = kwargs['flux_supply_V']
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
        if kwargs["export_type"] == "scan":
            dirname = dirname_create_raw(sweep_type=kwargs["export_type"])
            basename = F"scan{'%2.3f' % sweep_metadata['fmin_GHz']}GHz-{'%2.3f' % sweep_metadata['fmax_GHz']}GHz_" + \
                       F"{sweep_metadata['utc'].replace(':', '-')}.csv"
        else:
            basename = ramp_name_create(power_dBm=sweep_metadata['port_power_dBm'],
                                        current_uA=sweep_metadata['flux_current_uA'],
                                        res_num=sweep_metadata['res_num'],
                                        utc=sweep_metadata['utc'])
            dirname = dirname_create_raw(sweep_type=kwargs["export_type"], res_id=sweep_metadata['res_id'])
        sweep_metadata['path'] = os.path.join(dirname, basename)
        metadata_this_sweep.update(sweep_metadata)
        self.write(output_file=sweep_metadata['path'], freqs_ghz=freqs_GHz, s21_complex=s21real + 1j * s21imag,
                   metadata=metadata_this_sweep)

    @staticmethod
    def write(output_file, freqs_ghz, s21_complex, metadata):
        write_s21(output_file, freqs_ghz, s21_complex, metadata)

    def survey_ramp(self, resonator_metadata, dwell=None):
        for counter, flux_supply_V in list(enumerate(fsc.ramp_volts)):
            if counter == 0 and dwell is not None:
                # dwell after the ramp is reset.
                time.sleep(dwell)
            resonator_metadata['flux_current_uA'] = fsc.ramp_volt_to_uA[flux_supply_V]
            resonator_metadata['flux_supply_V'] = flux_supply_V
            resonator_metadata['ramp_series_resistance_ohms'] = fsc.ramp_rseries
            self.step(**resonator_metadata)

    def survey_power_ramp(self, resonator_metadata):
        for port_power_dBm in fsc.power_sweep_dBm:
            resonator_metadata["port_power_dBm"] = port_power_dBm
            resonator_metadata["fspan_GHz"] = resonator_metadata["fcenter_GHz"] / fsc.span_scale_factor
            resonator_metadata["num_freq_points"] = fsc.num_freq_points
            resonator_metadata["sweeptype"] = fsc.sweeptype
            resonator_metadata["if_bw_Hz"] = fsc.if_bw_Hz
            resonator_metadata["vna_avg"] = fsc.vna_avg
            self.survey_ramp(resonator_metadata)

    def resonator_ramp_survey(self, resonator_freqs_GHz, scan_name):
        for res_num, fcenter_GHz in list(enumerate(resonator_freqs_GHz)):
            resonator_metadata = {"fcenter_GHz": fcenter_GHz, "res_id": F"{res_num}_{scan_name}",
                                  "export_type": "single_res"}
            self.survey_power_ramp(resonator_metadata)

    def scan_for_resonators(self, fmin_GHz, fmax_GHz, group_delay_s=None, **kwargs):
        if fmin_GHz > fmax_GHz:
            fmin_GHz, fmax_GHz = fmax_GHz, fmin_GHz
        scan_stepsize_GHz = fsc.scan_stepsize_kHz * 1.e-6
        # set the default values from the config file
        resonator_metadata = {'flux_current_uA': 0.0, 'flux_supply_V': 0.0, "export_type": "scan",
                              'ramp_series_resistance_ohms': fsc.ramp_rseries, "port_power_dBm": fsc.probe_power_dBm,
                              "sweeptype": fsc.sweeptype, "if_bw_Hz": fsc.if_bw_Hz, "vna_avg": fsc.vna_avg,
                              "fspan_GHz": fmax_GHz - fmin_GHz, "fcenter_GHz": (fmax_GHz + fmin_GHz) / 2.0}
        # overwrite the defult values with what ever was sent by the use
        for user_key in kwargs.keys():
            resonator_metadata[user_key] = kwargs[user_key]
        resonator_metadata["num_freq_points"] = int(np.round(resonator_metadata["fspan_GHz"] / scan_stepsize_GHz))
        if group_delay_s is not None:
            resonator_metadata["group_delay_s"] = group_delay_s
        self.step(**resonator_metadata)


if __name__ == "__main__":
    afs = AbstractFluxSweep(rf_chain_letter="a")
    with afs:
        for if_bw_Hz in [300, 100]:
            afs.scan_for_resonators(fmin_GHz=fsc.scan_f_min_GHz, fmax_GHz=fsc.scan_f_max_GHz, if_bw_Hz=if_bw_Hz)






