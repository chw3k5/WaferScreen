from waferscreen.scripts import sweep_to_find_resonances
from waferscreen.analyze.find_and_fit import ResFit


sweep_file = sweep_to_find_resonances(project='test', wafer="null", trace_number=0)
res_fit = ResFit(file=sweep_file, group_delay=31.839, verbose=True, freq_units="GHz", auto_process=True)
