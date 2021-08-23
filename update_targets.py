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
# Script name:          update_targets.py
#
# Version:              1.03
#
# Purpose:              This script adds new targets from DBList into the 
#                       DBC Inventory Database. If the targe exists and 
#                       something has changed, then it updates the entry.
#
# Input files:          /u01/app/oracle/DBTools/tnsnames.ora
#
# Output:               Entries into the DBC_Targets tables
#                       Log files to ./logs directory
#
# Syntax:               python update_targets.py
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
# 2021/03/05   M.Pankratz        1.00     Copied from add_targets.py
# 2021/06/10   M.Pankratz        1.01     Move settings to separate file
# 2021/06/17   M.Pankratz        1.02     Refactor and cleanup
# 2021/07/07   M.Pankratz        1.03     make UpdateTarget external
# ============================================================================


# ============================================================================
# Import all the external Python modules that we need
# ============================================================================
from check_os_target import check_os_target
import getopt
import sys
import cx_Oracle
import paramiko           # https://oracle.github.io/python-cx_Oracle/
import psycopg2           # https://pypi.org/project/psycopg2/
import psycopg2.extras    # This gives access to the psycopg2 error messages
import threading          # Allows us to time and kill hung db connections
from Inv_Logging import StartLogging
# from numpy import asarray # convert sql result tuples to python arrays
from datetime import date # for some reason this is not included by default
from datetime import datetime
from decouple import config     # Allows us to read .env
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
LogFile="/home/orac4i/Inventory/src/logs/update_targets_"+str(date.today())+".log"
LogLevel="INFO"
LogName="Update_Targets"
# ============================================================================


# ============================================================================
# Function:    GetTargetDBInfo
# Description: Checks the target database for a single spcific key attribute
# Returns:     The result of the check query
# ============================================================================
def GetTargetDBInfo(target, check, TargetLogger):
    instance, host=target.split('_')
    value=''

    try:
        connection = cx_Oracle.connect(DBC_USER, DBC_PWD, target, encoding="UTF-8")
        timer = threading.Timer(30,connection.cancel)
        db_info_cursor = connection.cursor()
        timer.start()  # start counting right before connecting to the database
        db_info_cursor.execute(check)
        value = db_info_cursor.fetchone()
        value=str(value[0]).strip()
        TargetLogger.debug('Connected to: %s', str(target))

        # All done with the Target Oracle connection
        connection.close()
    
    # Handle all the things that could go wrong with this connection attempt
    except cx_Oracle.DatabaseError as exc:
    # If there was a database error we need the ORA-##### error
    # This might mean the database exists
        error, = exc.args
        oraerr=str(error.code)
        TargetLogger.error('Target: %s   Status: ORA- %s  Message: %s', str(target), oraerr, str(error))

    except Exception as exc:
    # ============================================================================
    # There was a problem that was not database related
    # ============================================================================
        error, = exc.args
        TargetLogger.error('Target: %s   Error: %s', str(target), error)
 
    timer.cancel()  # cancel the timer
  
    return value

# ============================================================================
# END GetTargetDBInfo
# ============================================================================

# ============================================================================
# Function:    GetTargetOSInfo
# Description: Takes a target and an OS check and first obtains the FID and 
#              home_dir for the call to the check_os_target routine
# Returns:     The result of the OS check query
# ============================================================================
def GetTargetOSInfo(InventoryID, target, check, result_column, TargetLogger):
    instance, host=target.split('_')
    value=''
    owner=''
    homedir=''
    QUERY='select owner, homedirectory from dbc_target where inventoryid = ' + str(InventoryID) + '' 
    if InventoryID > 0:

      try:
          postgres_conn = psycopg2.connect(INVENTORYDB)
          select_cursor = postgres_conn.cursor()
  
          # Get just the info about the target for comparison
          select_cursor.execute(QUERY)
          owner, homedir = select_cursor.fetchone()
  
          value=check_os_target(InventoryID, owner, host, homedir, check, result_column, TargetLogger)
    
      except cx_Oracle.DatabaseError as exc:
      # If there was a database error we need the ORA-##### error
          error, = exc.args
          oraerr=str(error.code)
          TargetLogger.error('Target: %s   Status: ORA- %s  Message: %s', str(target), oraerr, str(error))    

    return value

