from sample_changer import SC3

LOADED_SAMPLES = [('', 1, 1, '', 1), ('', 1, 2, '', 1), ('', 1, 3, '', 1), 
                  ('', 1, 4,'', 1), ('', 1, 5, '', 1), ('', 1, 6, '', 1), 
                  ('', 1, 7, '', 1), ('', 1, 8, '', 1), ('', 1, 9, '', 1), 
                  ('', 1, 10, '', 1), ('', 2, 1, '', 18), ('', 2, 2, '', 18), 
                  ('', 2, 3, '', 1), ('', 2, 4, '', 1), ('', 2, 5, '', 1), 
                  ('', 2, 6, '', 18), ('', 2, 7, '', 18), ('', 2, 8, '', 18), 
                  ('', 2, 9, '', 1), ('', 2, 10, '', 1), ('', 3, 1, '', 1), 
                  ('', 3, 2, '', 18), ('', 3, 3, '', 18), ('', 3, 4, '', 18), 
                  ('', 3, 5, '', 1), ('', 3, 6, '', 1), ('', 3, 7, '', 18), 
                  ('', 3, 8, '', 18), ('', 3, 9, '', 1), ('', 3, 10, '', 1), 
                  ('', 4, 1, '', 18), ('', 4, 2, '', 18), ('', 4, 3, '', 18), 
                  ('', 4, 4, '', 18),('', 4, 5, '', 18), ('', 4, 6, '', 1), 
                  ('', 4, 7, '', 1), ('', 4, 8, '', 1), ('', 4, 9, '', 18), 
                  ('', 4, 10, '', 18), ('', 5, 1, '', 18), ('', 5, 2, '', 18), 
                  ('', 5, 3, '', 18), ('', 5, 4, '', 18), ('', 5, 5, '', 18), 
                  ('', 5, 6, '', 18), ('', 5, 7, '', 18), ('', 5, 8, '', 18), 
                  ('', 5, 9, '', 18), ('', 5, 10, '', 18)]


class SampleChangerMockup(SC3.SC3):
    def __init__(self, *args, **kwargs):
        super(SampleChangerMockup, self).__init__(*args, **kwargs)

    def init(self):
        for channel_name in ("_state", "_selected_basket", "_selected_sample"):
            fun = lambda x: x
            setattr(self, channel_name, fun)
           
        for command_name in ("_abort", "_getInfo", "_is_task_running", \
                             "_check_task_result", "_load", "_unload",\
                             "_chained_load", "_set_sample_charge", "_scan_basket",\
                             "_scan_samples", "_select_sample", "_select_basket", "_reset", "_reset_basket_info"):
            fun = lambda x: x
            setattr(self, command_name, fun)

        pass

    def load_sample(self, holder_length, sample_location, wait):
        return

    def load(self, sample, wait):
        import pdb
        pdb.set_trace()
        return sample

    def unload(self, sample_slot, wait):
        return
