import os
from typing import NamedTuple, Optional
import ref

lamb_params_prime_types = ["i0fit", "mfit", "f2fit", "pfit", "lambfit"]
lambda_header_list = ["res_num"]
for prime_type in lamb_params_prime_types:
    lambda_header_list.append(prime_type)
    lambda_header_list.append(F"{prime_type}_err")
lambda_header_list.append("parent_dir")
lambda_header = F"# Lambda:{lambda_header_list[0]}"
for header_item in lambda_header_list[1:]:
    lambda_header += F",{header_item}"


class LambdaParams(NamedTuple):
    i0fit: float
    mfit: float
    f2fit: float
    pfit: float
    lambfit: float
    res_num: int
    parent_dir: str
    i0fit_err: Optional[float] = None
    mfit_err: Optional[float] = None
    f2fit_err: Optional[float] = None
    pfit_err: Optional[float] = None
    lambfit_err: Optional[float] = None

    def __str__(self):
        output_string = ""
        for header_item in lambda_header_list:
            output_string += str(self.__getattribute__(header_item)) + ","
        return output_string[:-1]


def remove_processing_tags(dir_str):
    for pro_tag in ref.s21_processing_types:
        remove_str = F"_{pro_tag}"
        dir_str = dir_str.replace(remove_str, "")
    return dir_str


def prep_lamb_dirs(pro_data_dir, report_parent_dir_str):
    report_dir = os.path.join(pro_data_dir, report_parent_dir_str, 'report')
    if not os.path.isdir(report_dir):
        os.mkdir(report_dir)
    lamb_outputs_dir = os.path.join(report_dir, "lambda")
    if not os.path.isdir(lamb_outputs_dir):
        os.mkdir(lamb_outputs_dir)
    lamb_plots_dir = os.path.join(lamb_outputs_dir, "lambda_plots")
    if not os.path.isdir(lamb_plots_dir):
        os.mkdir(lamb_plots_dir)
    return report_dir, lamb_outputs_dir, lamb_plots_dir