# ============================================================================
# END GetTargetOSInfo
# ============================================================================


# ============================================================================
# Function:    UpdateTargetColumn
# Description: Checks the Inventory database for 1 target and 1 attribute / column
# ============================================================================
def UpdateTargetColumn(inventoryid, column_name, value, TargetLogger):
    result = 'NO CHANGE'
 
    if value != '':
        # ============================================================================
        # Open a connection to the Inventory Database 
        # Update the results if anything has changed about the target (i.e. version or logmode)
        # ============================================================================
            
        postgres_conn = psycopg2.connect(INVENTORYDB)
        select_cursor = postgres_conn.cursor()
        TARGET_QUERY='select ' + column_name + ' from public.DBC_Target where inventoryid = \'' + str(inventoryid) + '\''
        TargetLogger.info('QUERY: %s', TARGET_QUERY)

        try:  
            # Get just the info about the target for comparison
            select_cursor.execute(TARGET_QUERY)
            Curr_Value = select_cursor.fetchone()

            if type(Curr_Value)==type(None) :
              Curr_Value = ''
            else: 
              Curr_Value=str(Curr_Value[0]).strip()

            TargetLogger.info('InventoryID: %s Column: %s Old Value: %s New Value: %s ',\
                                inventoryid, column_name, Curr_Value, value)

        except (psycopg2.DataError, psycopg2.DatabaseError, psycopg2.IntegrityError, psycopg2.InternalError) as exc:
            error, = exc.args
            errormsg = psycopg2.errors.lookup(exc.pgcode)
            TargetLogger.error('Failed to get %s from InventoryID: %s  DataError: %s', \
                                column_name, str(inventoryid), str(errormsg))

        if Curr_Value == value:
            TargetLogger.info('No change in Target Info')
        else:
            insert_cursor = postgres_conn.cursor()
            INSERT_STMT='UPDATE public.dbc_target set '+column_name+'= \''+ value + '\'where inventoryid = \'' + str(inventoryid) + '\''
             
            try:
                insert_cursor.execute(INSERT_STMT)
                # Make the changes to the database persistent
                postgres_conn.commit()

            except (psycopg2.DatabaseError, psycopg2.IntegrityError, psycopg2.DataError, psycopg2.InternalError)   as exc:
                error, = exc.args
                TargetLogger.error('Error updating target: %s Column_name %s from %s to %s', \
                                    inventoryid, column_name, Curr_Value, value )
                result='UPDATE FAILED'
         
            except Exception as exc:
                error, = exc.args
                TargetLogger.error('Error updating target: %s Column_name: %s Error:  %s ', \
                                    inventoryid, column_name, str(error))
                result='UPDATE FAILED'

            else:
                result='TARGET UPDATED'

        postgres_conn.close()

    return result

def UpdateTarget(InventoryID, host, instance, TargetLogger):
  TargetLogger.debug("Update Target: InventoryID: %s Host: %s Instance: %s", InventoryID, host, instance)

  postgres_conn = psycopg2.connect(INVENTORYDB)
  target_cursor = postgres_conn.cursor()

  # Get ALL the checks to perform on these targets
  CHECKQUERY="select check_command, check_type, result_column from public.checklist where frequency='TARGET' order by priority"
  target_cursor.execute(CHECKQUERY)
  all_checks = target_cursor.fetchall()
  TargetLogger.debug("All Checks: %s" , all_checks)
  
  TargetLogger.info("Updating Host: %s Instance: %s", host, instance)
  # Try connecting to the database and get info if possible
  for check, check_type, result_column in all_checks:
      value=''
      if check_type == 'DB':
          # if (VENDOR == 'ORACLE') or (VENDOR == '%') :
             if "+ASM" not in instance:
                 value=GetTargetDBInfo(instance+'_'+host, check, TargetLogger)
      elif check_type == 'OS':
          value=GetTargetOSInfo(InventoryID, instance+'_'+host, check, result_column, TargetLogger)

      UpdateTargetColumn(InventoryID, result_column, value, TargetLogger )

    # Lastly Update the Last Updated Column
  UpdateTargetColumn(InventoryID, "lastcheckdate", str(datetime.now()), TargetLogger)

  return

