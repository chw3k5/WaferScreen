from waferscreen.read.prodata import crawl_s21, read_pro_s21, ProS21
from waferscreen.res.finder import ResFinder
from waferscreen.plot.s21 import plot_21


class ResPro:
    def __init__(self, verbose=True):
        self.verbose = verbose
        self.s21 = {}
        self.tiny_sweeps = {}

    def proall(self):
        for path in crawl_s21():
            self.show_s21(path)
            self.s21[path] = ResFinder(file=path, remove_baseline_ripple=False, verbose=self.verbose, auto_process=True)

    def show_s21(self, path, save=True, show=True, show_bands=True):
        plot_21(file=path, save=save, show=show, show_bands=show_bands)


if __name__ == "__main__":
    res_pro = ResPro()
    res_pro.proall()
