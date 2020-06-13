#!/bin/bash

# 99 matches the number in the rfcomm.conf file
# rfcomm release 99
# rfcomm bind 99 all
exec python3 /usr/local/bin/auto-telemetry-collector.py 
