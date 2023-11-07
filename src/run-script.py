#!/usr/bin/env python3
import sys

from mini_apps.settings import Settings

Settings.load_global()

sys.argv.pop(0)

exec(open(sys.argv[0]).read())
