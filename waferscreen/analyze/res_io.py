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


primary_res_params = ["base_amplitude_abs", "a_phase_rad", "base_amplitude_slope", "tau_ns", "f0", "Qi", "Qc", "Zratio"]
res_params_header = ""
for param_type in primary_res_params:
    res_params_header += param_type + "," + param_type + "_error,"
res_params_header = res_params_header[:-1]


class ResParams(NamedTuple):
    base_amplitude_abs: float
    a_phase_rad: float
    base_amplitude_slope: float
    tau_ns: float
    f0: float
    Qi: float
    Qc: float
    Zratio: float
    base_amplitude_abs_error: Optional[float] = None
    a_phase_rad_error: Optional[float] = None
    base_amplitude_slope_error: Optional[float] = None
    tau_ns_error: Optional[float] = None
    f0_error: Optional[float] = None
    Qi_error: Optional[float] = None
    Qc_error: Optional[float] = None
    Zratio_error: Optional[float] = None

    def __str__(self):
        output_string = ""
        for attr in primary_res_params:
            error_value = str(self.__getattribute__(attr + "_error"))
            if error_value is None:
                error_str = ""
            else:
                error_str = str(error_value)
            output_string += str(self.__getattribute__(attr)) + "," + error_str + ","
        return output_string[:-1]
