import matplotlib.pyplot as plt
import numpy as np
from matplotlib import colors
from matplotlib.colors import LogNorm


Z = np.ones((4, 24))
Z[1, :] = 3
fig, ax = plt.subplots(1, 1)


c = ax.pcolor(Z, edgecolors='k', linewidths=4)
ax.set_title('4-day Wafer Screen')

fig.tight_layout()
plt.show()