# ============================================================================
# ============================================================================
# ---------------------------   MAIN PROGRAM   -------------------------------
# ============================================================================
# ============================================================================
def main(argv):
  TargetLogger=StartLogging(LogLevel, LogFile, LogName)    # Log to File 
  
  global VENDOR
  global FREQUENCY
  global CHECKTYPE
  VENDOR = '%'
  CHECKTYPE = '%'
  
  CHECKQUERY="select check_command, check_type, result_column from public.checklist where frequency='TARGET'"
  
  try:
      opts, args = getopt.getopt(sys.argv,"h:v:t")
      
  except getopt.GetoptError:
      print ('check_targets.py [ -t <type> ] -v <vendor> -f <frequency> ')
      sys.exit(2)
      
  for opt, arg in opts:
      if opt == '-h':
          print ('check_targets.py [ -t <type> ] -v <vendor> -f <frequency> ')
          sys.exit()
  
      elif opt in ("-t"):
          CHECKTYPE = arg
          CHECKQUERY += ' and check_type = \'' + CHECKTYPE + '\''
  
      elif opt in ("-v"):
          VENDOR = arg
          CHECKQUERY += ' and vendor = \'' + VENDOR + '\''
          
  CHECKQUERY += ' order by priority'
  # ============================================================================
  # Fetch all the active database targets from the InventoryDB and
  # check each one database by database
  # Attempt to query that target and update the target if needed 
  # ============================================================================
  # Connect to the Inventory DB
  
  postgres_conn = psycopg2.connect(INVENTORYDB)
  target_cursor = postgres_conn.cursor()
  
  # Get ALL the active targets
  target_cursor.execute("""
      select inventoryid, hostname, instancename, container
      from public.dbc_target
      where decommissioned is null
      and inventoryid < 25
      order by inventoryid """)
  targets = target_cursor.fetchall()
  
  # Get ALL the checks to perform on these targets     
  target_cursor.execute(CHECKQUERY)
  all_checks = target_cursor.fetchall()
  TargetLogger.debug("All Checks: %s" , all_checks)
  
  for InventoryID, HostName, InstanceName, Container in targets:
      if HostName.find(".") > 0:
          HostName=HostName[0:HostName.find(".")]
  
      Target = InstanceName + "_" + HostName
  
      TargetLogger.info("Updating target: %s", Target)
      # Try connecting to the database and get info if possible
      for check, check_type, result_column in all_checks:
          value=''
          if check_type == 'DB':
              if (VENDOR == 'ORACLE') or (VENDOR == '%') :
                 if "+ASM" not in Target:
                     value=GetTargetDBInfo(Target, check)
          elif check_type == 'OS':
              value=GetTargetOSInfo(InventoryID, Target, check, result_column, TargetLogger)
  
          # TargetLogger.debug("Target: %s Check: %s Column: %s Value:" , str(Target), str(check), str(result_column), str(value))
          UpdateTargetColumn(InventoryID, result_column, value , TargetLogger)
      # Lastly Update the Last Updated Column
      UpdateTargetColumn(InventoryID, "lastcheckdate", str(datetime.now()), TargetLogger)
  
# ============================================================================
# END main program
# ============================================================================

if __name__ == "__main__":
  main(sys.argv[1:])

