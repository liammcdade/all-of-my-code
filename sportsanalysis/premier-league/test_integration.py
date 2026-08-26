import sys
sys.stdout.reconfigure(encoding='utf-8')
import random
random.seed(42)
import numpy as np
np.random.seed(42)

import UCL
import UEL

UCL.NUM_CL_SIMS = 5
UEL.NUM_UEL_SIMS = 5

import importlib
import importlib.util
spec = importlib.util.spec_from_file_location("season", "26-27-season.py")
season = importlib.util.module_from_spec(spec)
spec.loader.exec_module(season)

season.main()
