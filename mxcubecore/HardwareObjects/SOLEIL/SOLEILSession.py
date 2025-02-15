import logging
import os
import time

import Session

from mxcubecore import HardwareRepository as HWR


class SOLEILSession(Session.Session):
    def __init__(self, *args, **kwargs):
        Session.Session.__init__(self, *args, **kwargs)
        self.username = ""
        self.gid = ""
        self.uid = ""
        self.projuser = ""

    def path_to_ispyb(self, path):
        ispyb_base = self["file_info"].get_property("ispyb_base_directory") % {
            "projuser": self.projuser
        }
        path = path.replace(
            self["file_info"].get_property("base_directory"), ispyb_base
        )
        return path

    def set_user_info(self, username, user_id, group_id, projuser=None):
        logging.debug(
            "SESSION - User %s logged in. gid=%s / uid=%s "
            % (username, group_id, user_id)
        )
        self.username = username
        self.group_id = group_id
        self.user_id = user_id
        self.projuser = projuser

    def get_proposal_number(self):
        """
        :returns: The proposal, 'local-user' if no proposal is
                  available
        :rtype: str
        """

        if self.proposal_number:
            return "%s" % (self.proposal_number)
        else:
            return "local-user"

    def get_base_data_directory(self):
        """
        Returns the base data directory taking the 'contextual'
        information into account, such as if the current user
        is inhouse.

        :returns: The base data path.
        :rtype: str
        """
        user_category = ""
        directory = ""

        if self.session_start_date:
            start_time = self.session_start_date.split(" ")[0]  # .replace('-', '')
        else:
            # PL. To avoid mixing users directory if they restart the application
            # after midnight but before 8 AM, the directory date doesn't change:
            _local_time = time.localtime()
            if _local_time[3] > 7:
                start_time = time.strftime("%Y-%m-%d")
            else:
                # substract 8 hours to current date to get yesterday's date.
                _local_time = time.gmtime((time.time() - 8 * 60 * 60))
                start_time = time.strftime("%Y-%m-%d", _local_time)

        if self.is_inhouse():
            # directory = os.path.join(self.base_directory, self.endstation_name,
            #                         self.get_user_category(), self.get_proposal(),
            #                         start_time)
            directory = os.path.join(
                self.base_directory,
                start_time,
                self.proposal_number,
                self.get_proposal_number(),
            )
        else:
            # directory = os.path.join(self.base_directory, self.get_user_category(),
            #                         self.get_proposal(), self.endstation_name,
            #                         start_time)
            logging.debug("SoleilSession self.base_directory %s" % self.base_directory)
            logging.debug("SoleilSession start_time %s" % start_time)
            logging.debug(
                "SoleilSession self.proposal_number %s" % self.proposal_number
            )
            logging.debug(
                "SoleilSession self.get_proposal_number() %s"
                % self.get_proposal_number()
            )
            directory = os.path.join(
                self.base_directory, start_time, self.get_proposal_number()
            )

        return directory

    # def get_rawdata_directory(self, directory=None):
    #    if directory is None:
    #        thedir = self.get_base_data_directory()
    #    else:
    #        thedir = directory
    #    if 'RAW_DATA' not in thedir:
    #        thedir = os.path.join(thedir, 'ARCHIVE')
    #    return thedir

    def get_archive_directory(self, directory=None):
        if directory is None:
            thedir = self.get_base_data_directory()
        else:
            thedir = directory

        if "RAW_DATA" in thedir:
            thedir = thedir.replace("RAW_DATA", "ARCHIVE")
        else:
            thedir = os.path.join(thedir, "ARCHIVE")

        return thedir

    def get_ruche_info(self, path):
        if self.is_inhouse(self.username):
            usertype = "soleil"
        else:
            usertype = "users"

        basedir = os.path.dirname(path)
        ruchepath = basedir.replace(
            self["file_info"].get_property("base_directory"), ""
        )
        if ruchepath and ruchepath[0] == os.path.sep:
            ruchepath = ruchepath[1:]

        infostr = "%s %s %s %s %s %s\n" % (
            usertype,
            self.username,
            self.user_id,
            self.group_id,
            basedir,
            ruchepath,
        )
        return infostr


def test():
    hwr = HWR.get_hardware_repository()
    hwr.connect()

    sess = HWR.beamline.session

    sess.set_user_info("mx2014", "143301", "14330", "20100023")

    path = "/927bis/ccd/2015_Run2/visitor/mx2014/px2/20150120/ARCHIVE/mx2014/mx2014_2_4.snapshot.jpeg"
    ispyb_path = sess.path_to_ispyb(path)

    print(path)
    print("  will become ")
    print(ispyb_path)

    # print sess.get_ruche_info(path)


if __name__ == "__main__":
    test()
