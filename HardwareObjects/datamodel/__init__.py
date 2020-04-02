# -*- coding: utf-8 -*-
import sys
import pkgutil

if sys.version_info <= (2, 8):
    from .data_model_py2 import *
else:
    from .data_model_py3 import *
