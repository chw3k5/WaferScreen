import os
import time
import numpy as np
import logging
from ref import agilent8722es_address, today_str
from waferscreen.inst_control.vnas import AbstractVNA
from waferscreen.inst_control.srs import SRS_SIM928, SRS_Connect
from waferscreen.data_io.s21_metadata import MetaDataDict
from waferscreen.data_io.s21_io import write_s21, dirname_create, read_s21
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
    if current_uA >= 0.0:
        current_str = F"+{'%05.1f' % current_uA}"
    else:
        current_str = str('%06.1f' % current_uA)
    return F"sdata_res_{res_num}_cur_{current_str}uA_{power_dBm}dBm_utc{utc.replace(':', '-')}.csv"


def dirname_create_raw(sweep_type="scan", res_id=None):
    path_str = dirname_create(output_basedir=fsc.output_base_dir, location=fsc.location,
                              wafer=fsc.wafer, date_str=today_str, is_raw=True, sweep_type=sweep_type, res_id=res_id)
    return path_str


def get_job(chain_letter):
    job_filename = os.path.join(ref.working_dir, F"{chain_letter}_chain_job.csv")
    if os.path.isfile(job_filename):
        with open(job_filename, "r") as f:
            lines = f.readlines()
        job_type = lines[0].strip()
        seed_files = [filename.strip() for filename in lines[1:]]
        return job_type, seed_files
    else:
        return None


def get_jobs():
    return get_job(chain_letter='a'), get_job(chain_letter="b")


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
    hungry_for_jobs_retry_time_s = 20
    hungry_for_jobs_timeout_hours = 0.01

    def __init__(self, rf_chain_letter, vna_address=agilent8722es_address, verbose=True, working_dir=None):
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
        for counter, flux_supply_V in list(enumerate(fsc.ramp_volts)):
            if counter == 0 and dwell is not None:
                # dwell after the ramp is reset.
                time.sleep(dwell)
            resonator_metadata['flux_current_ua'] = fsc.ramp_volt_to_uA[flux_supply_V]
            resonator_metadata['flux_supply_v'] = flux_supply_V
            resonator_metadata['ramp_series_resistance_ohms'] = fsc.ramp_rseries
            self.step(**resonator_metadata)

    def survey_power_ramp(self, resonator_metadata):
        for port_power_dBm in fsc.power_sweep_dBm:
            resonator_metadata["port_power_dbm"] = port_power_dBm
            resonator_metadata["num_freq_points"] = fsc.ramp_num_freq_points
            resonator_metadata["sweeptype"] = fsc.sweeptype
            resonator_metadata["if_bw_hz"] = fsc.if_bw_Hz
            resonator_metadata["vna_avg"] = fsc.vna_avg
            self.survey_ramp(resonator_metadata)

    def scan_for_resonators(self, fmin_GHz, fmax_GHz, group_delay_s=None, **kwargs):
        if fmin_GHz > fmax_GHz:
            fmin_GHz, fmax_GHz = fmax_GHz, fmin_GHz
        scan_stepsize_GHz = fsc.scan_stepsize_kHz * 1.e-6
        # set the default values from the config file
        resonator_metadata = {'flux_current_ua': 0.0, 'flux_supply_v': 0.0, "export_type": "scan",
                              'ramp_series_resistance_ohms': fsc.ramp_rseries, "port_power_dbm": fsc.probe_power_dBm,
                              "sweeptype": fsc.sweeptype, "if_bw_Hz": fsc.if_bw_Hz, "vna_avg": fsc.vna_avg,
                              "fspan_ghz": fmax_GHz - fmin_GHz, "fcenter_ghz": (fmax_GHz + fmin_GHz) / 2.0,
                              "location": fsc.location, "wafer": fsc.wafer}
        # overwrite the default values with what ever was sent by the use
        for user_key in kwargs.keys():
            resonator_metadata[user_key] = kwargs[user_key]
        resonator_metadata["num_freq_points"] = int(np.round(resonator_metadata["fspan_ghz"] / scan_stepsize_GHz))
        if group_delay_s is not None:
            resonator_metadata["group_delay_s"] = group_delay_s
        self.step(**resonator_metadata)

    def single_res_survey_from_job_file(self, seed_files):
        for seed_file in seed_files:
            seed_dirname, seed_file_basename = os.path.split(seed_file)
            all_files_in_seed_dir = os.listdir(seed_dirname)
            # skip files that have already have data
            if len(all_files_in_seed_dir) < 2:
                _, metadata, res_params = read_s21(path=seed_file, return_res_params=True)
                for res_param in res_params:
                    fcenter_GHz = res_param.fcenter_ghz
                    quality_factor_total = (res_param.q_i * res_param.q_c) / (res_param.q_c + res_param.q_i)
                    quality_factor_bw_GHz = fcenter_GHz / quality_factor_total
                    fspan_GHz = quality_factor_bw_GHz * fsc.ramp_span_as_multiple_of_quality_factor
                    res_num = res_param.res_number
                    seed_base = metadata["seed_base"]
                    resonator_metadata = {"export_type": "single_res", "res_id": F"res{res_num}_{seed_base}",
                                          "res_num": res_num, "seed_group_delay_s": metadata["group_delay_found_s"],
                                          "fspan_ghz": fspan_GHz, "fcenter_ghz": fcenter_GHz, "dirname": seed_dirname,
                                          "location": fsc.location, "wafer": metadata["wafer"],
                                          "so_band": metadata["so_band"], "seed_base": seed_base}
                    self.survey_power_ramp(resonator_metadata)

    def hungry_for_jobs(self):
        max_try_attempts = int(np.ceil(2 * (self.hungry_for_jobs_timeout_hours * 3600) /
                                       self.hungry_for_jobs_retry_time_s))
        last_job_found_time = time.time()
        attempts_count = 0
        while attempts_count < max_try_attempts:
            job = get_job(chain_letter=self.rf_chain)
            if job is not None:
                self.survey_from_job_file(job=job)
                last_job_found_time = time.time()
                attempts_count = 0
            else:
                attempts_count += 1
                now = time.time()
                delta_t_minutes = (last_job_found_time - now) / 60.0
                print(F"No new sweep jobs for {delta_t_minutes} minutes, " +
                      F"sleeping for {self.hungry_for_jobs_retry_time_s} seconds, " +
                      F"attempt {'%4i' % attempts_count} of {max_try_attempts}.")
                time.sleep(self.hungry_for_jobs_retry_time_s)

    def survey_from_job_file(self, job):
        job_type, seed_files = job
        if job_type == "single_res":
            self.single_res_survey_from_job_file(seed_files=seed_files)
        else:
            raise TypeError(F"Job type: {job_type} is not recognized.")


