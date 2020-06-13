#!/usr/bin/env python3

"""
Auto Telemetry Collector

Usage:
  auto-telemetry-collector.py --device <device>
  auto-telemetry-collector.py -h | --help
  auto-telemetry-collector.py --version

Options:
  -h --help     Show this screen.
  --version     Show version.
  --device <device>  Bluetooth or USB Device [default: /dev/ttyUSB0].
"""
from docopt import docopt


import sys
import time
sys.stdout.flush()

from prometheus_client import start_http_server
from prometheus_client import Gauge
import obd
# obd.logger.setLevel(obd.logging.DEBUG)

def connect_and_watch(device):
    connection = obd.Async(arguments["--device"]) # auto connect
    print("####################################", flush=True)
    for c in connection.supported_commands:
        print(f"-  {c.name} on ECU {c.ecu}")
    print("####################################")
    connection.watch(obd.commands.RPM, callback=collect_RPM)
    connection.watch(obd.commands.FUEL_RAIL_PRESSURE_DIRECT, callback=collect_FUEL_RAIL_PRESSURE_DIRECT)
    connection.start() # start the async update loop
    print (". OBD Async Started")
    return connection


def collect_RPM(rpm):
    #print(rpm)
    #print(f"RPM = [{rpm.value.magnitude}]")
    g_rpm.set(rpm.value.magnitude)   # Set to a given value

def collect_FUEL_RAIL_PRESSURE_DIRECT(x):
    #print(fuel_pressure)
    #print(f"RPM = [{fuel_pressure.value.magnitude}]")
    g_fuel_pressure.set(x.value.magnitude)   # Set to a given value

if __name__ == "__main__":
    arguments = docopt(__doc__, version='1.0.1')

    # Start the prometheus collector
    start_http_server(8000)

    g_rpm = Gauge('engine_rpm', 'Revs Per Minute')
    g_fuel_pressure = Gauge('fuel_pressure', 'Fuel Pressure kPa')
    device = arguments["--device"]

    conn = connect_and_watch(device)

    while True:
         status = conn.status()
         print(f"{device} is {status}")
         if status == "Not Connected":
            conn = connect_and_watch(device)
        
         print("{} is {}".format(arguments["--device"], status))
         time.sleep(10)
