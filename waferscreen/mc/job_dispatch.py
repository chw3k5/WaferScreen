# Copyright (C) 2021 Members of the Simons Observatory collaboration.
# Please refer to the LICENSE file in the root of this repository.

from ref import agilent8722es_address
import waferscreen.inst_control.flux_sweep_config as fsc
from waferscreen.inst_control.flux_sweep import AbstractFluxSweep
from waferscreen.data_io.jobs_io import JobOrganizer


class JobDispatch:

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

    def do_jobs(self, rf_chain_letter, require_in_regulation=False):
        this_chain_flux_sweep = self.__getattribute__(F"{rf_chain_letter}_chain_flux_sweep")

        while True:
            job_basename = self.job_organizer.get_next_job_to_process(rf_chain_letter=rf_chain_letter)
            if job_basename is None:
                # refresh and see if new job files were written to the disk
                self.job_organizer = JobOrganizer()
            job_basename = self.job_organizer.get_next_job_to_process(rf_chain_letter=rf_chain_letter)
            if job_basename is None or not self.job_organizer.job_exists(job_basename):
                # Case: there are no jobs available for this RF chain
                break
            else:
                # Case: there is at least on job file
                # get the seed files and launch the flux sweeps
                job_type, seed_files = self.job_organizer.get_seed_files_from_job(job_basename=job_basename)
                if job_type == "single_res":
                    this_chain_flux_sweep.single_res_survey_from_job_file(seed_files,
                                                                          require_in_regulation=require_in_regulation)
                else:
                    raise TypeError(F"{job_type} is not a recognized job_type.")
                # The jobs based on any number of seed files are now completed, mark this job completed
                self.job_organizer.mark_job_completed(job_basename=job_basename)
        print(F"{self.__name__} has completed all available {rf_chain_letter}-chain jobs. ")


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
            job_dispatch.do_jobs(rf_chain_letter=rf_chain, require_in_regulation=True)
