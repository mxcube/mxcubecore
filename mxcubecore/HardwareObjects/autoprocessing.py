import logging
import os
import subprocess


def grouped_processing(processEvent, params):
    endOfLineToExecute = ""

    for param_dict in params:
        dataCollectionId = param_dict.get("collect_id")
        residues = param_dict.get("residues", 0)
        anomalous = param_dict.get("anomalous", False)
        spacegroup = param_dict.get("spacegroup")

        if spacegroup:
            sg_opt = " -sg {0}".format(spacegroup)
        else:
            sg_opt = ""

        unit_cell_constants = param_dict.get("cell")
        if unit_cell_constants:
            cell_opt = ' -cell "{0}"'.format(unit_cell_constants)
        else:
            cell_opt = ""

        endOfLineToExecute += " -mode %s -collect %d:%s" % (
            processEvent,
            dataCollectionId,
            param_dict["xds_dir"],
        )
        endOfLineToExecute += (
            " -residues "
            + str(residues)
            + " -anomalous "
            + str(anomalous)
            + sg_opt
            + cell_opt
        )
        # + (param_dict["inverse_beam"] and ' -inverse' or '')
    return endOfLineToExecute


def start(programs, processEvent, paramsDict):
    for program in programs["program"]:
        try:
            allowed_events = program.get_property("event").split(" ")
            if processEvent in allowed_events:
                executable = program.get_property("executable")

                if os.path.isfile(executable):
                    if processEvent == "end_multicollect":
                        endOfLineToExecute = grouped_processing(
                            "end_multicollect", paramsDict
                        )
                    elif os.path.isdir(paramsDict["xds_dir"]):
                        dataCollectionId = paramsDict.get("datacollect_id")
                        residues = paramsDict.get("residues", 0)
                        anomalous = paramsDict.get("anomalous", False)
                        spacegroup = paramsDict.get("spacegroup")
                        if spacegroup:
                            sg_opt = " -sg {0}".format(spacegroup)
                        else:
                            sg_opt = ""

                        unit_cell_constants = paramsDict.get("cell")
                        if unit_cell_constants:
                            cell_opt = ' -cell "{0}"'.format(unit_cell_constants)
                        else:
                            cell_opt = ""

                        endOfLineToExecute = (
                            " -path "
                            + paramsDict["xds_dir"]
                            + " -mode "
                            + processEvent
                            + " -datacollectionID "
                            + str(dataCollectionId)
                            + " -residues "
                            + str(residues)
                            + " -anomalous "
                            + str(anomalous)
                            + sg_opt
                            + cell_opt
                        )  # +\
                        # (paramsDict["inverse_beam"] and ' -inverse' or '')
                    lineToExecute = (
                        executable + endOfLineToExecute + " 2>&1 > /dev/null &"
                    )
                    logging.info(
                        "Process event %s, executing %s"
                        % (processEvent, str(lineToExecute))
                    )

                    subprocess.Popen(
                        str(lineToExecute),
                        shell=True,
                        stdin=None,
                        stdout=None,
                        stderr=None,
                        close_fds=True,
                    )
                else:
                    logging.getLogger().error(
                        "No program to execute found (%s)", executable
                    )
        except KeyError:
            logging.exception("autoprocessing: an error occurred")


def startInducedRadDam(datacollect_params, old={"xds_dir": None}):
    if not datacollect_params["xds_dir"] == old["xds_dir"]:
        old["xds_dir"] = datacollect_params["xds_dir"]
        eda_dirs = sorted(
            filter(
                os.path.isdir,
                [
                    os.path.join(datacollect_params["EDNA_files_dir"], x)
                    for x in os.listdir(datacollect_params["EDNA_files_dir"])
                    if x.startswith("EDA")
                ],
            )
        )
        EDApplication = eda_dirs[-1]
        os.system(
            "export TCL_LIBRARY=/usr/share/tcl8.4;/opt/pxsoft/bin/InducedRadDam.py -i -e %s -p %s &"
            % (EDApplication, datacollect_params["xds_dir"])
        )
    return True
