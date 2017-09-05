import Session

class ESRFSession(Session):
    def __init__(self, name):
        Session.__init__(self, name)

    def init(self):
        Session.init(self)

        archive_base_directory = self['file_info'].getProperty('archive_base_directory')
        if archive_base_directory:
            archive_folder = os.path.join(self['file_info'].getProperty('archive_folder'), time.strftime('%Y'))
            queue_model_objects.PathTemplate.set_archive_path(archive_base_directory, archive_folder)
