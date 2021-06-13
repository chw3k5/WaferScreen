# Copyright (C) 2021 Members of the Simons Observatory collaboration.
# Please refer to the LICENSE file in the root of this repository.
import datetime
import os
import time
import numpy as np
import logging
from threading import Thread
from ref import agilent8722es_address, today_str
from waferscreen.inst_control.vnas import AbstractVNA
from waferscreen.inst_control.srs import SRS_SIM928, SRS_Connect
from waferscreen.data_io.s21_metadata import MetaDataDict
from waferscreen.data_io.s21_io import write_s21, dirname_create, read_s21
import waferscreen.inst_control.flux_sweep_config as fsc
from waferscreen.data_io.screener_read import screener_sheet
from waferscreen.analyze.res_pipeline_config import processing_metadata_to_remove_from_seeds
from waferscreen.inst_control.starcryo_monitor import Monitor, log_checker
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
    if current_uA >= 0.0:
        current_str = F"+{'%05.1f' % current_uA}"
    else:
        current_str = str('%06.1f' % current_uA)
    return F"sdata_res_{res_num}_cur_{current_str}uA_{power_dBm}dBm_utc{utc.replace(':', '-')}.csv"


def dirname_create_raw(sweep_type="scan", res_id=None):
    path_str = dirname_create(output_basedir=fsc.output_base_dir, location=fsc.location,
                              wafer=screener_sheet.wafers_this_cool_down, date_str=today_str,
                              is_raw=True, sweep_type=sweep_type, res_id=res_id)
    return path_str


def thread_function(name):
    """
    A simple test function to practice on
    :param name:
    :return:
    """
    logging.info("Thread %s: starting", name)
    time.sleep(2)
    logging.info("Thread %s: finishing", name)


