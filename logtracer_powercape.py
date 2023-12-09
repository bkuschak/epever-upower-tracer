#!/usr/bin/python3

import sys
import datetime
import time
import minimalmodbus
import os
import serial
from SolarTracer import *

# InfluxDB v1
influxdb_host = '192.168.2.154'
influxdb_port = 8086
influxdb_name = 'mydb'
influxdb_table = 'solar'

# Create the serial device manually so we can issue the RS485 ioctl to configure the RTS# signal correctly.
ser = serial.Serial('/dev/ttyS5')

up = SolarTracer(device='/dev/ttyS5')
#up = SolarTracer(device=ser)
if (up.connect() < 0):
	print ("Could not connect to the device")
	exit -2

# get timestamps
timestamp = datetime.datetime.utcnow()

FloatNo = 0.0

# TODO error handling.  Code returns -2 on IOError.

PVvolt = up.readReg(PVvolt) + FloatNo
PVamps = up.readReg(PVamps) + FloatNo
PVwatt = round(PVvolt * PVamps, 2)
PVkwhTotal = up.readReg(PVkwhTotal);
PVkwhToday = up.readReg(PVkwhToday);

BAvolt = up.readReg(BAvolt) + FloatNo
BAamps = up.readReg(BAamps) + FloatNo
BAwatt = round(BAvolt * BAamps, 2)
BAperc = up.readReg(BAperc) * 100
BAtemp = up.readReg(BAtemp)

ControllerTemp = up.readReg(ControllerTemp)

DCvolt = up.readReg(DCvolt) + FloatNo
DCamps = round(up.readReg(DCamps), 2) + FloatNo
DCwatt = round(DCvolt * DCamps, 2) + FloatNo
DCkwhTotal = up.readReg(DCkwhTotal)
DCkwhToday = up.readReg(DCkwhToday)

## form a data record
#body_solar = [
#    {
#        "t": timestamp,
#        "d": {
#            # Solar panel
#            "PVV": PVvolt,
#            "PVI": PVamps,
#            "PVW": PVwatt,
#            "PVKWh": PVkwhTotal,
#            "PVKWh24": PVkwhToday,
#            # Battery
#            "BV": BAvolt,
#            "BI": BAamps,
#            "BW": BAwatt,
#            "BSOC": BAperc,
#            "BTEMP": BAtemp,
#            "CTEMP": ControllerTemp,
#            # Load
#            "LV": DCvolt,
#            "LI": DCamps,
#            "LW": DCwatt,
#            "LKWh": DCkwhTotal,
#            "LKWh24": DCkwhToday
#        }
#    }
#]
#print (body_solar)

# print csv format
print('%.3f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f' %
        (timestamp.timestamp(),
        PVvolt, PVamps, PVwatt, PVkwhTotal, PVkwhToday,
        DCvolt, DCamps, DCwatt, DCkwhTotal, DCkwhToday,
        BAvolt, BAamps, BAwatt, BAperc, BAtemp, ControllerTemp))

# send to influxdb, for example:
# curl -i -XPOST 'http://192.168.2.154:8086/write?db=mydb' --data-binary 'cpu_load_short,host=server02,region=us-west value=2.64'
msg =   "%s," \
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
        "value=0 %d" % \
        (influxdb_table, \
         PVvolt, PVamps, PVwatt, PVkwhTotal, PVkwhToday, \
         DCvolt, DCamps, DCwatt, DCkwhTotal, DCkwhToday, \
         BAvolt, BAamps, BAwatt, BAperc, BAtemp, ControllerTemp, \
         int(timestamp.timestamp()*1e9))
#cmd = "curl -i -XPOST 'http://192.168.2.154:8086/write?db=mydb' --data-binary '%s'" % (msg)
cmd = "curl -i -XPOST 'http://%s:%d/write?db=%s' --data-binary '%s'" % \
        (influxdb_host, influxdb_port, influxdb_name, msg)
print(cmd)
os.system(cmd)

