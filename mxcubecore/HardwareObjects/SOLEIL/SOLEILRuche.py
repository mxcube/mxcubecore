import os
import time
import logging
from HardwareRepository import HardwareRepository
from HardwareRepository.BaseHardwareObjects import HardwareObject


class SOLEILRuche(HardwareObject):
    def __init__(self, *args, **kwargs):
        HardwareObject.__init__(self, *args, **kwargs)

    def init(self):
        self.session_ho = self.getObjectByRole("session")
        self.sync_dir = self.getProperty("sync_dir")

    def trigger_sync(self, path):

        try:
            logging.getLogger().info("<SOLEIL Ruche> - trigger_sync path %s." % path)
            logging.getLogger().info(
                "<SOLEIL Ruche> username: %s  user_id: %s projuser: %s"
                % (
                    self.session_ho.username,
                    self.session_ho.user_id,
                    self.session_ho.projuser,
                )
            )
            if self.session_ho.user_id == None:
                return
        except:
            pass
        if os.path.isdir(path):
            path_to_sync = path
        elif os.path.exists(path):
            path_to_sync = os.path.dirname(os.path.abspath(path))
        else:
            logging.getLogger().info(
                "<SOLEIL Ruche> - sync on non existant path %s. Ignored" % path
            )
            path_to_sync = os.path.dirname(os.path.abspath(path))
            # return

        logging.getLogger().info(
            "<SOLEIL Ruche> - triggering data sync on directory %s" % path_to_sync
        )
        ruche_info = self.session_ho.get_ruche_info(path_to_sync)
        try:
            sync_filename = time.strftime(
                "%Y_%m_%d-%H_%M_%S", time.localtime(time.time())
            )
            sync_file_path = os.path.join(self.sync_dir, sync_filename)
            open(sync_file_path, "w").write(ruche_info)
        except:
            logging.getLogger().error(
                "<SOLEIL Ruche> - Cannot write sync in path %s." % sync_file_path
            )


def test():
    import sys

    hwr_directory = os.environ["XML_FILES_PATH"]

    hwr = HardwareRepository.HardwareRepository(os.path.abspath(hwr_directory))
    hwr.connect()

    ruche = hwr.getHardwareObject("/ruche")
    filename = sys.argv[1]
    ruche.trigger_sync(filename)


if __name__ == "__main__":
    test()
