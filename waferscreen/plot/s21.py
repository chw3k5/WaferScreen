from ref import s21_dir
import os
import numpy as np
from matplotlib import pyplot as plt

file = os.path.join(s21_dir, "so", "7_Band02_2020-09-10_run2.csv")

with open(file, 'r') as f:
    raw_lines = f.readlines()

header = raw_lines[0].rstrip().split(',')
data = [tuple(single_line.rstrip().split(',')) for single_line in raw_lines[1:]]
by_column_data = list(zip(*data))
data_dict = {header_value: np.array(column_values, dtype=float) for header_value, column_values in zip(header, by_column_data)}

data_dict["mag"] = 20.0 * np.log10(np.sqrt(np.square(data_dict['real']) + np.square(data_dict['imag'])))
data_dict['phase'] = np.arctan2(data_dict['imag'], data_dict['real'])

plt.figure(figsize=(20, 8))
plt.plot(data_dict["freq"], data_dict['mag'], color='firebrick')
plt.show()
