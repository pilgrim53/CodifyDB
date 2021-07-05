#!/home/orac4i/Inventory/bin/python
#  -*- coding: utf-8
# ============================================================================
# Copyright (c) 2020 Bell Canada
#
# All rights reserved. No part of this script may be copied or translated
# in any form or by any means without prior written permission from BELL.
#
# DO NOT MODIFY THIS SCRIPT LOCALLY
# This script is part of the DBC DBTools.  Do not make
# modifications to local copies.
# ============================================================================
# Description
# ============================================================================
#
# Script name:          scan_target.py
#
# Version:              1.00
#
# Purpose:              This script adds new targets from the AddToDBList.txt 
#                       file into the DBC Inventory Database.
#
# Input files:          /u01/app/oracle/DBTools/AddToDBList.txt
#
# Output:               Successful Adds are Entries in DBC_Target
#                       Failed attemps are written to dbc_target_rejects
#                       Log files written to ./logs directory
#
# Syntax:               scan_target.py instancename_hostname
#
# Called Routines:      cx_Oracle - for Oracle database calls
#                       psycopg2 - for PostgreSQL database calls
#                       date, grep, awk, cat, uname - misc UNIX commands
#
# Return Codes:         0=success  otherwise TNS Error value
#
# Restrictions:         You must first run "source ~/Inventory/bin/activate
#                       to enter the necessary Python virtual environment
#
# Abend instructions:   Resolve and rerun
#
# ============================================================================
# History of Changes
# ============================================================================
# Date         Person            Version  Comments
# 2021/06/17   M.Pankratz        1.00     Copied from update_targets.py
# ============================================================================


# ============================================================================
# Import all the external Python modules that we need
# ============================================================================
import paramiko           # Allows us to ssh to the target hosts
import cx_Oracle          # https://oracle.github.io/python-cx_Oracle/
import psycopg2           # https://pypi.org/project/psycopg2/
import psycopg2.extras    # This gives access to the psycopg2 error messages
import sys                # for some reason this is not included by default
import logging            # https://docs.python.org/3/library/logging.html
import threading          # Allows us to time and kill hung db connections
# from numpy import asarray # convert sql result tuples to python arrays
from datetime import date # for some reason this is not included by default
from decouple  import config     # Allows us to read .env
# from update_targets import check_os # Allows us to reuse the os check function
import socket
import subprocess
import os
# ============================================================================

# ============================================================================
# Set DBTools Environment and Global Variables
# ============================================================================
DBC_USER = config('DBC_USER')
DBC_PWD  = config('DBC_PWD')
INV_USER = config('INV_USER')
INV_PWD  = config('INV_PWD')
INVENTORYDB = "dbname=testdb user="+INV_USER+" password="+INV_PWD+" host=caddld-498.belldev.dev.bce.ca"
ORACLE_HOME="/u01/app/oracle/product/12.2.0.1"
TNS_ADMIN="/u01/app/oracle/DBTools/"
target_file="/u01/app/oracle/DBTools/AddToDBList.txt"
Log_File="/home/orac4i/Inventory/src/logs/scan_targets_"+str(date.today())+".log"
LogLevel="DEBUG"
# ============================================================================

# ============================================================================
# Define Functions
# ============================================================================

def StartLogging(LogLevel, Log_File):
    logging.basicConfig(filename=Log_File, level=logging.DEBUG)
    logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
    TargetLogger=logging.getLogger('Target_Scanner')
    TargetLogger.setLevel(logging.DEBUG)

    # Create a console handler
    ch = logging.StreamHandler()
    #ch.setLevel(logging.LogLevel)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    TargetLogger.addHandler(ch)

    return TargetLogger
    # End StartLogging

