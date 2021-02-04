from waferscreen.data_io.s21_io import read_s21
from waferscreen.mc.data import get_all_lamb_files


class SingleLamb:
    def __init__(self, path, auto_load=True):
        self.path = path
        self.metadata = None
        self.res_fits = None
        self.lamb_fit = None
        if auto_load:
            self.read(lamb_path=self.path)

    def read(self, lamb_path):
        _s21, self.metadata, self.res_fits, lamb_fits = read_s21(path=lamb_path, return_res_params=True,
                                                                 return_lamb_params=True)
        self.lamb_fit = lamb_fits[0]


class LambExplore:
    def __init__(self, auto_load=True):
        self.lamb_params_data = None
        if auto_load:
            self.readall()

    def readall(self):
        self.lamb_params_data = {lamb_path: SingleLamb(path=lamb_path, auto_load=True)
                                 for lamb_path in get_all_lamb_files()}


if __name__ == "__main__":
    lamb_explore = LambExplore(auto_load=True)
