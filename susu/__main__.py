"""Allow `python -m susu ...`."""

import sys

from .cli import main

sys.exit(main())
