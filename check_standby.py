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
# Script name:          check_standby.py
#
# Version:              1.01
#
# Purpose:              This script checks to see if a particular target
#                       is registered in the non-prod OMS repository
#
# Input files:          DBC_TARGET  Table
#
# Output:               DBC_TARGET.StandbyDest 
#                       Log files to ./logs directory
#
# Syntax:               check_standy.py
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
# from numpy import asarray # convert sql result tuples to python arrays
from datetime import date # for some reason this is not included by default
from decouple  import config     # Allows us to read .env
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
Log_File="/home/orac4i/Inventory/src/logs/check_standy_"+str(date.today())+".log"
LogLevel="INFO"
# ============================================================================

# ============================================================================
# Define Functions
# ============================================================================

def StartLogging(LogLevel, Log_File):
    logging.basicConfig(filename=Log_File, level=logging.DEBUG)
    logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
    TargetLogger=logging.getLogger('Target_Update')
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
# Function:    CheckStandby
# Description: Checks the targets to see if it has a standby destination
# Input:       Takes target in the format of host_instance
# Ouptut:      Returns the string for the standbydestination
# ============================================================================
def CheckStandby(target):
  # Set some initial values each time we do a check
  StandbyDest='NONE'  # Set to False until we determine if it's True

  if "+ASM" in target:
     # TargetLogger.info('ASM Instance found: %s', str(target))
     a=1
     # Build connection to
     # return NewTarget, TargetRow
  else:
    instance, host=target.split('_')
    # TargetLogger.debug('Target: %s  Host: %s  Instance: %s |', str(target), host, instance )


    try:
      connection = cx_Oracle.connect(DBC_USER, DBC_PWD, target, encoding="UTF-8")
      query = "select distinct * from (   \
             select i.instance_name, i.host_name,    \
                    d.open_mode, d.database_role,   \
                    case when (select count(*) from v$archive_dest where target='STANDBY') = 0    \
                          and d.database_role = 'PRIMARY'   \
                         then 'Stand alone'   \
                         when d.database_role like '%STANDBY%'   \
                         then (select 'Primary: '||destination from v$archive_dest where target='REMOTE')    \
                         else a.target||': '||a.destination   \
                         end as Destination_Name,   \
                    case when (select count(*) from v$archive_dest where target in ('STANDBY','REMOTE')) = 0 then null   \
                         else a.status   \
                         end as Status,   \
                    case when (select count(*) from v$archive_dest  where target in ('STANDBY','REMOTE')) = 0 then null   \
                         else a.schedule   \
                         end as Schedule        \
             from v$instance i, v$database d, v$archive_dest a   \
             where a.target in ('STANDBY','REMOTE')   \
                or d.database_role='PRIMARY')   \
             where Destination_Name like 'STANDBY%'   \
                or Destination_Name='Stand alone'   \
                or Destination_Name like 'Primary%' "

      # TargetLogger.debug('SQL: %s', query)
      timer = threading.Timer(30,connection.cancel)

      db_info_cursor = connection.cursor()
      timer.start()  # start counting right before connecting to the database
      db_info_cursor.execute(query)

      StandbyDest = db_info_cursor.fetchone() 
      TargetLogger.info('Target: %s  StandbyDest = %s', str(target), str(StandbyDest) )
      timer.cancel()  # cancel the connection thread if it's still alive 

    except (OSError, ValueError, RuntimeError, TypeError, NameError) as exc:
      error, = exc.args
      TargetLogger.error("Error:  %s ", error)
      pass

    except cx_Oracle.DatabaseError as exc:
      error, = exc.args
      TargetLogger.error("DatabaseError-Code:  %s %s ", error.code, error.message, str(host), str(instance))
      pass

    except :
      TargetLogger.error('Failed to check OMS:  %s ', str(target))
      StandbyDest=('Check Failed')
    
    else:
      connection.close()
               

  return str(StandbyDest)
# ============================================================================
# END CheckStandby
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
         and status = 'OPEN'
      order by inventoryid """)
  targets = target_cursor.fetchall()
  
  for InventoryID, instancename, owner, homedirectory, hostname in targets:
     target=instancename + '_' + hostname
     StandbyDest=CheckStandby(target)
     update_cursor = postgres_conn.cursor()
  
     try:
         update_cursor.execute("""
         UPDATE public.dbc_target
            set standbydest=%s
          WHERE InventoryID=%s """, ( str(StandbyDest), str(InventoryID)))
  
         # Make the changes to the database persistent
         # # TargetLogger.info("InventoryID %s Updated to %s.", InventoryID, StandbyDest)
         postgres_conn.commit()
         update_cursor.close()

     except (psycopg2.DataError) as exc:
            errormsg = psycopg2.errors.lookup(exc.pgcode)
            TargetLogger.error('Target: %s  DataError: %s', str(target), str(errormsg))
            pass

     except (psycopg2.DatabaseError, psycopg2.IntegrityError, psycopg2.InternalError)   as exc:
            error, = exc.args
            TargetLogger.error('Target: %s  Message: %s', str(target),  str(error))
            pass


     except Exception as exc:
            error, = exc.args
            TargetLogger.error('Postgres Exception on target: %s  Message: %s', str(target),  str(error))

     
  postgres_conn.close()
