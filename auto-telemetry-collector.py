#!/usr/bin/env python3

"""
Auto Telemetry Collector

Usage:
  auto-telemetry-collector.py monitor --device <device> --config <config_yaml> [ --noconnect ]
  auto-telemetry-collector.py inspect --device <device> 
  auto-telemetry-collector.py clear --device <device> 
  auto-telemetry-collector.py -h | --help
  auto-telemetry-collector.py --version

Options:
  -h --help                Show this screen.
  --version                Show version.
  --device <device>        Bluetooth or USB Device [default: /dev/ttyUSB0].
  --config <config_yaml>   Config yaml file
  --carname <carname>      name of car
"""
from docopt import docopt
import sys
import yaml
import os
import time
import obd
import pint
import time
import random

from threading import Thread
from flask import Flask, json
from flask_cors import CORS
import socket

from columnar import columnar
from datetime import datetime

#
# UDP Socket for influx
#

udp = socket.socket(socket.AF_INET, # Internet
                     socket.SOCK_DGRAM) # UDP

#
# Webserver for the grafana back to the monitor
#
api = Flask(__name__)
CORS(api, resources={r"/api/*": {"origins": "*"}})
connection = None

def api_daemon():
    api.run(host="0.0.0.0", port=5000)

@api.route('/api/getcodes', methods=['GET'])
def api_get_errorcodes():
    print("Request for DTC fault codes")
    if connection is not None:
        return {
            "status": "connected",
            "codes" : get_dtc_codes(connection)
        }
    else:
        return {
            "status": "not connected to a vehicle"
        }

@api.route('/api/clearcodes', methods=['GET'])
def api_clear_codes():
    print("Request to clear DTC fault codes")
    if connection is not None:
        return {
            "status": "connected",
            "response" : clear_dtcs(connection)
        }
    else:
        return {
            "status": "not connected to a vehicle"
        }

@api.route('/api/getvehicleinfo', methods=['GET'])
def api_get_vehicle_info():
    print("Request for vehicle info")
    if connection is not None:
        return {
            "status": "connected",
            "supported_commands" : get_supported_commands(connection)
        }
    else:
        return {
            "status": "not connected to a vehicle"
        }

def start_webserver():
    t = Thread(target=api_daemon)
    t.daemon = True
    t.start()

#
# OBD2 type stuff
#
def inspect(connection):

    # we are going to output the supported commands in YAML format
    # so they can go back into the config file.

    supported_commands = []
    for c in connection.supported_commands:
        # embedded the YAML entries - and a comment
        # supported_commands.append({ "name": f"- {c.name}", "desc": f"# {c.desc}", "ecu": c.ecu })
        supported_commands.append([ f"- {c.name}", f"# {c.desc}", c.ecu ])
        
    commands = columnar(supported_commands, headers=None, no_borders=True)

    print(commands)
    
    print("------ current fault codes -----")
    print(yaml.dump(get_dtc_codes(connection)))

def get_supported_commands(connection):
    supported_commands = []
    for c in connection.supported_commands:
        # embedded the YAML entries - and a comment
        # supported_commands.append({ "name": f"- {c.name}", "desc": f"# {c.desc}", "ecu": c.ecu })
        supported_commands.append(
            { 
                "name": c.name,
                "desc": c.desc,
                "ecu_id": c.ecu
            }
        )
    return supported_commands
    
def get_dtc_codes(connection):
    response = connection.query(obd.commands.GET_DTC)
    codes = []
    for e in response.value:
        codes.append(
            { 
                "code": e[0],
                "name": e[1]
            }
        )
    return codes


def clear_dtcs(connection):
    response = connection.query(obd.commands.CLEAR_DTC)
    return response.value

def connect_and_watch(device, monitored_name, config):
    connection = obd.Async(device) # auto connect
    for c in connection.supported_commands:
        if c.name in config["codes-to-monitor"]:
            connection.watch(eval(f"obd.commands.{c.name}"), callback=fn_collect(monitored_name, c))
            print(f"+ Added watch for {c.name} from {c.ecu}")
        else:
            print(f"+ Ignored watch for {c.name}")
    # connection.watch(obd.commands.FUEL_RAIL_PRESSURE_DIRECT, callback=collect_FUEL_RAIL_PRESSURE_DIRECT)
    connection.start() # start the async update loop


def fn_collect(monitored_name, code):

    def collect_generic(x):
        #print(rpm)
        #print(f"RPM = [{rpm.value.magnitude}]")
        if not x.is_null():

            try:
                if hasattr(x.value, 'magnitude'):
                  send_data(code.name, { "vehicle": monitored_name, "ecu": code.ecu}, x.value.units, x.value.magnitude)

            except AttributeError:
                print(f"{code.name} has no value.magnitude {type(x.value)} {code}")
            except Exception as e:
                print(f"{code.name} - {str(e)} - failed send of stats - [{code.desc}]")

    return collect_generic

def send_data(name, tags, measure, val): 

  event_ms = int(round(time.time() * 1000))
  tag_str = ",".join(["=".join([k, str(v)]) for k, v in tags.items()])
  data_msg = f"{name},{tag_str} {measure}={val} {event_ms}\n"
  print(data_msg, flush=True, end="")

  udp.sendto(str.encode(data_msg), (socket.gethostbyname("influxdb"), 8089))


def debug_send():
    x = random.randint(0,1000)
    send_data("some_metric", { "foo": 99, "booboo": "ding" }, "testy_ticks", random.randint(0,1000))
    print(f"send. tt {x}", flush=True)

if __name__ == "__main__":
    arguments = docopt(__doc__, version='1.0.2')
    # obd.logger.setLevel(obd.logging.DEBUG)

    device = arguments["--device"]

    if arguments["inspect"]:
        connection = obd.OBD(device) # auto connect
        inspect(connection)
        sys.exit(0)

    if arguments["clear"]:
        connection = obd.OBD(device) # auto connect
        print(clear_dtcs(connection))
        sys.exit(0)

    if arguments["monitor"]:

        #
        # collect the config
        
        try:
            config_yaml = open(arguments["--config"])
            config = yaml.load(config_yaml, Loader=yaml.FullLoader)
        except:
            print("Failed to load the config file [" + arguments["--config"] + "]")
            sys.exit(1)

        #
        # set the name we will use for the stats

        if "name" in config:
            monitored_name = config["name"] # typically the car name
        else:
            monitored_name = "car-" + datetime.now().strftime("%Y-%m-%d-%H%M%S")
        
        #
        # start the API server (from grafan back to the "OBD2 module")

        start_webserver()

        if arguments["--noconnect"]:
            # we won't connect to the car
            print(f"No Monitoring OBD2 monitoring: {monitored_name}", flush=True)
            while True:
                debug_send()
                time.sleep(10)
        else:
            print(f"Monitoring OBD2: {monitored_name}", flush=True)

            connect_and_watch(device, monitored_name, config)

            while True:
                status = conn.status()
                print(f"{device} is {status}", flush=True)

                if status == "Not Connected":
                    connect_and_watch(device, monitored_name,  config)
                
                print("{} is {}".format(device, status), flush=True)
                time.sleep(10)

