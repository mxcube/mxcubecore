from __future__ import print_function

import itertools
import logging
import sys
import time
from datetime import datetime
from typing import (
    Dict,
    List,
)
from urllib.error import URLError

from suds import WebFault
from suds.client import Client
from suds.sudsobject import asdict

from mxcubecore.HardwareObjects.abstract.ISPyBValueFactory import ISPyBValueFactory
from mxcubecore.model.lims_session import (
    LimsSessionManager,
    Proposal,
    Session,
)
from mxcubecore.utils.conversion import string_types

suds_encode = str.encode

if sys.version_info > (3, 0):
    suds_encode = bytes.decode


def utf_encode(res_d):
    for key, value in res_d.items():
        if isinstance(value, dict):
            utf_encode(value)

        try:
            # Decode bytes object or encode str object depending
            # on Python version
            res_d[key] = suds_encode("utf8", "ignore")
        except Exception:
            # If not primitive or Text data, complext type, try to convert to
            # dict or str if the first fails
            try:
                res_d[key] = utf_encode(asdict(value))
            except Exception:
                try:
                    res_d[key] = str(value)
                except Exception:
                    res_d[key] = "ISPyBClient: could not encode value"

    return res_d


def utf_decode(res_d):
    for key, value in res_d.items():
        if isinstance(value, dict):
            utf_decode(value)
        try:
            res_d[key] = value.decode("utf8", "ignore")
        except Exception:
            pass

    return res_d