class AbstractFluxSweep:
    """
    Manages the AbstractVNA and FluxRamp controllers
     Optimized for resonator measurements:
     1) long sweeps for scanning
     2) fast switching for many smaller sweeps 'on resonance'
    """
    # one connection is shared by all instances of this class
    flux_ramp_srs_connect = SRS_Connect(address=ref.flux_ramp_address)

    def __init__(self, rf_chain_letter, vna_address=agilent8722es_address, verbose=True, working_dir=None,
                 monitor_starcryo=True):
        # For the star Cryo Monitoring system
        self.monitor_thread = None
        self.is_in_regulation = None
        self.starcryo_monitor = Monitor()
        if monitor_starcryo:
            self.start_monitor()
        # the instrument connections
        test_letter = rf_chain_letter.lower().strip()
        if test_letter == "a":
            self.ramp = SRS_SIM928(srs_port=1, srs_connect=self.flux_ramp_srs_connect)
            self.rf_chain = "a"
        elif test_letter == "b":
            # self.ramp = SRS_SIM928(srs_port=2, srs_connect=self.flux_ramp_srs_connect)
            self.ramp = SRS_SIM928(srs_port=1, srs_connect=self.flux_ramp_srs_connect)
            self.rf_chain = "b"
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
        if self.monitor_thread is not None:
            self.starcryo_monitor.stop_log_check()

    def power_on(self):
        self.ramp.output_on()
        self.abstract_vna.power_on()

    def power_off(self):
        self.ramp.setvolt(voltage=0.0)
        self.ramp.output_off()
        self.abstract_vna.set_port_power_dbm(port_power_dbm=-70)
        self.abstract_vna.power_off()

    def close_connections(self):
        self.abstract_vna.close_connection()

    def end(self):
        self.power_off()
        self.close_connections()

    def step(self, **kwargs):
        # initialize the data storage tools
        flux_ramp_voltage = kwargs['flux_supply_v']
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
        freqs_GHz, s21real, s21imag, vna_sweep_metadata = self.abstract_vna.vna_sweep()
        # write out sdata
        if kwargs["export_type"] == "scan":
            dirname = dirname_create_raw(sweep_type=kwargs["export_type"])
            basename = F"scan{'%2.3f' % vna_sweep_metadata['fmin_ghz']}GHz-{'%2.3f' % vna_sweep_metadata['fmax_ghz']}GHz_" + \
                       F"{vna_sweep_metadata['utc'].replace(':', '-')}.csv"
        elif kwargs["export_type"] == "single_res":
            basename = ramp_name_create(power_dBm=vna_sweep_metadata['port_power_dbm'],
                                        current_uA=metadata_this_sweep['flux_current_ua'],
                                        res_num=metadata_this_sweep['res_num'],
                                        utc=vna_sweep_metadata['utc'])
            dirname = metadata_this_sweep['dirname']
        else:
            raise TypeError

        vna_sweep_metadata['path'] = os.path.join(dirname, basename)
        vna_sweep_metadata['rf_chain'] = self.rf_chain
        metadata_this_sweep.update(vna_sweep_metadata)
        self.write(output_file=vna_sweep_metadata['path'], freqs_ghz=freqs_GHz, s21_complex=s21real + 1j * s21imag,
                   metadata=metadata_this_sweep)

    @staticmethod
    def write(output_file, freqs_ghz, s21_complex, metadata):
        write_s21(output_file, freqs_ghz, s21_complex, metadata)

    def survey_ramp(self, resonator_metadata, dwell=None):
        # only make measurements while the ADR system is in regulation
        while not self.starcryo_monitor.is_in_regulation:
            now = datetime.datetime.now()
            print(F"\nThe flux ramp survey is paused while not the StarCryo System is not in regulation.")
            print(F"  Current local time: {now.strftime('%H:%M:%S')}, rechecking regulation " +
                  F"status every {self.starcryo_monitor.sleep_time_s} seconds")
            time.sleep(self.starcryo_monitor.sleep_time_s)
        # Start the flux ramp survey for this resonator
        for counter, flux_supply_V in list(enumerate(fsc.ramp_volts)):
            if counter == 0 and dwell is not None:
                # dwell after the ramp is reset.
                time.sleep(dwell)
            resonator_metadata['flux_current_ua'] = fsc.ramp_volt_to_uA[flux_supply_V]
            resonator_metadata['flux_supply_v'] = flux_supply_V
            resonator_metadata['ramp_series_resistance_ohms'] = fsc.ramp_rseries
            self.step(**resonator_metadata)

    def survey_power_ramp(self, resonator_metadata, in_regulation=False):
        for port_power_dBm in fsc.power_sweep_dBm:
            resonator_metadata["port_power_dbm"] = port_power_dBm
            resonator_metadata["num_freq_points"] = fsc.ramp_num_freq_points
            resonator_metadata["sweeptype"] = fsc.sweeptype
            resonator_metadata["if_bw_hz"] = fsc.if_bw_Hz
            resonator_metadata["vna_avg"] = fsc.vna_avg
            self.survey_ramp(resonator_metadata, in_regulation=in_regulation)

    def scan_for_resonators(self, fmin_GHz, fmax_GHz, group_delay_s=None, **kwargs):
        if fmin_GHz > fmax_GHz:
            fmin_GHz, fmax_GHz = fmax_GHz, fmin_GHz
        scan_stepsize_GHz = fsc.scan_stepsize_kHz * 1.e-6
        # set the default values from the config file
        resonator_metadata = {'flux_current_ua': 0.0, 'flux_supply_v': 0.0, "export_type": "scan",
                              'ramp_series_resistance_ohms': fsc.ramp_rseries, "port_power_dbm": fsc.probe_power_dBm,
                              "sweeptype": fsc.sweeptype, "if_bw_Hz": fsc.if_bw_Hz, "vna_avg": fsc.vna_avg,
                              "fspan_ghz": fmax_GHz - fmin_GHz, "fcenter_ghz": (fmax_GHz + fmin_GHz) / 2.0,
                              "location": fsc.location, "wafer": screener_sheet.wafers_this_cool_down}
        # overwrite the default values with what ever was sent by the use
        for user_key in kwargs.keys():
            resonator_metadata[user_key] = kwargs[user_key]
        resonator_metadata["num_freq_points"] = int(np.round(resonator_metadata["fspan_ghz"] / scan_stepsize_GHz))
        if group_delay_s is not None:
            resonator_metadata["group_delay_s"] = group_delay_s
        self.step(**resonator_metadata)

    def single_res_survey_from_job_file(self, seed_files, in_regulation=False):
        for seed_file in seed_files:
            seed_dirname, seed_file_basename = os.path.split(seed_file)
            all_files_in_seed_dir = os.listdir(seed_dirname)
            # skip files that have already have data
            if len(all_files_in_seed_dir) < 2:
                _, metadata_seed, res_params = read_s21(path=seed_file, return_res_params=True)
                for res_param in res_params:
                    fcenter_GHz = res_param.fcenter_ghz
                    quality_factor_total = (res_param.q_i * res_param.q_c) / (res_param.q_c + res_param.q_i)
                    quality_factor_bw_GHz = fcenter_GHz / quality_factor_total
                    fspan_GHz = quality_factor_bw_GHz * fsc.ramp_span_as_multiple_of_quality_factor
                    res_num = res_param.res_number
                    resonator_metadata = {"export_type": "single_res",
                                          "res_id": F"res{res_num}_{metadata_seed['seed_base']}",
                                          "res_num": res_num,
                                          "seed_group_delay_s": metadata_seed["group_delay_found_s"],
                                          "fspan_ghz": fspan_GHz,
                                          "fcenter_ghz": fcenter_GHz,
                                          "dirname": seed_dirname,
                                          "location": fsc.location}
                    # update with all non-processing metadata (processing will start fresh for the new data).
                    for seed_key in metadata_seed.keys():
                        if seed_key not in processing_metadata_to_remove_from_seeds \
                                and seed_key not in resonator_metadata.keys():
                            resonator_metadata[seed_key] = metadata_seed[seed_key]
                    self.survey_power_ramp(resonator_metadata, in_regulation=in_regulation)

    def start_monitor(self):
        self.monitor_thread = Thread(target=log_checker, args=(self.starcryo_monitor,), daemon=True)
        self.monitor_thread.start()
        self.is_in_regulation = self.starcryo_monitor.is_in_regulation