class JobAssignment:
    def __init__(self):
        self.a_jobs, self.b_job = None, None
        self.a_chain_flux_sweep = AbstractFluxSweep(rf_chain_letter='a',
                                                    vna_address=agilent8722es_address,
                                                    verbose=True, working_dir=None)
        self.b_chain_flux_sweep = AbstractFluxSweep(rf_chain_letter='b',
                                                    vna_address=agilent8722es_address,
                                                    verbose=True, working_dir=None)

    def __enter__(self):
        self.a_chain_flux_sweep.power_on()
        self.b_chain_flux_sweep.power_on()

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.a_chain_flux_sweep.end()
        self.b_chain_flux_sweep.end()

    def launch_hungry_for_jobs(self, chain_letter="a"):
        self.__getattribute__(F"{chain_letter}_chain_flux_sweep").hungry_for_jobs()


if __name__ == "__main__":
    rf_chain_letter = "b"  # choose either {"a", "b"}
    do_scan = False
    do_res_sweeps = not do_scan

    if do_scan:
        abstract_flux_sweep = AbstractFluxSweep(rf_chain_letter=rf_chain_letter)
        with abstract_flux_sweep:
            abstract_flux_sweep.scan_for_resonators(fmin_GHz=fsc.scan_f_min_GHz, fmax_GHz=fsc.scan_f_max_GHz)

    if do_res_sweeps:
        # resonator sweeps based on an analyzed scan
        job_assign = JobAssignment()
        with job_assign:
            job_assign.launch_hungry_for_jobs(chain_letter=rf_chain_letter)


            # # Not ready for continuous use.
            # format = "%(asctime)s: %(message)s"
            # logging.basicConfig(format=format, level=logging.INFO,
            #                     datefmt="%H:%M:%S")
            # logging.info("Main    : before creating thread")
            # x = threading.Thread(target=job_assign.launch_hungry_for_jobs, args=("a",))
            # logging.info("Main    : before running thread")
            # x.start()
            # logging.info("Main    : wait for the thread to finish")
            # # x.join()
            # logging.info("Main    : all done")







