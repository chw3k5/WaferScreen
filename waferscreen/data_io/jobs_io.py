# Copyright (C) 2021 Members of the Simons Observatory collaboration.
# Please refer to the LICENSE file in the root of this repository.

import os
import re
from collections import deque
from ref import working_dir


class JobOrganizer:
    working_dir = working_dir
    a_chain_job_deque = deque()
    b_chain_job_deque = deque()
    a_chain_new_job_int = 1
    b_chain_new_job_int = 1
    job_file_matching_expression = re.compile("._chain_jobs_....\.csv")

    def __init__(self, check_for_old_jobs=True):
        self.check_for_jobs()
        self.check_for_old_jobs = check_for_old_jobs
        if check_for_old_jobs:
            self.a_chain_job_deque = deque(sorted(self.a_chain_job_deque))
            self.b_chain_job_deque = deque(sorted(self.b_chain_job_deque))

    def get_seed_files_from_job(self, job_basename):
        job_full_path = os.path.join(self.working_dir, job_basename)
        with open(job_full_path, "r") as f:
            lines = f.readlines()
        job_type = lines[0].strip()
        seed_files = [filename.strip() for filename in lines[1:]]
        return job_type, seed_files

    @staticmethod
    def parse_job_file(job_basename):
        rf_chain_letter, job_int = job_basename.rstrip(".csv").split("_chain_jobs_")
        job_int = int(job_int)
        return rf_chain_letter, job_int

    def job_exists(self, job_basename):
        return os.path.isfile(os.path.join(self.working_dir, job_basename))

    def temp(self, rf_chain_letter):
        this_chain_job_deque = self.__getattribute__(F"{rf_chain_letter}_chain_job_deque")
        this_chain_new_job_int = self.__getattribute__(F"{rf_chain_letter}_chain_new_job_int")
        return this_chain_job_deque, this_chain_new_job_int

    def mark_job_completed(self, job_basename):
        rf_chain_letter, job_int = self.parse_job_file(job_basename)
        this_chain_job_deque = self.__getattribute__(F"{rf_chain_letter}_chain_job_deque")
        # keep trying to remove the file, make sure it is deleted before removing it from the available files
        os.remove(os.path.join(self.working_dir, job_basename))
        # delete the first element in the deque
        this_chain_job_deque.popleft()
        return

    def get_new_job_name(self, rf_chain_letter):
        this_chain_new_job_int = self.__getattribute__(F"{rf_chain_letter}_chain_new_job_int")
        job_basename = F"{rf_chain_letter}_chain_jobs_{'%04i' % this_chain_new_job_int}.csv"
        self.add_job_file_to_deque(job_basename=job_basename)
        self.__setattr__(F"{rf_chain_letter}_chain_new_job_int", this_chain_new_job_int + 1)
        return os.path.join(self.working_dir, job_basename)

    def get_next_job_to_process(self, rf_chain_letter):
        this_chain_job_deque = self.__getattribute__(F"{rf_chain_letter}_chain_job_deque")
        if len(this_chain_job_deque) > 0:
            # always send back the job at the left most entry in the deque, the first element in the deque
            return this_chain_job_deque[0]
        else:
            return None

    def add_job_file_to_deque(self, job_basename):
        rf_chain_letter, job_int = self.parse_job_file(job_basename=job_basename)
        this_chain_job_deque = self.__getattribute__(F"{rf_chain_letter}_chain_job_deque")
        this_chain_new_job_int = self.__getattribute__(F"{rf_chain_letter}_chain_new_job_int")
        # increment the next_job_int, this only happens here when the job processing was interrupted and restarted
        if job_int >= this_chain_new_job_int:
            self.__setattr__(F"{rf_chain_letter}_chain_new_job_int", job_int + 1)
        # add the file to the deque, if it is not there already from another instance of this class
        if job_basename not in this_chain_job_deque:
            this_chain_job_deque.append(job_basename)
        return

    def check_for_jobs(self):
        """
        Job files located in the working_dir and have the format F"{chain_letter}_chain_jobs_{'%04i' % job_int}.csv"

        This method can be called at anytime, but was made with the intention of only being called once at the
        start of processing to catch job files the were made on a previously interrupted thread.
        For adding and deleting one job file at a time use the methods:
        mark_job_completed
        get_next_job_name
        add_job_file_to_deque
        :return:
        """
        # get all the files in working_dir that match "._chain_jobs_....\.csv"
        all_job_files = []
        for file_or_folder in os.listdir(self.working_dir):
            full_path = os.path.join(self.working_dir, file_or_folder)
            if os.path.isfile(full_path) and re.match(self.job_file_matching_expression, file_or_folder):
                all_job_files.append(file_or_folder)
        # add files to the deque to be processed
        for job_file in all_job_files:
            self.add_job_file_to_deque(job_basename=job_file)
        return
