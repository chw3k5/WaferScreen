import matplotlib.pyplot as plt
import matplotlib.transforms as mtransforms
from ref import band_params, smurf_keepout_zones_ghz


colors = ['BlueViolet', 'Brown', 'CadetBlue', 'Coral', 'Crimson',
          'DarkGoldenRod', 'DarkGreen', 'DarkMagenta', 'DarkOrange',
          'DarkOrchid', 'DarkRed', 'DarkSalmon', 'DodgerBlue', 'FireBrick']
hatches = ['/', '*', '\\', 'x', 'o']

# plot initialization
fig, ax = plt.subplots(figsize=(12, 8))
trans = mtransforms.blended_transform_factory(ax.transData, ax.transAxes)
ax.tick_params(axis='y',  # changes apply to the x-axis
               which='both',  # both major and minor ticks are affected
               left=False,  # ticks along the bottom edge are off
               right=False,  # ticks along the top edge are off
               labelleft=False)

# SO band definitions
for band_int in range(14):
    band_name = F"Band{'%02i' % band_int}"
    band_dict = band_params[band_name]
    band_min_ghz = band_dict["min_GHz"]
    band_max_ghz = band_dict["max_GHz"]
    color = colors[band_int]
    ax.fill_between((band_dict['min_GHz'], band_dict['max_GHz']), 0, 1,
                    facecolor=color, alpha=0.5, transform=trans)
    band_size_mhz = 1000.0 * (band_max_ghz - band_min_ghz)
    plt.text(x=band_dict['min_GHz'], y=0.9 - (band_int * 0.8 / 14.0),
             s=F"{band_name}\n size={'%5.1f' % band_size_mhz}MHz",
             color="white", fontsize=6,
             bbox={"facecolor": color, "alpha": 0.5}, transform=trans)

# smurf keep out zones
for keepout_index, keepout_zone in list(enumerate(smurf_keepout_zones_ghz)):
    keepout_min, keepout_max = keepout_zone
    hatch = hatches[keepout_index]
    ax.fill_between((keepout_min, keepout_max), 0, 1,
                    facecolor='black', alpha=0.5, transform=trans,
                    hatch=hatch)
    plt.text(x=keepout_min, y=0.1, s="SMURF Keepout Zone", color="white", fontsize=6,
             bbox={"facecolor": 'black', "alpha": 0.5}, transform=trans)

ax.set_xlabel("Frequency (GHz)")
plt.show(block=True)
