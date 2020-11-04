import numpy as np
from operator import itemgetter
import bisect
from ref import band_params

band_edges = []
band_centers = []
center_freq_to_band_num = {}
for band in band_params.keys():
    band_edges.append((band_params[band]["min_GHz"], F"Start {band}"))
    band_edges.append((band_params[band]["max_GHz"], F"End {band}"))
    band_centers.append((band_params[band]["center_GHz"], F"{band}  Center at {'%1.3f' % band_params[band]['center_GHz']} GHz"))
    center_freq_to_band_num[band_params[band]["center_GHz"]] = band_params[band]["band_num"]
ordered_band_edges = sorted(band_edges, key=itemgetter(0))
ordered_band_list = [band_tuple[0] for band_tuple in ordered_band_edges]
ordered_band_centers = sorted(band_centers, key=itemgetter(0))


def find_band_edges(min_freq, max_freq, extened=False):
    start_index = bisect.bisect(ordered_band_list, min_freq)
    end_index = bisect.bisect_left(ordered_band_list, max_freq)
    if extened:
        if start_index != 0:
            start_index -= 1
        if end_index != len(ordered_band_list):
            end_index += 1
    return ordered_band_edges[start_index: end_index]


def band_center_to_band_number(center_freq_ghz):
    closest_center_freq, _format_str = find_center_band(center_GHz=center_freq_ghz)
    return center_freq_to_band_num[closest_center_freq]


def find_center_band(center_GHz):
    min_diff = float('inf')
    nearest_band_center_index = -1
    count = 0
    for freq, _ in ordered_band_centers:
        diff = np.abs(center_GHz - freq)
        if diff < min_diff:
            min_diff = diff
            nearest_band_center_index = count
        count += 1
    return ordered_band_centers[nearest_band_center_index]


def calc_band_edges(min_GHz, max_GHz, center_GHz,
                    lower_extra_span_fraction=0.1, upper_extra_span_fraction=0.1, return_span_center=False):
    lower_edge = center_GHz - ((center_GHz - min_GHz) * (1.0 + lower_extra_span_fraction))
    upper_edge = center_GHz + ((max_GHz - center_GHz) * (1.0 + upper_extra_span_fraction))
    if return_span_center:
        return (upper_edge - lower_edge), ((upper_edge + lower_edge) * 0.5)
    else:
        return lower_edge, upper_edge