# ============================================================================
# Function:    ScanTarget
# Description: Checks the Inventory database and retuns the result
# Input:       Takes target in the format of host_instance
# Ouptut:      Returns the target info
#              [instance,host,DBCreateDate,DBID,version,logMode,status]
# ============================================================================
def ScanTarget(target):
  # Set some initial values each time we do a check
  TargetRow=[]     # create an empty array to start
  instance, host=target.split('_')

  if "+ASM" in target:
     TargetLogger.info('ASM Instance found: %s', str(TargetRow))
     print ("Ignoring ASM Instance")
  else:
    ping_result=os.system("ping " + host + " -4 -c 4")

    if ping_result == 0 :
      TargetLogger.info('Host: %s is pingable.', host)
      for PORT in range(1521, 2390): 
        TargetLogger.info('checking Port: %s', PORT)
        try:
          sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
          result = sock.connect_ex((host, PORT))
          # result = sock.connect_ex((remoteServerIP, port))
          if result == 0:
            TargetLogger.info('OPEN Port: %s', PORT)

            dsn = cx_Oracle.makedsn(host, PORT, service_name=instance)
            connection = cx_Oracle.connect(DBC_USER, DBC_PWD, dsn=dsn, encoding="UTF-8")
            timer = threading.Timer(5,connection.cancel)
            timer.start()  # start counting right before connecting to the database
            TargetLogger.info('Connection: %s', connection)
            db_info_cursor = connection.cursor()
            TargetLogger.info('Connection: %s', TargetLogger)
        #    try:
           # db_info_cursor.execute("select 'CONNECTED' from dual")
           # pingResult = db_info_cursor.fetchone()
           # TargetLogger.info('DB Connection returned: %s', pingResult)
            timer.cancel()  # cancel the timer
            connection.close()

        # Handle all the things that could go wrong with this connection attempt
        except cx_Oracle.DatabaseError as exc:
        # If there was a database error we need the ORA-##### error
        # This might mean the database exists
                    error, = exc.args
                    oraerr=str(error.code)
                    NotExist=['12545','12541','12543','12514','12505']
                    if oraerr in NotExist :
                        TargetLogger.error('Target: %s   Status: ORA- %s  Message: %s', str(target), oraerr, str(error))
                        TargetLogger.error('TNS Error: Target DB not added to inventory. Correct the issue or remove from DBList')
                        TargetRow = 'NONE'
                    else:
                        TargetLogger.warning('Target: %s   Status: ORA- %s  Message: %s', str(target), oraerr, str(error))
                        # We can add this target to inventory even though we can't log in
                        TargetLogger.info('Target %s exists, but couldn''t log in. Setting blank initial values.', str(target))
                        TargetRow = (str(instance).upper(),str(host).upper(),"1900-01-01",'','Unknown','',oraerr,'','','','','ORACLE',0,'','')
            
        except Exception as exc:
        # ============================================================================
        # There was a problem that was not database related
        # ============================================================================
                    error, = exc.args
                    TargetLogger.error('Target: %s   Error: %s', str(target), error)
                    TargetLogger.error('Target DB not added to inventory. Correct the issue or remove from DBList')             
              
              
              

        except KeyboardInterrupt:
            print ("You pressed Ctrl+C")
            sys.exit()
        
        except socket.gaierror:
            print ("Hostname could not be resolved. Exiting")
            sys.exit()
        
        except socket.error:
            print ("Couldn't connect to server")
            sys.exit()
            
        sock.close()

    else:
      TargetLogger.info('Host %s not pingable. Please check.', target)
      
      
  return TargetRow
# ============================================================================
# END ScanTarget
# ============================================================================

def countdown():
        global timeout
        time.sleep(30)
        timeout = True

# ============================================================================
# ============================================================================
# ---------------------------   MAIN PROGRAM   -------------------------------
# ============================================================================
# ============================================================================


TargetLogger=StartLogging(LogLevel, Log_File)  # Log to File 

# ============================================================================
# Read through the AddToDBList.txt file database by database
# Attempt to query that target and record the results
# ============================================================================
with open(target_file) as tf:
  for target in tf:
    target=target.strip()
    TargetLogger.info('Checking target: %s', str(target))
   
    # Try connecting to the database and get info if possible
    TargetInfo=ScanTarget(target)

    TargetLogger.info('Target %s results: %s ', str(target), TargetInfo)

