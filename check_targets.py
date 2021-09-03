#!/home/orac4i/Inventory/bin/python
#    -*- coding: utf-8
# ============================================================================
# Copyright (c) 2020 Bell Canada
#
# All rights reserved. No part of this script may be copied or translated
# in any form or by any means without prior written permission from BELL.
#
# DO NOT MODIFY THIS SCRIPT LOCALLY
# This script is part of the DBC DBTools.    Do not make
# modifications to local copies.
# ============================================================================
# Description
# ============================================================================
#
# Script name:        check_targets.py
#
# Version:            1.03
#
# Purpose:            This script monitors database targets from the
#                     DBC Inventory Database. If the target exists and
#                     something has changed, then it updates the entry.
#
# Input files:        DBC_TARGETS Table
#                     checklist table
#                     $TNS_ADMIN/tnsnames.ora
#
# Output:             Entries into the CheckResults table
#                     Log files to ./logs directory
#
# Syntax:             check_targets.py -v vendor -f frequency -t type
#
# Called Routines:    cx_Oracle - for Oracle database calls
#                     psycopg2 - for PostgreSQL database calls
#                     date, grep, awk, cat, uname - misc UNIX commands
#
# Return Codes:       none
#
# Restrictions:       You must first run "source ~/venv/bin/activate
#                     to enter the necessary Python virtual environment
#
# Abend instructions: Resolve and rerun
#
# ============================================================================
# History of Changes
# ============================================================================
# Date           Person          Version    Comments
# 2021/01/13     M.Pankratz       1.00      Created
# 2021/01/21     M.Pankratz       1.01      add logging and restructure
# 2021/04/16     M.Pankratz       1.02      Refactoring / Consolidate Functions
#                                         1) Move checks into checklist table
#                                         2) Update results for each check
#                                         3) Move environment variables to file
# 2021/07/06     M.Pankratz       1.03      Extract common routines
# ============================================================================

# ============================================================================
# Import all the external Python modules that we need
# ============================================================================
from Inv_Logging import StartLogging
import cx_Oracle
import psycopg2
import sys, getopt               # Allows us to interact with the o/s
import paramiko                  # Allows us to ssh to the Database Servers
import threading                 # Allows us to time and kill hung db connections
from check_os_target import check_os_target  #Allows us to send o/s level checks to target
from add_result import add_result
from datetime  import datetime
from datetime  import date
from check_oms import CheckOMS   # Allows us to query the OEM Dev instance
from decouple  import config     # Allows us to read .env

# ============================================================================

# ============================================================================
# Set DBTools Environment and Global Variables
# ============================================================================

DBC_USER = config('DBC_USER')
DBC_PWD  = config('DBC_PWD')
INV_USER = config('INV_USER')
INV_PWD  = config('INV_PWD')
ORACLE_BASE = "/u01/app/oracle"
ORACLE_HOME = "/u01/app/oracle/product/12.2.0.1"
TNS_ADMIN = "/u01/app/oracle/DBTools/"
GlobalLogFile = "/home/orac4i/Inventory/src/logs/check_targets_"+str(date.today())+".log"
GlobalLogLevel = 'DEBUG'
GlobalLogName = "Check_Targets"
INVENTORYDB = "dbname=testdb user="+INV_USER+" password="+INV_PWD+" host=caddld-498.belldev.dev.bce.ca"

# ============================================================================

# ============================================================================
# Define Functions
# ============================================================================

# ============================================================================
# Function:     check_oracle_target
# Description:  Connect to the target and check it
# Input:        Valid TNS Entry
# Ouptut:       Return code
# ============================================================================

def check_oracle_target(ID, tns, all_db_checks):

    TargetLogger.info("Start Oracle DB Check on: %s ", tns)
    result=''
    RC=0

    try:
        target = cx_Oracle.connect(DBC_USER, DBC_PWD, tns, encoding="UTF-8")

        # lets only allow a few seconds per database query to collect what we want
        # note:  summing used space on some databases can take overa minute
        timer = threading.Timer(60,target.cancel)
        timer.start()    # start counting right before connecting to the database

        for check, check_type, result_column in all_db_checks:

          TargetLogger.debug("check: %s checktype: %s result_column: %s ", \
                                       check, check_type, result_column)
          if check_type == 'DB':
            if (VENDOR == 'ORACLE') or (VENDOR == '%') :
               target_cursor = target.cursor()
               target_cursor.execute(check)
               result = target_cursor.fetchone()

            elif check_type == 'OMS':
              result = CheckOMS(tns, check, TargetLogger)

            add_result(ID, result, result_column, TargetLogger)

            TargetLogger.info("InventoryID: %s result: %s result_column: %s ", \
                                     ID, result, result_column)


    except (OSError, ValueError, RuntimeError, TypeError, NameError) as exc:
        error, = exc.args
        TargetLogger.error("Error:    %s ", error)
    except cx_Oracle.DatabaseError as exc:
        error, = exc.args
        TargetLogger.error("DatabaseError-Code: %s %s ", error.code, error.message)
        RC=error.code
    except cx_Oracle.OperationalError as exc:
        error, = exc.args
        TargetLogger.error("OperationalError-Code: %s %s", error.code, error.message)
    except cx_Oracle.InternalError as exc:
        error, = exc.args
        TargetLogger.error("OperationalError-Code: %s %s    ", error.code, error.message)
    except cx_Oracle.InterfaceError as exc:
        error, = exc.args
        TargetLogger.error("InterfaceError-Code: %s %s ", error.code, error.message)
    except cx_Oracle.ProgrammingError as exc:
        error, = exc.args
        TargetLogger.error("ProgrammingError-Code: %s %s ", error.code, error.message)
    except cx_Oracle.NotSupportedError as exc:
        error, = exc.args
        TargetLogger.error("NotSupportedError-Code: %s %s ", error.code, error.message)
    except cx_Oracle.Error as exc:
        error, = exc.args
        TargetLogger.error("Error-Code: %s %s", error.code, error.message)
    except:
        TargetLogger.error("Unexpected error: %s ", sys.exc_info()[0])
        raise

    else:
        TargetLogger.debug("Oracle DB Check result: %s ", result)
        timer.cancel()
        target.close()

    finally:
        TargetLogger.info("Oracle DB Check Completed")

    return RC

