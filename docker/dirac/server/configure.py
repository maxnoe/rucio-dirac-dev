__RCSID__ = "$Id$"

import DIRAC
from DIRAC import gLogger
from DIRAC.ConfigurationSystem.Client.CSAPI import CSAPI
from DIRAC.Core.Base import Script
from diraccfg import CFG

Script.parseCommandLine()

args = Script.getPositionalArgs()

if len(args) == 1:
    config_file = args[0]
else:
    gLogger.error("Needs 1 argument: configuration file")
    DIRAC.exit(-1)

cs_api = CSAPI()
cfg = CFG()

cfg.loadFromFile(config_file)

res = cs_api.mergeWithCFG(cfg)
if not res["OK"]:
    gLogger.error("Can't merge with input configuration", f"{res['Message']}")
    DIRAC.exit(-1)

res = cs_api.commit()
if not res["OK"]:
    gLogger.error("Can't commit new configuration data", f"{res['Message']}")
    DIRAC.exit(-1)
