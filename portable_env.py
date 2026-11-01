"""App-local Tk configuration, used with the bundled embeddable Python."""
import os
from pathlib import Path

def configure():
    runtime=Path(__file__).resolve().parent/'runtime'
    for variable,directory in [('TCL_LIBRARY','tcl/tcl8.6'),('TK_LIBRARY','tcl/tk8.6')]:
        if (runtime/directory).exists():os.environ[variable]=str(runtime/directory)
