from datetime import datetime

from mxcubecore.utils.conversion import string_types


class ISPyBValueFactory:
    """
    Constructs ws objects from "old style" mxCuBE dictonaries.
    """

    @staticmethod
    def detector_from_blc(bl_config, mx_collect_dict):
        try:
            detector_manufacturer = bl_config.detector_manufacturer

            if isinstance(detector_manufacturer, string_types):
                detector_manufacturer = detector_manufacturer.upper()
        except Exception:
            detector_manufacturer = ""

        try:
            detector_type = bl_config.detector_type
        except Exception:
            detector_type = ""

        try:
            detector_model = bl_config.detector_model
        except Exception:
            detector_model = ""

        try:
            detector_mode = det_mode = bl_config.detector_binning_mode
        except (KeyError, IndexError, ValueError, TypeError):
            detector_mode = ""

        return (detector_type, detector_manufacturer, detector_model, detector_mode)

    @staticmethod
    def from_bl_config(ws_client, bl_config):
        """
        Creates a beamLineSetup3VO from the bl_config dictionary.
        :rtype: beamLineSetup3VO
        """
        beamline_setup = None
        try:
            beamline_setup = ws_client.factory.create("ns0:beamLineSetup3VO")
        except Exception:
            raise
        try:
            synchrotron_name = bl_config.synchrotron_name
            beamline_setup.synchrotronName = synchrotron_name
        except (IndexError, AttributeError):
            beamline_setup.synchrotronName = "ESRF"

        if bl_config.undulators:
            i = 1
            for und in bl_config.undulators:
                beamline_setup.__setattr__("undulatorType%d" % i, und.type)
                i += 1

        try:
            beamline_setup.monochromatorType = bl_config.monochromator_type

            beamline_setup.focusingOptic = bl_config.focusing_optic

            beamline_setup.beamDivergenceVertical = bl_config.beam_divergence_vertical

            beamline_setup.beamDivergenceHorizontal = (
                bl_config.beam_divergence_horizontal
            )

            beamline_setup.polarisation = bl_config.polarisation

            beamline_setup.minExposureTimePerImage = bl_config.minimum_exposure_time

            beamline_setup.goniostatMaxOscillationSpeed = bl_config.maximum_phi_speed

            beamline_setup.goniostatMinOscillationWidth = (
                bl_config.minimum_phi_oscillation
            )

        except Exception:
            pass

        beamline_setup.setupDate = datetime.now()

        return beamline_setup

    @staticmethod
    def dcg_from_dc_params(ws_client, mx_collect_dict):
        """
        Creates a dataCollectionGroupWS3VO object from a mx_collect_dict.
        """

        group = None

        try:
            group = ws_client.factory.create("ns0:dataCollectionGroupWS3VO")
        except Exception:
            raise
        else:
            try:
                group.actualContainerBarcode = mx_collect_dict["actualContainerBarcode"]
            except Exception:
                pass

            try:
                group.actualContainerSlotInSC = mx_collect_dict[
                    "actualContainerSlotInSC"
                ]
            except KeyError:
                pass

            try:
                group.actualSampleBarcode = mx_collect_dict["actualSampleBarcode"]
            except KeyError:
                pass

            try:
                group.actualSampleSlotInContainer = mx_collect_dict[
                    "actualSampleSlotInContainer"
                ]
            except KeyError:
                pass

            try:
                group.blSampleId = mx_collect_dict["sample_reference"]["blSampleId"]
            except KeyError:
                pass

            try:
                group.comments = mx_collect_dict["comments"]
            except KeyError:
                pass

            try:
                group.workflowId = mx_collect_dict["workflow_id"]
            except KeyError:
                pass

            group.endTime = datetime.now()

            try:
                try:
                    helical_used = mx_collect_dict["helical"]
                except Exception:
                    helical_used = False
                else:
                    if helical_used:
                        mx_collect_dict["experiment_type"] = "Helical"
                        mx_collect_dict["comment"] = "Helical"

                try:
                    directory = mx_collect_dict["fileinfo"]["directory"]
                except Exception:
                    directory = ""
                experiment_type = mx_collect_dict["experiment_type"]
                if experiment_type.lower() == "mesh":
                    experiment_type = "Mesh"
                group.experimentType = experiment_type
            except KeyError:
                pass

            try:
                group.sessionId = mx_collect_dict["sessionId"]
            except Exception:
                pass

            try:
                start_time = mx_collect_dict["collection_start_time"]
                start_time = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
                group.startTime = start_time
            except Exception:
                pass

            try:
                group.dataCollectionGroupId = mx_collect_dict["group_id"]
            except Exception:
                pass

            return group

    @staticmethod
    def from_data_collect_parameters(ws_client, mx_collect_dict):
        """
        Ceates a dataCollectionWS3VO from mx_collect_dict.
        :rtype: dataCollectionWS3VO
        """
        if len(mx_collect_dict["oscillation_sequence"]) != 1:
            raise ISPyBArgumentError(
                "ISPyBServer: number of oscillations"
                + " must be 1 (until further notice...)"
            )
        data_collection = None

        try:
            data_collection = ws_client.factory.create("ns0:dataCollectionWS3VO")
        except Exception:
            raise

        osc_seq = mx_collect_dict["oscillation_sequence"][0]

        try:
            data_collection.runStatus = mx_collect_dict["status"]
            data_collection.axisStart = osc_seq["start"]

            data_collection.axisEnd = float(osc_seq["start"]) + (
                float(osc_seq["range"]) - float(osc_seq["overlap"])
            ) * float(osc_seq["number_of_images"])

            data_collection.axisRange = osc_seq["range"]
            data_collection.overlap = osc_seq["overlap"]
            data_collection.numberOfImages = osc_seq["number_of_images"]
            data_collection.startImageNumber = osc_seq["start_image_number"]
            data_collection.numberOfPasses = osc_seq["number_of_passes"]
            data_collection.exposureTime = osc_seq["exposure_time"]
            data_collection.imageDirectory = mx_collect_dict["fileinfo"]["directory"]

            if "kappaStart" in osc_seq:
                if osc_seq["kappaStart"] != 0 and osc_seq["kappaStart"] != -9999:
                    data_collection.rotationAxis = "Omega"
                    data_collection.omegaStart = osc_seq["start"]
                else:
                    data_collection.rotationAxis = "Phi"
            else:
                data_collection.rotationAxis = "Phi"
                osc_seq["kappaStart"] = -9999
                osc_seq["phiStart"] = -9999

            data_collection.kappaStart = osc_seq["kappaStart"]
            data_collection.phiStart = osc_seq["phiStart"]

        except KeyError as diag:
            err_msg = "ISPyBClient: error storing a data collection (%s)" % str(diag)
            raise ISPyBArgumentError(err_msg)

        data_collection.detector2theta = 0

        try:
            data_collection.dataCollectionId = int(mx_collect_dict["collection_id"])
        except (TypeError, ValueError, KeyError):
            pass

        try:
            data_collection.wavelength = mx_collect_dict["wavelength"]
        except KeyError as diag:
            pass

        res_at_edge = None
        try:
            try:
                res_at_edge = float(mx_collect_dict["resolution"])
            except Exception:
                res_at_edge = float(mx_collect_dict["resolution"]["lower"])
        except KeyError:
            try:
                res_at_edge = float(mx_collect_dict["resolution"]["upper"])
            except Exception:
                pass
        if res_at_edge is not None:
            data_collection.resolution = res_at_edge

        try:
            data_collection.resolutionAtCorner = mx_collect_dict["resolutionAtCorner"]
        except KeyError:
            pass

        try:
            data_collection.detectorDistance = mx_collect_dict["detectorDistance"]
        except KeyError as diag:
            pass

        try:
            data_collection.xbeam = mx_collect_dict["xBeam"]
            data_collection.ybeam = mx_collect_dict["yBeam"]
        except KeyError as diag:
            pass

        try:
            data_collection.beamSizeAtSampleX = mx_collect_dict["beamSizeAtSampleX"]
            data_collection.beamSizeAtSampleY = mx_collect_dict["beamSizeAtSampleY"]
        except KeyError:
            pass

        try:
            data_collection.beamShape = mx_collect_dict["beamShape"]
        except KeyError:
            pass

        try:
            data_collection.slitGapHorizontal = mx_collect_dict["slitGapHorizontal"]
            data_collection.slitGapVertical = mx_collect_dict["slitGapVertical"]
        except KeyError:
            pass

        try:
            data_collection.imagePrefix = mx_collect_dict["fileinfo"]["prefix"]
        except KeyError as diag:
            pass

        try:
            data_collection.imageSuffix = mx_collect_dict["fileinfo"]["suffix"]
        except KeyError as diag:
            pass
        try:
            data_collection.fileTemplate = mx_collect_dict["fileinfo"]["template"]
        except KeyError as diag:
            pass

        try:
            data_collection.dataCollectionNumber = mx_collect_dict["fileinfo"][
                "run_number"
            ]
        except KeyError as diag:
            pass

        try:
            data_collection.synchrotronMode = mx_collect_dict["synchrotronMode"]
            data_collection.flux = mx_collect_dict["flux"]
        except KeyError as diag:
            pass

        try:
            data_collection.flux_end = mx_collect_dict["flux_end"]
        except KeyError as diag:
            pass

        try:
            data_collection.transmission = mx_collect_dict["transmission"]
        except KeyError:
            pass

        try:
            data_collection.undulatorGap1 = mx_collect_dict["undulatorGap1"]
            data_collection.undulatorGap2 = mx_collect_dict["undulatorGap2"]
            data_collection.undulatorGap3 = mx_collect_dict["undulatorGap3"]
        except KeyError:
            pass

        try:
            data_collection.xtalSnapshotFullPath1 = mx_collect_dict[
                "xtalSnapshotFullPath1"
            ]
        except KeyError:
            pass

        try:
            data_collection.xtalSnapshotFullPath2 = mx_collect_dict[
                "xtalSnapshotFullPath2"
            ]
        except KeyError:
            pass

        try:
            data_collection.xtalSnapshotFullPath3 = mx_collect_dict[
                "xtalSnapshotFullPath3"
            ]
        except KeyError:
            pass

        try:
            data_collection.xtalSnapshotFullPath4 = mx_collect_dict[
                "xtalSnapshotFullPath4"
            ]
        except KeyError:
            pass

        try:
            data_collection.centeringMethod = mx_collect_dict["centeringMethod"]
        except KeyError:
            pass

        try:
            data_collection.actualCenteringPosition = mx_collect_dict[
                "actualCenteringPosition"
            ]
        except KeyError:
            pass

        try:
            data_collection.dataCollectionGroupId = mx_collect_dict["group_id"]
        except KeyError:
            pass

        try:
            data_collection.detectorId = mx_collect_dict["detector_id"]
        except KeyError:
            pass

        try:
            data_collection.strategySubWedgeOrigId = mx_collect_dict[
                "screening_sub_wedge_id"
            ]
        except Exception:
            pass

        try:
            start_time = mx_collect_dict["collection_start_time"]
            start_time = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
            data_collection.startTime = start_time
        except Exception:
            pass

        data_collection.endTime = datetime.now()

        return data_collection

    def workflow_from_workflow_info(self, workflow_info_dict):
        """
        Ceates workflow3VO from worflow_info_dict.
        :rtype: workflow3VO
        """
        ws_client = None
        workflow_vo = None

        try:
            ws_client = Client(_WS_COLLECTION_URL, cache=None)
            workflow_vo = ws_client.factory.create("workflow3VO")
        except Exception:
            raise

        try:
            if workflow_info_dict.get("workflow_id"):
                workflow_vo.workflowId = workflow_info_dict.get("workflow_id")
            workflow_vo.workflowType = workflow_info_dict.get(
                "workflow_type", "MeshScan"
            )
            workflow_vo.comments = workflow_info_dict.get("comments", "")
            workflow_vo.logFilePath = workflow_info_dict.get("log_file_path", "")
            workflow_vo.resultFilePath = workflow_info_dict.get("result_file_path", "")
            workflow_vo.status = workflow_info_dict.get("status", "")
            workflow_vo.workflowTitle = workflow_info_dict.get("title", "")
        except KeyError as diag:
            err_msg = "ISPyBClient: error storing a workflow (%s)" % str(diag)
            raise ISPyBArgumentError(err_msg)

        return workflow_vo

    def workflow_mesh_from_workflow_info(self, workflow_info_dict):
        """
        Ceates workflowMesh3VO from worflow_info_dict.
        :rtype: workflowMesh3VO
        """
        ws_client = None
        workflow_mesh_vo = None

        try:
            ws_client = Client(_WS_COLLECTION_URL, cache=None)
            workflow_mesh_vo = ws_client.factory.create("workflowMeshWS3VO")
        except Exception:
            raise

        try:
            if workflow_info_dict.get("workflow_mesh_id"):
                workflow_mesh_vo.workflowMeshId = workflow_info_dict.get(
                    "workflow_mesh_id"
                )
            workflow_mesh_vo.cartographyPath = workflow_info_dict.get(
                "cartography_path", ""
            )
            workflow_mesh_vo.bestImageId = workflow_info_dict.get("best_image_id", "")
            workflow_mesh_vo.bestPositionId = workflow_info_dict.get("best_position_id")
            workflow_mesh_vo.value1 = workflow_info_dict.get("value_1")
            workflow_mesh_vo.value2 = workflow_info_dict.get("value_2")
            workflow_mesh_vo.value3 = workflow_info_dict.get("value_3")
            workflow_mesh_vo.value4 = workflow_info_dict.get("value_4")
        except KeyError as diag:
            err_msg = "ISPyBClient: error storing a workflow mesh (%s)" % str(diag)
            raise ISPyBArgumentError(err_msg)

        return workflow_mesh_vo

    def workflow_step_from_workflow_info(self, workflow_info_dict):
        """
        Ceates workflow3VO from worflow_info_dict.
        :rtype: workflow3VO
        """
        ws_client = None
        workflow_vo = None

        try:
            ws_client = Client(_WS_COLLECTION_URL, cache=None)
            workflow_step_vo = ws_client.factory.create("workflowStep3VO")
        except Exception:
            raise

        try:
            workflow_step_vo.workflowId = workflow_info_dict.get("workflow_id")
            workflow_step_vo["type"] = workflow_info_dict.get(
                "workflow_type", "MeshScan"
            )
            workflow_step_vo.status = workflow_info_dict.get("status", "")
            workflow_step_vo.folderPath = workflow_info_dict.get("result_file_path", "")
            workflow_step_vo.htmlResultFilePath = os.path.join(
                workflow_step_vo.folderPath, "index.html"
            )
            workflow_step_vo.resultFilePath = os.path.join(
                workflow_step_vo.folderPath, "index.html"
            )
            workflow_step_vo.comments = workflow_info_dict.get("comments", "")
            workflow_step_vo.crystalSizeX = workflow_info_dict.get("crystal_size_x")
            workflow_step_vo.crystalSizeY = workflow_info_dict.get("crystal_size_y")
            workflow_step_vo.crystalSizeZ = workflow_info_dict.get("crystal_size_z")
            workflow_step_vo.maxDozorScore = workflow_info_dict.get("max_dozor_score")
        except KeyError as diag:
            err_msg = "ISPyBClient: error storing a workflow (%s)" % str(diag)
            raise ISPyBArgumentError(err_msg)

        return workflow_step_vo

    def grid_info_from_workflow_info(self, workflow_info_dict):
        """
        Ceates grid3VO from worflow_info_dict.
        :rtype: grid3VO
        """
        ws_client = None
        grid_info_vo = None

        try:
            ws_client = Client(_WS_COLLECTION_URL, cache=None)
            grid_info_vo = ws_client.factory.create("gridInfoWS3VO")
        except Exception:
            raise

        try:
            if workflow_info_dict.get("grid_info_id"):
                grid_info_vo.gridInfoId = workflow_info_dict.get("grid_info_id")
            grid_info_vo.dx_mm = workflow_info_dict.get("dx_mm")
            grid_info_vo.dy_mm = workflow_info_dict.get("dy_mm")
            grid_info_vo.meshAngle = workflow_info_dict.get("mesh_angle")
            grid_info_vo.steps_x = workflow_info_dict.get("steps_x")
            grid_info_vo.steps_y = workflow_info_dict.get("steps_y")
            grid_info_vo.xOffset = workflow_info_dict.get("xOffset")
            grid_info_vo.yOffset = workflow_info_dict.get("yOffset")
        except KeyError as diag:
            err_msg = "ISPyBClient: error storing a grid info (%s)" % str(diag)
            raise ISPyBArgumentError(err_msg)

        return grid_info_vo


class ISPyBArgumentError(Exception):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return repr(self.value)


def test_hwo(hwo):
    info = hwo.login("20100023", "tisabet")
    print("Logging through ISPyB. Proposals for 201000223 are:", str(info))
