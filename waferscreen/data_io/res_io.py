# Copyright (C) 2021 Members of the Simons Observatory collaboration.
# Please refer to the LICENSE file in the root of this repository.

from typing import NamedTuple, Optional


def read_res_params(path):
    # open resonant frequencies file
    with open(path, 'r') as f:
        lines = f.readlines()
    header = lines[0].strip().split(",")
    res_params = []
    for line in lines[1:]:
        datavec = line.split(",")
        res_params.append(ResParams(**{column_name: float(value) for column_name, value in zip(header, datavec)}))
    return res_params


primary_res_params = ["fcenter_ghz", "q_i", "q_c", "base_amplitude_abs", "a_phase_rad", "base_amplitude_slope", "tau_ns", "impedance_ratio"]
res_params_header = "res_number,"
for param_type in primary_res_params:
    res_params_header += param_type + "," + param_type + "_error,"
res_params_header += "flux_ramp_current_ua,parent_file"
res_params_head_list = res_params_header.split(",")
res_params_header = "# Resfits:" + res_params_header


class ResParams(NamedTuple):
    base_amplitude_abs: float
    a_phase_rad: float
    base_amplitude_slope: float
    tau_ns: float
    fcenter_ghz: float
    q_i: float
    q_c: float
    impedance_ratio: float
    base_amplitude_abs_error: Optional[float] = None
    a_phase_rad_error: Optional[float] = None
    base_amplitude_slope_error: Optional[float] = None
    tau_ns_error: Optional[float] = None
    fcenter_ghz_error: Optional[float] = None
    q_i_error: Optional[float] = None
    q_c_error: Optional[float] = None
    impedance_ratio_error: Optional[float] = None
    parent_file: Optional[str] = None
    res_number: Optional[int] = None
    flux_ramp_current_ua: Optional[float] = None

    def __str__(self):
        value_list = [self.__getattribute__(item_name) for item_name in res_params_head_list]
        output_string = None
        for value in value_list:
            if value is None:
                value_str = ""
            else:
                value_str = str(value)
            if output_string is None:
                output_string = F"{value_str}"
            else:
                output_string += F",{value_str}"
        return output_string
