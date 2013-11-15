import os
import sys
import logging

def start(programs,processEvent,paramsDict):
        dataCollectionId = paramsDict.get('datacollect_id')
        residues = paramsDict.get('residues', 0)
        anomalous = paramsDict.get('anomalous', False)
        spacegroup = paramsDict.get('spacegroup')
        if spacegroup: 
            sg_opt = ' -sg {0}'.format(spacegroup)
        else:
            sg_opt = ''
        unit_cell_constants = paramsDict.get('cell')
        if unit_cell_constants:
            cell_opt = ' -cell "{0}"'.format(unit_cell_constants)
        else:
            cell_opt = ''

        #import pdb;pdb.set_trace()
        for program in programs["program"]:
             try:
                allowed_events = program.getProperty("event").split(" ")
                if processEvent in allowed_events:
                        executable = program.getProperty('executable')
                        opts = "-path"
                        if os.path.isfile(executable):
                            if processEvent == "end_multicollect":
                               # in this case paramsDict is a list of tuples
                               endOfLineToExecute = ' -mode ' + processEvent + " ".join([' -collect %d:%s -residues %s -anomalous %s %s' % (id,dir,anomalous,residues,inverse_beam and "-inverse" or "") for id,dir,_,anomalous,residues,inverse_beam,_ in paramsDict["collections_params"]])
                            elif os.path.isdir(paramsDict["xds_dir"]):
                                in_queue = paramsDict.get("in_multicollect")
                                
                                endOfLineToExecute = ' ' + paramsDict["xds_dir"] +\
                                                     ' -mode ' + processEvent +\
                                                     ' -datacollectionID ' + str(dataCollectionId) +\
                                                     ' -residues ' + str(residues) +\
                                                     ' -anomalous ' + str(anomalous) +\
                                                     ' -in_queue ' + str(in_queue) +\
                                                     sg_opt + cell_opt +\
                                                     (paramsDict["inverse_beam"] and ' -inverse' or '')

                            if opts is not None:
                                lineToExecute = executable + ' ' + opts + endOfLineToExecute
                            else:
                                lineToExecute = executable + endOfLineToExecute

                            logging.info("Process event %s, executing %s" % (processEvent,str(lineToExecute)))

                            # os.system is preferred to subprocess because we want to detach
                            # the started program from the parent process group
                            os.system(str(lineToExecute)+" &")
                        else:
                            logging.getLogger().error("No program to execute found (%s)",executable)
             except:
                    logging.exception("autoprocessing: an error occurred")


def startInducedRadDam(datacollect_params, old={"xds_dir":None}):
  if not datacollect_params["xds_dir"] == old["xds_dir"]:
      old["xds_dir"]=datacollect_params["xds_dir"]
      eda_dirs=filter(os.path.isdir, [os.path.join(datacollect_params['EDNA_files_dir'], x) for x in os.listdir(datacollect_params['EDNA_files_dir']) if x.startswith("EDA")])
      eda_dirs.sort()
      EDApplication = eda_dirs[-1]
      os.system("export TCL_LIBRARY=/usr/share/tcl8.4;/opt/pxsoft/bin/InducedRadDam.py -i -e %s -p %s &" % (EDApplication, datacollect_params["xds_dir"]))
  return True
