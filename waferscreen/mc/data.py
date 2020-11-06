import os
from ref import pro_data_dir, raw_data_dir
from waferscreen.read.s21_inductor import InductS21, MetaS21
from waferscreen.read.prodata import read_pro_s21, crawl_raw_s21, crawl_s21


class DataManager:
    def __init__(self, user_input_group_delay=None, verbose=True):
        self.user_input_group_delay = user_input_group_delay
        self.verbose = verbose
        self.raw_search_dirs = [os.path.join(raw_data_dir, dirname) for dirname in ["nist", "princeton"]]
        self.meta_data_paths = [os.path.join(raw_data_dir, dirname1, dirname2, filename)
                                for dirname1, dirname2, filename in [("princeton", "SMBK_wafer8", "meta_data.txt")]]
        self.raw_s21_meta = MetaS21()

    def from_scratch(self):
        self.raw_process_all()

    def raw_process_all(self):
        for raw_path in crawl_raw_s21(search_dirs=self.raw_search_dirs):
            self.raw_process(raw_path)

    def raw_get_meta_data(self):
        for meta_data_path in self.meta_data_paths:
            self.raw_s21_meta.meta_from_file(meta_data_path)

    def raw_process(self, path):
        if not self.raw_s21_meta.paths:
            self.raw_get_meta_data()
        inducts21 = InductS21(path, columns=None, verbose=self.verbose)
        inducts21.induct()
        inducts21.remove_group_delay(user_input_group_delay=self.user_input_group_delay)
        inducts21.add_meta_data(**self.raw_s21_meta.file_to_meta[path])
        inducts21.calc_meta_data()
        inducts21.write()
        inducts21.plot()


if __name__ == "__main__":
    dm = DataManager(user_input_group_delay=None)
    dm.from_scratch()