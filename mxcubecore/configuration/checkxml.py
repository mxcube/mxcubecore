import os
import xmltodict
import argparse
import pprint
import pydantic

from colorama import Fore, Back, Style
from mxcubecore.model import configmodel


def check_xml(rpath="."):
    for path in os.listdir(rpath):
        fpath = os.path.join(os.path.abspath(rpath), path)
        if os.path.isfile(fpath) and fpath.endswith(".xml"):

            with open(fpath, "r+") as f:
                data = xmltodict.parse(f.read())

                if list(data.keys())[0] in ["equipment", "device"]:
                    print(f"{fpath}")
                    pprint.pprint(data)
                    print(
                        f"{Fore.RED}WARNING: equipment and device are depricated, use object instead"
                    )
                    print(Style.RESET_ALL)

                _data_to_validate = data[list(data.keys())[0]]


                try:
                    config_model_class_name = _data_to_validate["@class"].strip("Mockup")
                    config_model = getattr(configmodel, f"{config_model_class_name}ConfigModel", None)
                except KeyError:
                    print(f"{Fore.RED}WARNING in: {fpath}")
                    print(f"{Fore.RED}WARNING: no class")
                else:
                    if config_model:
                        try:
                            config_model(**_data_to_validate)
                        except pydantic.ValidationError as ex:
                            print(f"{Fore.RED}WARNING in: {fpath}")
                            print(f"{str(ex)}")
                            print(Style.RESET_ALL)


def parse_args():
    XML_DIR = os.path.join(os.path.dirname(__file__))

    opt_parser = argparse.ArgumentParser(
        description="Tool for checking mxcubecore xml configuration files"
    )

    opt_parser.add_argument(
        "hwr_directory",
        metavar="hwr_directory",
        help="Hardware Repository XML files path",
        nargs=1,
        default=XML_DIR,
    )

    return opt_parser.parse_args()


if __name__ == "__main__":
    cmdline_options = parse_args()
    check_xml(cmdline_options.hwr_directory[0])
