import os
from ref import output_dirs
from waferscreen.read.s21_inductor import InductS21, read_s21
from waferscreen.read.s21_metadata import S21MetadataPrinceton, S21MetadataNist
from waferscreen.read.prodata import crawl_s21


def get_subdirs(rootdir, matching_str):
    folder_list = []
    for root, subdirs, files in os.walk(rootdir):
        for subdir in subdirs:
            if subdir == matching_str:
                folder_list.append(os.path.join(root, subdir))
    return folder_list


class DataManager:
    def __init__(self, user_input_group_delay=None, verbose=True):
        self.user_input_group_delay = user_input_group_delay
        self.verbose = verbose
        self.raw_search_dirs = output_dirs
        self.raw_scan_files = None

    def from_scratch(self):
        self.raw_process_all()

    def raw_process_all(self):
        self.raw_scan_files = []
        for rootdir in output_dirs:
            raw_dirs = get_subdirs(rootdir=rootdir, matching_str='raw')
            for raw_dir in raw_dirs:
                self.raw_scan_files.extend([os.path.join(raw_dir, path) for path in os.listdir(raw_dir)
                                            if path[:4] == 'scan'])
        for raw_scan_path in self.raw_scan_files:
            self.raw_process(path=raw_scan_path)

    def raw_process(self, path):
        inducts21 = InductS21(path, verbose=self.verbose)
        inducts21.induct()
        inducts21.remove_group_delay(user_input_group_delay=self.user_input_group_delay)
        inducts21.write()
        inducts21.plot()


class DataProcessing(DataManager):
    pass


if __name__ == "__main__":
    dm = DataManager(user_input_group_delay=None)
    dm.raw_process_all()
