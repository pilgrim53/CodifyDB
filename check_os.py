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
# Script name:          check_os.py
#
# Version:              1.00
#
# Purpose:              This script checks to see if a particular target
#                       is registered in the non-prod Patch repository
#
# Input files:          DBC_TARGET  Table
#
# Output:               DBC_TARGET.in_sqlpatch 
#                       Log files to ./logs directory
#
# Syntax:               check_os.py
#
# Called Routines:      cx_Oracle - for Oracle database calls
#                       psycopg2 - for PostgreSQL database calls
#                       date, grep, awk, cat, uname - misc UNIX commands
#
# Return Codes:
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
# 2021/03/29   M.Pankratz        1.00     Created
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
# ============================================================================

# ============================================================================
# Set DBTools Environment and Global Variables
# ============================================================================
ORACLE_HOME="/u01/app/oracle/product/12.2.0.1"
TNS_ADMIN="/u01/app/oracle/DBTools/"
Log_File="/home/orac4i/Inventory/src/logs/check_os_"+str(date.today())+".log"
LogLevel="DEBUG"
# ============================================================================

# ============================================================================
# Define Functions
# ============================================================================

def StartLogging(LogLevel, Log_File):
    logging.basicConfig(filename=Log_File, level=logging.DEBUG)
    logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
    TargetLogger=logging.getLogger('Check_OS')
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
# Logging examples
# ============================================================================
# logging.debug('This should go to the log file.')
# logging.info('So should this')
# logging.warning('And this, too')
# logging.error('And non-ASCII stuff, too, like Øresund and Malmö')
# ============================================================================

# ============================================================================
# Function:    GetOSType
# Description: Checks the host to get the OS of the requested target.
# Input:       Takes target in the format of host_instance
# Ouptut:      Returns a "Y/N" result 
# ============================================================================
def GetOSType(host, owner):

  OSType="Unknown"
  command="uname -rs"
  ssh1 = paramiko.SSHClient()
  ssh1.load_system_host_keys()
  ssh1.set_missing_host_key_policy(paramiko.AutoAddPolicy())

  TargetLogger.info("Connecting to %s as %s to run %s ", host, owner, command)

  timer1 = threading.Timer(10,ssh1.close)
  timer1.start()  # start counting right before connecting to the database

  try:
      ssh1.connect(host, 22, owner)
      stdin, stdout, stderr = ssh1.exec_command(command)
      OSTypeRow = stdout.readlines()
      TargetLogger.debug("Result: %s ", OSTypeRow)
      OSType=str(OSTypeRow[0]).strip()
      timer1.cancel()  # cancel the connection thread if it's still alive after 30 seconds

  except Exception as exc:
      TargetLogger.error("Error connecting to check host type: %s", host)

  finally:
      ssh1.close()

  return OSType
 
# ============================================================================
# END CheckOS
# ============================================================================

# ============================================================================
# ============================================================================
# ---------------------------   MAIN PROGRAM   -------------------------------
# ============================================================================
# ============================================================================

if __name__ == '__main__':

  TargetLogger=StartLogging(LogLevel, Log_File)  # Log to File

  # ============================================================================
  # Fetch all the valid database targets from the InventoryDB and
  # check each one database by database
  # Attempt to query that target and record the results
  # ============================================================================
  
  # Connect to the Inventory DB
  
  postgres_conn = psycopg2.connect(database="testdb", user = "postgres", password = "sys4Bell", host = "caddld-498.belldev.dev.bce.ca", port = "5432")
  target_cursor = postgres_conn.cursor()
  
  # Get ALL the active targets
  target_cursor.execute("""
      select inventoryid, hostname, owner
        from public.dbc_target
       where decommissioned is null """)
  targets = target_cursor.fetchall()
  
  for inventoryid, hostname,owner in targets:
     OSType=GetOSType(hostname,owner)
  
     #update_conn = psycopg2.connect(database="testdb", user = "postgres", password = "sys4Bell", host = "caddld-498.belldev.dev.bce.ca", port = "5432")
     update_cursor = postgres_conn.cursor()
  
     try:
         update_cursor.execute("""
         UPDATE public.dbc_target
            set os=%s
          WHERE inventoryid=%s """, ( str(OSType), str(inventoryid)))
  
         # Make the changes to the database persistent
         TargetLogger.info("InventoryID %s Updated to %s.", inventoryid, OSType)
         postgres_conn.commit()
         update_cursor.close()
     except:
         TargetLogger.error("Error setting OS Type for InventoryID %s to Patch %s ", str(inventoryid), str(OSType))
         a=1
      
     
  postgres_conn.close()
