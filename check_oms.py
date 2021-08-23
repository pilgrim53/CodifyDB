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
# Script name:          check_oms.py
#
# Version:              1.01
#
# Purpose:              This script checks to see if a particular target
#                       is registered in the non-prod OMS repository
#
# Input files:          DBC_TARGET  Table
#
# Output:               DBC_TARGET.in_oms 
#                       Log files to ./logs directory
#
# Syntax:               check_oms.py
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
# 2021/02/15   M.Pankratz        1.00     Created
# 2021/06/10   M.Pankratz        1.01     Move settings to separate file
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
# from numpy import asarray  # convert sql result tuples to python arrays
from datetime import date    # for some reason this is not included by default
from decouple import config  # Allows us to read .env
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
Log_File="/home/orac4i/Inventory/src/logs/check_oms_"+str(date.today())+".log"
LogLevel="INFO"
# ============================================================================

# ============================================================================
# Define Functions
# ============================================================================

def StartLogging(LogLevel, Log_File):
    logging.basicConfig(filename=Log_File, level=logging.DEBUG)
    logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
    TargetLogger=logging.getLogger('Check_OMS')
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
# Function:    CheckOMS
# Description: Checks the DBC NonProd OMS Repository to see if it contains
#              The requested target.
# Input:       Takes target in the format of host_instance and checkstring
# Ouptut:      Returns a "Y/N" result 
# ============================================================================
def CheckOMS(target, checkstring, TargetLogger):
  # Set some initial values each time we do a check
  In_OMS='N'  # Set to False until we determine if it's True

  if "+ASM" in target:
     # TargetLogger.info('ASM Instance found: %s', str(target))
     a=1
     # Build connection to
     # return NewTarget, TargetRow
  else:
    instance, host=target.split('_')
    TargetLogger.debug('Target: %s  Host: %s  Instance: %s |', str(target), host, instance )
    connection = cx_Oracle.connect(DBC_USER, DBC_PWD, 'DVOMS_caddld-593', encoding="UTF-8")
    query = f"{checkstring.format(host, instance)}" 
    TargetLogger.debug('SQL: %s', query)
    timer = threading.Timer(10,connection.cancel)

    try:
      db_info_cursor = connection.cursor()
      timer.start()  # start counting right before connecting to the database
      db_info_cursor.execute(query)

      In_OMS = db_info_cursor.fetchone() 
      # TargetLogger.info('Target: %s  in OMS = %s', str(target), In_OMS )
      timer.cancel()  # cancel the connection thread if it's still alive 

    except (OSError, ValueError, RuntimeError, TypeError, NameError) as exc:
      error, = exc.args
      # TargetLogger.error("Error:  %s ", error)

    except cx_Oracle.DatabaseError as exc:
      error, = exc.args
      # TargetLogger.error("DatabaseError-Code:  %s %s ", error.code, error.message, str(host), str(instance))

    except :
      # TargetLogger.error('Failed to check OMS:  %s ', str(target))
      In_OMS=('U')


    connection.close()
               

  return In_OMS[0]
# ============================================================================
# END CheckOMS
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
  
  postgres_conn = psycopg2.connect(INVENTORYDB)
  target_cursor = postgres_conn.cursor()
  
  # Get ALL the active targets
  target_cursor.execute("""
      select inventoryid, instancename, owner, homedirectory, hostname
        from public.dbc_target
       where decommissioned is null
      order by inventoryid """)
  targets = target_cursor.fetchall()

  # Get the check query
  target_cursor.execute("""
      select check_command from public.checklist
       where check_type = 'OMS' 
    order by priority """)
  checkstring = target_cursor.fetchone()


  
  for InventoryID, instancename, owner, homedirectory, hostname in targets:
     target=instancename + '_' + hostname
     in_oms=CheckOMS(target, checkstring[0], TargetLogger)
  
     update_cursor = postgres_conn.cursor()
  
     try:
         update_cursor.execute("""
         UPDATE public.dbc_target
            set in_oms=%s
          WHERE InventoryID=%s """, ( str(in_oms), str(InventoryID)))
  
         # Make the changes to the database persistent
         TargetLogger.info("InventoryID %s Updated to %s.", InventoryID, in_oms)
         postgres_conn.commit()
         update_cursor.close()
     except:
         TargetLogger.error("Error setting OMS flag for InventoryID %s to In_OMS %s ", str(InventoryID), str(in_oms))
         a=1
      
     
  postgres_conn.close()