class ISPyBDataAdapter:
    def __init__(
        self,
        ws_root: str,
        proxy: dict,
        ws_username: str,
        ws_password: str,
        beamline_name: str,
    ):
        self.ws_root = ws_root
        self.ws_username = ws_username
        self.ws_password = ws_password
        self.proxy = proxy  # type: ignore
        self.beamline_name = beamline_name

        # the duration of the session in days for the ones that are created by MXCuBE
        self.new_sesssion_duration_days = 2

        self.logger = logging.getLogger("ispyb_adapter")

        self._shipping = self.__create_client(
            self.ws_root + "ToolsForShippingWebService?wsdl"
        )
        self._collection = self.__create_client(
            self.ws_root + "ToolsForCollectionWebService?wsdl"
        )
        self._tools_ws = self.__create_client(
            self.ws_root + "ToolsForBLSampleWebService?wsdl"
        )

    def __create_client(self, url: str):
        """
        Given a url it will create
        """
        if self.ws_root.strip().startswith("https://"):
            from suds.transport.https import HttpAuthenticated
        else:
            from suds.transport.http import HttpAuthenticated

        client = Client(
            url,
            timeout=3,
            transport=HttpAuthenticated(
                username=self.ws_username,  # type: ignore
                password=self.ws_password,
                proxy=self.proxy,
            ),
            cache=None,
            proxy=self.proxy,
        )
        client.set_options(cache=None, location=url)
        return client

    def isEnabled(self) -> object:
        return self._shipping  # type: ignore

    def create_session(self, proposal_id: str, beamline_name: str) -> Session:
        try:
            current_time = time.localtime()
            start_time = time.strftime("%Y-%m-%d 00:00:00", current_time)
            end_time = (
                time.mktime(current_time)
                + 60 * 60 * 24 * self.new_sesssion_duration_days
            )
            tomorrow = time.localtime(end_time)
            end_time = time.strftime("%Y-%m-%d 07:59:59", tomorrow)

            session = {}
            session["proposalId"] = proposal_id
            session["beamlineName"] = beamline_name
            session["scheduled"] = 0
            session["nbShifts"] = 3
            session["comments"] = "Session created by the BCM"
            session["startDate"] = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
            session["endDate"] = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")

            # return data to original codification
            session_id = self._collection.service.storeOrUpdateSession(
                utf_decode(session)
            )
            logging.getLogger("ispyb_client").info(
                "Session created. session_id=%s" % session_id
            )
            response = self._collection.service.findSession(session_id)
            return self.__to_session(asdict(response))
        except Exception:
            raise

    def __is_scheduled_now(self, startDate: datetime, endDate: datetime) -> bool:
        return self.__is_time_between(startDate, endDate)

    def __is_time_between(
        self, start_date: datetime, end_date: datetime, check_time=None
    ):
        if start_date is None or end_date is None:
            return False

        begin_time = start_date.date()
        end_time = end_date.date()

        # If check time is not given, default to current UTC time
        check_time = check_time or datetime.utcnow().date()
        if begin_time <= check_time <= end_time:
            return True
        else:
            return False

    def __to_session(self, session: Dict[str, str]) -> Session:
        """
        Converts a dictionary composed by the person entries to the object proposal
        """
        proposal_name = session.get("proposalName")
        proposal_code = "".join(
            itertools.takewhile(lambda c: not c.isdigit(), proposal_name)
        )
        proposal_number = proposal_name[len(proposal_code) :]
        return Session(
            code=proposal_code,
            number=proposal_number,
            proposal_name=proposal_name,
            session_id=session.get("sessionId"),
            proposal_id=session.get("proposalId"),
            beamline_name=session.get("beamlineName"),
            comments=session.get("comments"),
            end_date=datetime.strftime(
                session.get("endDate"), "%Y%m%d"
            ),  # session.get("endDate"),
            nb_shifts=session.get("nbShifts"),
            scheduled=session.get("scheduled"),
            start_date=datetime.strftime(
                session.get("startDate"), "%Y%m%d"
            ),  # session.get("startDate"),
            start_datetime=session.get("startDate"),
            end_datetime=session.get("endDate"),
            is_scheduled_time=self.__is_scheduled_now(
                session.get("startDate"), session.get("endDate")
            ),
            is_scheduled_beamline=True,
        )

    def __to_proposal(self, proposal: Dict[str, str]) -> Proposal:
        """
        Converts a dictionary composed by the person entries to the object proposal
        """
        return Proposal(
            code=proposal.get("code").lower(),
            number=proposal.get("number").lower(),
            proposal_id=proposal.get("proposalId"),
            title=proposal.get("title"),
            type=proposal.get("type"),
        )

    def _debug(self, msg: str):
        logging.getLogger("HWR").debug(msg)

    def _exception(self, msg: str):
        logging.getLogger("HWR").exception(msg)

    def find_session(self, session_id: str) -> Session:
        try:
            response = self._collection.service.findSession(session_id)
            return self.__to_session(asdict(response))
        except Exception as e:
            self._exception(str(e))
            raise e

    def find_proposal(self, code: str, number: str) -> Proposal:
        try:
            self._debug("find_proposal. code=%s number=%s" % (code, number))
            response = self._shipping.service.findProposal(code, number)  # type: ignore
            return self.__to_proposal(asdict(response))  # type: ignore
        except Exception as e:
            self._exception(str(e))
            raise e

    def find_proposal_by_login_and_beamline(
        self, username: str, beamline_name: str
    ) -> Proposal:
        try:
            self._debug(
                "find_proposal_by_login_and_beamline. username=%s beamline_name=%s"
                % (username, beamline_name)
            )
            response = self._shipping.service.findProposalByLoginAndBeamline(
                username, beamline_name
            )
            print(response)
            if response is None:
                return []

            return self.__to_proposal(asdict(response))  # type: ignore
        except Exception as e:
            self._exception(str(e))
            raise e

    def find_sessions_by_proposal_and_beamLine(
        self, code: str, number: str, beamline: str
    ) -> List[Session]:
        try:
            self._debug(
                "find_sessions_by_proposal_and_beamLine. code=%s number=%s beamline=%s"
                % (code, number, beamline)
            )

            responses = self._collection.service.findSessionsByProposalAndBeamLine(
                code.upper(), number, beamline
            )
            sessions: List[Session] = []
            for response in responses:
                sessions.append(self.__to_session(asdict(response)))
            return sessions
        except Exception as e:
            self._exception(str(e))
            # raise e
        return []

    def _is_session_scheduled_today(self, session: Session) -> bool:
        now = datetime.now()
        if session.start_datetime.date() <= now.date() <= session.end_datetime.date():
            return True
        return False

    def get_sessions_by_code_and_number(
        self, code: str, number: str, beamline_name: str
    ) -> LimsSessionManager:
        try:
            self._debug(
                "get_sessions_by_code_and_number. code=%s number=%s beamline_name=%s"
                % (code, number, beamline_name)
            )
            sessions = self.find_sessions_by_proposal_and_beamLine(
                code, number, beamline_name
            )
            return LimsSessionManager(sessions=sessions)
        except WebFault as e:
            self._exception(str(e))
            raise e

    def get_person_by_username(self, username: str) -> Dict:
        try:
            person = self._shipping.service.findPersonByLogin(username)
            return asdict(person)
        except WebFault as e:
            self._error(str(e))

        return {}

    def get_sessions_by_username(
        self, username: str, beamline_name: str
    ) -> LimsSessionManager:
        try:
            self._debug(
                "get_sessions_by_username. username=%s beamline_name=%s"
                % (username, beamline_name)
            )

            proposal = self.find_proposal_by_login_and_beamline(username, beamline_name)  # type: ignore
            sessions = self.find_sessions_by_proposal_and_beamLine(
                proposal.code, proposal.number, beamline_name
            )
            return LimsSessionManager(
                sessions=sessions,
            )
        except WebFault as e:
            self._exception(str(e))
        return LimsSessionManager()

    ############# Legacy methods #####################
    def _store_data_collection_group(self, group_data):
        return self._collection.service.storeOrUpdateDataCollectionGroup(group_data)

    def store_data_collection_group(self, mx_collection):
        group_id = None
        if mx_collection["ispyb_group_data_collections"]:
            group_id = mx_collection.get("group_id", None)

        # Create a new group id
        group = ISPyBValueFactory().dcg_from_dc_params(self._collection, mx_collection)
        # if group_id is None:
        group_id = self._collection.service.storeOrUpdateDataCollectionGroup(group)
        mx_collection["group_id"] = group_id

    def _update_data_collection(self, mx_collection):
        if "collection_id" in mx_collection:
            try:
                # Update the data collection group
                self.store_data_collection_group(mx_collection)
                data_collection = ISPyBValueFactory().from_data_collect_parameters(
                    self._collection, mx_collection
                )
                self._collection.service.storeOrUpdateDataCollection(data_collection)
            except WebFault as e:
                logging.getLogger("ispyb_client").exception(e)
            except URLError as e:
                logging.getLogger("ispyb_client").exception(e)
        else:
            logging.getLogger("ispyb_client").error(
                "Error in update_data_collection: "
                + "collection-id missing, the ISPyB data-collection is not updated."
            )

        return (0, 0)

    def store_image(self, image_dict):
        if self._collection:
            logging.getLogger("HWR").debug("Storing image in lims")
            if "dataCollectionId" in image_dict:
                try:
                    # Possible fields of ISPYB storeOrUpdateImage method are:
                    #  comments (str): additional comments,
                    #  cumulativeIntensity (float): image cumulative intensity value,
                    #  dataCollectionId (int): collection id,
                    #  fileName (str): name of the master file (.h5),
                    #  fileLocation (str): location of the master file,
                    #  imageId (str | None): if None the new id will be created,
                    #  imageNumber (int): number of frames,
                    #  jpegFileFullPath (str): path to jpeg file,
                    #  jpegThumbnailFileFullPath (str): path to jpeg thumbnail file,
                    #  machineMessage: the operator message from the machine,
                    #  measuredIntensity (float): measured flux value,
                    #  synchrotronCurrent (float | str): machine current,
                    #  temperature (float): temperature of the cryo system
                    image_id = self._collection.service.storeOrUpdateImage(image_dict)
                    logging.getLogger("HWR").debug(
                        "  - storing image in lims ok. id : %s" % image_id
                    )
                    return image_id
                except WebFault:
                    logging.getLogger("ispyb_client").exception(
                        "ISPyBClient: exception in store_image"
                    )
                except URLError as e:
                    logging.getLogger("ispyb_client").exception(e)
            else:
                logging.getLogger("ispyb_client").error(
                    "Error in store_image: "
                    + "data_collection_id missing, could not store image in ISPyB"
                )
        else:
            logging.getLogger("ispyb_client").exception(
                "Error in store_image: could not connect to server"
            )

    def get_samples(self, proposal_id):
        response_samples = []

        if self._tools_ws:
            try:
                response_samples = (
                    self._tools_ws.service.findSampleInfoLightForProposal(
                        proposal_id, self.beamline_name
                    )
                )
                response_samples = [
                    utf_encode(asdict(sample)) for sample in response_samples
                ]

            except WebFault as e:
                logging.getLogger("ispyb_client").exception(str(e))
            except URLError as e:
                logging.getLogger("ispyb_client").exception(e)
        else:
            logging.getLogger("ispyb_client").exception(
                "Error in get_samples: could not connect to server"
            )

        return response_samples

    def store_robot_action(self, robot_action_dict):
        """Stores robot action"""
        logging.getLogger("HWR").debug("Storing robot actions in lims")

        if True:
            robot_action_vo = self._collection.factory.create("robotActionWS3VO")

            robot_action_vo.actionType = robot_action_dict.get("actionType")
            robot_action_vo.containerLocation = robot_action_dict.get(
                "containerLocation"
            )
            robot_action_vo.dewarLocation = robot_action_dict.get("dewarLocation")

            robot_action_vo.message = robot_action_dict.get("message")
            robot_action_vo.sampleBarcode = robot_action_dict.get("sampleBarcode")
            robot_action_vo.sessionId = robot_action_dict.get("sessionId")
            robot_action_vo.blSampleId = robot_action_dict.get("sampleId")
            robot_action_vo.startTime = datetime.strptime(
                robot_action_dict.get("startTime"), "%Y-%m-%d %H:%M:%S"
            )
            robot_action_vo.endTime = datetime.strptime(
                robot_action_dict.get("endTime"), "%Y-%m-%d %H:%M:%S"
            )
            robot_action_vo.status = robot_action_dict.get("status")
            robot_action_vo.xtalSnapshotAfter = robot_action_dict.get(
                "xtalSnapshotAfter"
            )
            robot_action_vo.xtalSnapshotBefore = robot_action_dict.get(
                "xtalSnapshotBefore"
            )
            return self._collection.service.storeRobotAction(robot_action_vo)
        return None

    def associate_bl_sample_and_energy_scan(self, entry_dict):
        try:
            return self._collection.service.storeBLSampleHasEnergyScan(
                entry_dict["energyScanId"], entry_dict["blSampleId"]
            )
        except Exception as e:
            logging.getLogger("ispyb_client").exception(str(e))
            return -1

    def get_data_collection(self, data_collection_id):
        try:
            dc_response = self._collection.service.findDataCollection(
                data_collection_id
            )

            dc = utf_encode(asdict(dc_response))
            dc["startTime"] = datetime.strftime(dc["startTime"], "%Y-%m-%d %H:%M:%S")
            dc["endTime"] = datetime.strftime(dc["endTime"], "%Y-%m-%d %H:%M:%S")
            return dc
        except Exception as e:
            logging.getLogger("ispyb_client").exception(str(e))
            return {}

    def find_detector(self, type, manufacturer, model, mode):
        """
        Returns the Detector3VO object with the characteristics
        matching the ones given.
        """
        if self._collection:
            try:
                res = self._collection.service.findDetectorByParam(
                    "", manufacturer, model, mode
                )
                return res
            except WebFault:
                logging.getLogger("ispyb_client").exception(
                    "ISPyBClient: exception in find_detector"
                )
        else:
            logging.getLogger("ispyb_client").exception(
                "Error find_detector: could not connect to" + " server"
            )

    def update_session(self, session_dict):
        if self._collection:
            try:
                print(session_dict)
                # The old API used date formated strings and the new
                # one uses DateTime objects.
                session_dict["startDate"] = datetime.strptime(
                    session_dict["startDate"], "%Y-%m-%d %H:%M:%S"
                )
                session_dict["endDate"] = datetime.strptime(
                    session_dict["endDate"], "%Y-%m-%d %H:%M:%S"
                )

                try:
                    session_dict["lastUpdate"] = datetime.strptime(
                        session_dict["lastUpdate"].split("+")[0], "%Y-%m-%d %H:%M:%S"
                    )
                    session_dict["timeStamp"] = datetime.strptime(
                        session_dict["timeStamp"].split("+")[0], "%Y-%m-%d %H:%M:%S"
                    )
                except Exception:
                    pass

                # return data to original codification
                decoded_dict = utf_decode(session_dict)
                session = self._collection.service.storeOrUpdateSession(decoded_dict)

                # changing back to string representation of the dates,
                # since the session_dict is used after this method is called,
                session_dict["startDate"] = datetime.strftime(
                    session_dict["startDate"], "%Y-%m-%d %H:%M:%S"
                )
                session_dict["endDate"] = datetime.strftime(
                    session_dict["endDate"], "%Y-%m-%d %H:%M:%S"
                )

            except WebFault as e:
                session = {}
                logging.getLogger("ispyb_client").exception(str(e))
            except URLError:
                logging.getLogger("ispyb_client").exception(_CONNECTION_ERROR_MSG)

            logging.getLogger("ispyb_client").info(
                "[ISPYB] Session created: %s" % session
            )
            return session
        else:
            logging.getLogger("ispyb_client").exception(
                "Error in create_session: could not connect to server"
            )

    def store_beamline_setup(self, session_id, bl_config):
        blSetupId = None
        if self._collection:
            session = {}

            try:
                session = self.get_session(session_id)
            except Exception:
                logging.getLogger("ispyb_client").exception(
                    "ISPyBClient: exception in store_beam_line_setup"
                )
            else:
                if session is not None:
                    try:
                        blSetupId = self._collection.service.storeOrUpdateBeamLineSetup(
                            bl_config
                        )

                        session["beamLineSetupId"] = blSetupId
                        self.update_session(session)

                    except WebFault as e:
                        logging.getLogger("ispyb_client").exception(str(e))
                    except URLError:
                        logging.getLogger("ispyb_client").exception(
                            _CONNECTION_ERROR_MSG
                        )
        else:
            logging.getLogger("ispyb_client").exception(
                "Error in store_beamline_setup: could not connect" + " to server"
            )

        return blSetupId

    def store_data_collection(self, mx_collection, bl_config=None):
        logging.getLogger("HWR").info("Storing datacollection in ISPyB")
        return self._store_data_collection(mx_collection, bl_config=bl_config)

    def update_data_collection(self, mx_collection):
        logging.getLogger("HWR").info("Updating datacollection in ISPyB")
        return self._update_data_collection(mx_collection)

    def finalize_data_collection(self, mx_collection):
        logging.getLogger("HWR").info("Updating datacollection in ISPyB")
        return self._update_data_collection(mx_collection)

    def _store_data_collection(self, mx_collection, bl_config=None):
        data_collection = ISPyBValueFactory().from_data_collect_parameters(
            self._collection, mx_collection
        )

        detector_id = 0
        if bl_config:
            lims_beamline_setup = ISPyBValueFactory.from_bl_config(
                self._collection, bl_config
            )

            lims_beamline_setup.synchrotronMode = data_collection.synchrotronMode

            self.store_beamline_setup(mx_collection["sessionId"], lims_beamline_setup)

            detector_params = ISPyBValueFactory().detector_from_blc(
                bl_config, mx_collection
            )

            detector = self.find_detector(*detector_params)
            detector_id = 0

            if detector:
                detector_id = detector.detectorId
                data_collection.detectorId = detector_id

        collection_id = self._collection.service.storeOrUpdateDataCollection(
            data_collection
        )
        logging.getLogger("HWR").debug(
            "Storing data collection ok. collection id : %s" % collection_id
        )

        return collection_id, detector_id

    def get_session(self, session_id):
        try:
            logging.getLogger("HWR").debug("get_session. session_id=%s" % session_id)
            session = self._collection.service.findSession(session_id)
            logging.getLogger("HWR").debug("get_session. session=%s" % session)
            if session is not None:
                session.startDate = datetime.strftime(
                    session.startDate, "%Y-%m-%d %H:%M:%S"
                )
                session.endDate = datetime.strftime(
                    session.endDate, "%Y-%m-%d %H:%M:%S"
                )
                return utf_encode(asdict(session))
        except Exception as e:
            logging.getLogger("ispyb_client").exception(e)

        return {}

    def store_energy_scan(self, energyscan_dict):
        status = {"energyScanId": -1}

        try:
            energyscan_dict["startTime"] = datetime.strptime(
                energyscan_dict["startTime"], "%Y-%m-%d %H:%M:%S"
            )

            energyscan_dict["endTime"] = datetime.strptime(
                energyscan_dict["endTime"], "%Y-%m-%d %H:%M:%S"
            )

            try:
                del energyscan_dict["remoteEnergy"]
            except KeyError:
                pass

            status["energyScanId"] = self._collection.service.storeOrUpdateEnergyScan(
                energyscan_dict
            )

        except Exception as e:
            logging.getLogger("ispyb_client").exception(str(e))

        return status

    def store_xfe_spectrum(self, xfespectrum_dict):
        status = {"xfeFluorescenceSpectrumId": -1}
        try:
            if isinstance(xfespectrum_dict["startTime"], string_types):
                xfespectrum_dict["startTime"] = datetime.strptime(
                    xfespectrum_dict["startTime"], "%Y-%m-%d %H:%M:%S"
                )

                xfespectrum_dict["endTime"] = datetime.strptime(
                    xfespectrum_dict["endTime"], "%Y-%m-%d %H:%M:%S"
                )
            else:
                xfespectrum_dict["startTime"] = xfespectrum_dict["startTime"]
                xfespectrum_dict["endTime"] = xfespectrum_dict["endTime"]

            status["xfeFluorescenceSpectrumId"] = (
                self._collection.service.storeOrUpdateXFEFluorescenceSpectrum(
                    xfespectrum_dict
                )
            )

        except URLError as e:
            logging.getLogger("ispyb_client").exception(str(e))

        return status

    def update_bl_sample(self, bl_sample):
        if self._disabled:
            return {}

        if self._tools_ws:
            try:
                status = self._tools_ws.service.storeOrUpdateBLSample(bl_sample)
            except WebFault as e:
                logging.getLogger("ispyb_client").exception(str(e))
                status = {}
            except URLError:
                logging.getLogger("ispyb_client").exception(
                    "Could not connect to ISPyB, URLerror"
                )

            return status
        else:
            logging.getLogger("ispyb_client").exception(
                "Error in update_bl_sample: could not connect to server"
            )
