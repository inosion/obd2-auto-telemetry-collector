import obd
obd.logger.setLevel(obd.logging.DEBUG)

connection = obd.OBD() # auto connect

# OR

connection = obd.OBD("/dev/ttyUSB0") # create connection with USB 0

# OR

ports = obd.scan_serial()      # return list of valid USB or RF ports

print (ports ) 
