# Copyright (C) 2021 Members of the Simons Observatory collaboration.
# Please refer to the LICENSE file in the root of this repository.

import time
import numpy as np
from ref import agilent8722es_address
import waferscreen.inst_control.flux_sweep_config as fsc
from waferscreen.inst_control.flux_sweep import AbstractFluxSweep
from waferscreen.data_io.jobs_io import JobOrganizer


class JobDispatch:
    hungry_for_jobs_retry_time_s = 20
    hungry_for_jobs_timeout_hours = 0.01
    minimum_failed_job_search_attempts = 2

    def __init__(self):
        self.a_jobs, self.b_job = None, None
        self.a_chain_flux_sweep = AbstractFluxSweep(rf_chain_letter='a',
                                                    vna_address=agilent8722es_address,
                                                    verbose=True, working_dir=None)
        self.b_chain_flux_sweep = AbstractFluxSweep(rf_chain_letter='b',
                                                    vna_address=agilent8722es_address,
                                                    verbose=True, working_dir=None)
        self.job_organizer = JobOrganizer()

    def __enter__(self):
        self.a_chain_flux_sweep.power_on()
        self.b_chain_flux_sweep.power_on()

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.a_chain_flux_sweep.end()
        self.b_chain_flux_sweep.end()

    def hungry_for_jobs(self, rf_chain_letter):
        calculated_job_search_attempts = int(np.ceil(self.hungry_for_jobs_timeout_hours * 3600 /
                                                     self.hungry_for_jobs_retry_time_s))
        max_job_search_attempts = np.max((self.minimum_failed_job_search_attempts, calculated_job_search_attempts))
        last_job_found_time = time.time()
        failed_attempts_count = 0
        this_chain_flux_sweep = self.__getattribute__(F"{rf_chain_letter}_chain_flux_sweep")
        while failed_attempts_count < max_job_search_attempts:
            job_basename = self.job_organizer.get_next_job_to_process(rf_chain_letter=rf_chain_letter)
            if job_basename is None:
                # refresh and see if new job files were written to the disk
                self.job_organizer = JobOrganizer()
            job_basename = self.job_organizer.get_next_job_to_process(rf_chain_letter=rf_chain_letter)
            if job_basename is None or not self.job_organizer.job_exists():
                # Case: there a not jobs available for this RF chain
                failed_attempts_count += 1
                now = time.time()
                delta_t_minutes = (last_job_found_time - now) / 60.0
                print(F"No new sweep jobs for {delta_t_minutes} minutes, " +
                      F"sleeping for {self.hungry_for_jobs_retry_time_s} seconds, " +
                      F"failed attempt {failed_attempts_count} of {max_job_search_attempts}.")
                time.sleep(self.hungry_for_jobs_retry_time_s)
            else:
                # Case: there is at least on job file
                # get the seed files and launch the flux sweeps
                job_type, seed_files = self.job_organizer.get_seed_files_from_job(job_basename=job_basename)
                if job_type == "single_res":
                    this_chain_flux_sweep.single_res_survey_from_job_file(seed_files)
                else:
                    raise TypeError(F"{job_type} is not a recognized job_type.")
                # The jobs based on any number of seed files are now completed, mark this job completed
                self.job_organizer.mark_job_completed(job_basename=job_basename)

                # reset the attempts counter
                failed_attempts_count = 0
                last_job_found_time = time.time()


if __name__ == "__main__":
    rf_chain = "b"  # choose either {"a", "b"}
    do_scan = False
    do_res_sweeps = not do_scan

    if do_scan:
        abstract_flux_sweep = AbstractFluxSweep(rf_chain_letter=rf_chain)
        with abstract_flux_sweep:
            abstract_flux_sweep.scan_for_resonators(fmin_GHz=fsc.scan_f_min_GHz, fmax_GHz=fsc.scan_f_max_GHz)

    if do_res_sweeps:
        # resonator sweeps based on an analyzed scan
        job_dispatch = JobDispatch()
        with job_dispatch:
            job_dispatch.hungry_for_jobs(rf_chain_letter=rf_chain)
