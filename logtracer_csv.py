#!/usr/bin/python3

import array
import datetime
import fcntl
import getopt
import minimalmodbus
import os
import sys
import time
from SolarTracer import *

# Defaults
#serial_port = '/dev/ttyXRUSB1'
#native_rs485 = False
serial_port = '/dev/ttyS5'
native_rs485 = True
write_to_db = False
csv_format = False

# InfluxDB v1
influxdb_host = '192.168.2.154'
influxdb_port = 8086
influxdb_name = 'mydb'
influxdb_meas_name = 'solar'
influxdb_tag_station = 'gblco'

# Print to stdout unless the user specifies a file name.
log_filename = None

def usage(argv):
    print(  "Usage: %s [-N] [-p <port>] [-f <filename>]\n"
            " -p <port>       Use serial port. Ex: /dev/ttyS5\n"
            " -N              Configure native RS485 settings for serial port.\n"
            " -c              Output CSV format.\n"
            " -d              Write to InfluxDB database.\n"
            " -f <filename>   Append output to a file.\n" % argv)
    sys.exit()

argv = sys.argv[1:]
opts, args = getopt.getopt(argv, "hcdp:f:N")
for opt, arg in opts:
    if opt in ['-p']:
        serial_port = arg
    elif opt in ['-c']:
        csv_format = True
    elif opt in ['-d']:
        write_to_db = True
    elif opt in ['-f']:
        log_filename = arg
    elif opt in ['-N']:
        native_rs485 = True
    elif opt in ['-h']:
        usage(sys.argv[0])
    else:
        usage(sys.argv[0])

if native_rs485:
    # minimalmodbus < 2.1 does not support initializing device with an RS485 pySerial object. 
    # As a workaround, use this method below.  Set native RS485 mode in the driver.
    # The driver seems to remember these settings even after the file is closed.
    # Then later when minimalmodbus opens the port, these RS485 settings remain in
    # effect.
    # Adpated from https://github.com/pyserial/pyserial/blob/master/serial/serialposix.py#L171
    TIOCSRS485 = 0x542F
    SER_RS485_ENABLED = 0b00000001
    SER_RS485_RTS_ON_SEND = 0b00000010
    SER_RS485_RTS_AFTER_SEND = 0b00000100
    SER_RS485_RX_DURING_TX = 0b00010000
    buf = array.array('i', [0] * 8)  # flags, delaytx, delayrx, padding
    # RTS# seems to be inverted.
    buf[0] |= SER_RS485_ENABLED
    buf[0] &= ~SER_RS485_RTS_ON_SEND
    buf[0] |= SER_RS485_RTS_AFTER_SEND
    with open(serial_port, 'w') as fd:
        fcntl.ioctl(fd, TIOCSRS485, buf)

# Open the EPEVER.
up = SolarTracer(device=serial_port)
if (up.connect() < 0):
	print ("Could not connect to the device")
	exit -2

# get timestamps
timestamp = datetime.datetime.utcnow()

# TODO error handling.  Code returns -2 on IOError.

PVvolt = float(up.readReg(PVvolt))
PVamps = float(up.readReg(PVamps))
PVwatt = round(PVvolt * PVamps, 3)
PVkwhTotal = float(up.readReg(PVkwhTotal));
PVkwhToday = float(up.readReg(PVkwhToday));

BAvolt = float(up.readReg(BAvolt))
#BAamps = float(up.readReg(BAamps))
BAamps = float(up.readReg32(BAampsnetL)) / 256 # Use bipolar battery current instead
BAwatt = round(BAvolt * BAamps, 3)
BAperc = float(up.readReg(BAperc)) * 100
BAtemp = float(up.readReg(BAtemp))

ControllerTemp = float(up.readReg(ControllerTemp))

DCvolt = float(up.readReg(DCvolt))
DCamps = round(float(up.readReg(DCamps)), 3)
DCwatt = round(DCvolt * DCamps, 3)
DCkwhTotal = float(up.readReg(DCkwhTotal))
DCkwhToday = float(up.readReg(DCkwhToday))

data_timestamp = timestamp.timestamp()

if csv_format:
    # output csv format
    output = ('%.3f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f' %
            (timestamp.timestamp(),
            PVvolt, PVamps, PVwatt, PVkwhTotal, PVkwhToday,
            DCvolt, DCamps, DCwatt, DCkwhTotal, DCkwhToday,
            BAvolt, BAamps, BAwatt, BAperc, BAtemp, ControllerTemp))

    if log_filename:
        print(output, file=open(log_filename, 'a'))
    else:
        print(output)

if write_to_db:
    # send to influxdb, for example:
    # curl -i -XPOST 'http://192.168.2.154:8086/write?db=mydb' --data-binary 'cpu_load_short,host=server02,region=us-west value=2.64'
    msg =   "%s," \
            "station=%s " \
            "pv_v=%.2f," \
            "pv_i=%.2f," \
            "pv_w=%.2f," \
            "pv_kwh_total=%.2f," \
            "pv_kwh_today=%.2f," \
            "ld_v=%.2f," \
            "ld_i=%.2f," \
            "ld_w=%.2f," \
            "ld_kwh_total=%.2f," \
            "ld_kwh_today=%.2f," \
            "ba_v=%.2f," \
            "ba_i=%.2f," \
            "ba_w=%.2f," \
            "ba_soc=%.2f," \
            "ba_temp=%.2f," \
            "ctrl_temp=%.2f " \
            "%d" % \
            (influxdb_meas_name, influxdb_tag_station, \
             PVvolt, PVamps, PVwatt, PVkwhTotal, PVkwhToday, \
             DCvolt, DCamps, DCwatt, DCkwhTotal, DCkwhToday, \
             BAvolt, BAamps, BAwatt, BAperc, BAtemp, ControllerTemp, \
             int(data_timestamp*1e9))
    cmd = "curl -s -i -XPOST 'http://%s:%d/write?db=%s' --data-binary '%s'" % \
            (influxdb_host, influxdb_port, influxdb_name, msg)
    os.system(cmd)