# ============================================================================
# END check_oracle_target
# ============================================================================

# ============================================================================
# ============================================================================
# ---------------------------     MAIN PROGRAM     -------------------------------
# ============================================================================
# ============================================================================
def main(argv):
    global VENDOR
    global FREQUENCY
    global CHECKTYPE
    global TARGETTYPE
    VENDOR = '%'
    FREQUENCY = 'HOURLY'    # Default to the hourly checks if not specified
    CHECKTYPE = '%'
    TARGETTYPE = 'Database'

    CHECKQUERY='select check_command, check_type, result_column from public.checklist where 1=1 '
    TARGETQUERY='select inventoryid, instancename, owner, homedirectory, hostname, targettype from public.dbc_target where decommissioned is null '

    try:
        opts, args = getopt.getopt(argv,":t:c:v:f:h")

    except getopt.GetoptError:
        print ('check_targets.py [ -t Database|Server -c DB|OS -v <vendor> -f <frequency> ]')
        sys.exit(2)

    print("All Options passed: {}".format(opts))
    print("All arguments passed: {}".format(args))

    for opt, arg in opts:
        print("Option: {} Argument: {}".format(opt,arg))
        if opt == '-h':
            print ('check_targets.py [ -t Database|Server -c DB|OS -v <vendor> -f <frequency> ]')
            sys.exit()

        elif opt == "-t" :
            TARGETTYPE = arg
            TARGETQUERY += ' and targettype = \'' + TARGETTYPE + '\''
            if TARGETTYPE == 'Server' :
              CHECKTYPE='OS'
              CHECKQUERY += ' and check_type = \'' + CHECKTYPE + '\''
            elif opt == "-c":
              CHECKTYPE = arg
              CHECKQUERY += ' and check_type = \'' + CHECKTYPE + '\''

        elif opt== "-v":
            VENDOR = arg
            CHECKQUERY += ' and vendor = \'' + VENDOR + '\''

        elif opt =="-f":
            FREQUENCY = arg


    CHECKQUERY += ' and frequency = \'' + FREQUENCY + '\' order by priority'


    TargetLogger.info("Running CheckTargets.py with TARGETTYPE= %s VENDOR= %s FREQUENCY= %s CHECKTYPE= %s", TARGETTYPE, VENDOR, FREQUENCY, CHECKTYPE )
    TargetLogger.debug("Query: %s", CHECKQUERY)
    TargetLogger.info("Running Target Query: %s", TARGETQUERY)

    # ============================================================================
    # Fetch all the valid database targets from the InventoryDB and
    # check each one database by database
    # Attempt to query that target and record the results
    # ============================================================================

    # Connect to the Inventory DB

    inventory_conn = psycopg2.connect(INVENTORYDB)
    target_cursor = inventory_conn.cursor()


    # Get ALL the active targets
    target_cursor.execute(TARGETQUERY)
    all_targets = target_cursor.fetchall()
    TargetLogger.debug("# of Targets: %s" , len(all_targets))

    # Get ALL the checks to perform on these targets
    target_cursor.execute(CHECKQUERY)
    all_checks = target_cursor.fetchall()
    TargetLogger.debug("All Checks: %s" , all_checks)

    for InventoryID, InstanceName, Owner, HomeDir, HostName, TargetType in all_targets:
      if TARGETTYPE == 'Database' :
        OracleRC=0
        RC=0

        TargetLogger.debug("InventoryID: %s InstanceName: %s Owner: %s HomeDir: %s HostName: %s TargetType: %s " , \
                          InventoryID, InstanceName, Owner, HomeDir, HostName, TargetType)

        OracleRC=check_oracle_target(InventoryID, InstanceName+'_'+HostName, all_checks)
        add_result(InventoryID, OracleRC, 'dbstatus', TargetLogger)

        if OracleRC > 0 :
          TargetLogger.info("Inventory ID: %s Returned Error Code: %s" , InventoryID, OracleRC)

      for check, check_type, result_column in all_checks:
          OSRC=''
          if check_type == 'OS':
              OSRC=check_os_target(InventoryID, Owner, HostName, HomeDir, check, result_column, TargetLogger)
              if OSRC != '' :
                add_result(InventoryID, OSRC, result_column, TargetLogger)



    inventory_conn.close()
# ============================================================================
# END main program
# ============================================================================

if __name__ == "__main__":
    TargetLogger=StartLogging(GlobalLogLevel, GlobalLogFile, GlobalLogName)    # Log to File
    main(sys.argv[1:])
