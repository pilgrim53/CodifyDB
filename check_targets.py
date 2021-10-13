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
# Version:            1.04
#
# Purpose:            This script monitors database targets from the
#                     DBC Inventory Database. If the target exists and
#                     something has changed, then it updates the entry.
#
# Input files:        TARGETS Table
#                     checklist table
#                     $TNS_ADMIN/tnsnames.ora
#
# Output:             Entries into the CheckResults table
#                     Log files to $LOG_DIR/check_results_$date.log
#
# Syntax:             check_targets.py -t targettype -v vendor -f frequency -c checktype
#
# Called Routines:    cx_Oracle - for Oracle database calls
#                     psycopg2 - for PostgreSQL database calls
#                     date, grep, awk, cat, uname - misc UNIX commands
#
# Return Codes:       none
#
# Restrictions:       Enter the correct python environment prior to running.
#                     ex)  "source ~/<venv>/bin/activate"
#                           to enter the necessary virtual environment
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
# 2021/09/05     M.Pankratz       1.04      Add TargetType for OS Targets, etc.
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
from datetime  import datetime
from datetime  import date
from check_oms import CheckOMS   # Allows us to query the OEM Dev instance
from decouple  import config     # Allows us to read .env
# ============================================================================
import Targets
import Results
# ============================================================================

# ============================================================================
# Set DBTools Environment and Global Variables
# ============================================================================
DBC_USER      = config('DBC_USER')
DBC_PWD       = config('DBC_PWD')
INV_USER      = config('INV_USER')
INV_PWD       = config('INV_PWD')
ORACLE_BASE   = config('ORACLE_BASE')
ORACLE_HOME   = config('ORACLE_HOME')
TNS_ADMIN     = config('TNS_ADMIN')
LOG_DIR       = config('LOG_DIR')
CODIFYDB_HOST = config('CODIFYDB_HOST')
CODIFYDB      = config('CODIFYDB')
INVENTORYDB = "dbname="+CODIFYDB+" user="+INV_USER+" password="+INV_PWD+" host="+CODIFYDB_HOST

GlobalLogName = "Check_Targets"
GlobalLogFile = LOG_DIR+GlobalLogName+"_"+str(date.today())+".log"
GlobalLogLevel = 'INFO'

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
    TARGETTYPE = 'Database'  # Default to Database right now for development

    CHECKQUERY='select check_command, check_type, result_column, handler from public.checklist where 1=1 '
    TARGETQUERY='select inventoryid, instancename, owner, homedirectory, hostname, targettype from public.dbc_target where decommissioned is null '

    try:
        opts, args = getopt.getopt(argv,":t:c:v:f:h")

    except getopt.GetoptError:
        print ('check_targets.py [ -t Database|Server -c DB|OS -v <vendor> -f <frequency> ]')
        sys.exit(2)

    TargetLogger.debug('Command Options: %s  Arguments: ', opts, args ) 

    for opt, arg in opts:
        print("Option: {} Argument: {}".format(opt,arg))
        if opt == '-h':
            print ('check_targets.py -t [Database|Server] -c [DB|OS] -v [ORACLE|SUNOS|LINUX|AIX] -f [HOURLY|DAILY|WEEKLY] ')
            sys.exit()

        elif opt == "-t" :
            TARGETTYPE = arg
            if TARGETTYPE == 'Server' :
              CHECKTYPE='OS'
              CHECKQUERY += ' and vendor != \'ORACLE\' and check_type = \'' + CHECKTYPE + '\''
            elif opt == "-c":
              CHECKTYPE = arg
              CHECKQUERY += ' and check_type = \'' + CHECKTYPE + '\''

        elif opt== "-v":
            VENDOR = arg
            CHECKQUERY += ' and vendor = \'' + VENDOR + '\''
            TARGETQUERY += ' and vendor =  \'' + VENDOR + '\''

        elif opt== "-c":
            CHECKTYPE = arg
            CHECKQUERY += ' and check_type = \'' + CHECKTYPE + '\''

        elif opt =="-f":
            FREQUENCY = arg

    CHECKQUERY += ' and frequency = \'' + FREQUENCY + '\'  order by handler, priority'
    TARGETQUERY += ' and targettype = \'' + TARGETTYPE + '\' order by inventoryid'

    TargetLogger.info("Running CheckTargets.py with TARGETTYPE=%s VENDOR=%s FREQUENCY=%s CHECKTYPE=%s", TARGETTYPE, VENDOR, FREQUENCY, CHECKTYPE )
    TargetLogger.debug("Check Query: %s", CHECKQUERY)
    TargetLogger.debug("Target Query: %s", TARGETQUERY)

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
    inventory_conn.close()

    ######################################################
    # * * * *  Main Loop of all in-scope Targets * * * * #
    ######################################################
    for InventoryID, InstanceName, Owner, HomeDir, HostName, TargetType in all_targets:
        TargetLogger.debug("InventoryID: %s InstanceName: %s Owner: %s HomeDir: %s HostName: %s TargetType: %s " , \
                          InventoryID, InstanceName, Owner, HomeDir, HostName, TargetType)

        ###############################################################################
        # Sub Loop of All Checks for the Target
        # Reuse the connection to the target for all similar checks with same handler
        ###############################################################################
        oldHandler = ''
        RC=1
        connected = 'FALSE'

        for check, check_type, result_column, handler in all_checks:
            result=''
            if handler != oldHandler :
                oldHandler = handler
                if connected == 'TRUE' :
                   try:
                     connected = 'FALSE'
                     curr_connection.close()
                   except cx_Oracle.DatabaseError as exc:
                     error, = exc.args
                     TargetLogger.error("DatabaseError-Code: %s %s ", error.code, error.message)

                RC, curr_connection=Targets.Connect(HostName, InstanceName, Owner, handler, TargetLogger)
                TargetLogger.info("Connecting to Host: %s Instance: %s returned: %s " , HostName, InstanceName, RC )
                if RC != 1 :
                    Results.add(InventoryID, handler+':'+str(RC), 'access', TargetLogger)
                    TargetLogger.debug("%s connection failed to Host: %s Instance: %s Error: %s", handler, HostName, InstanceName, RC)
                    connected = 'FALSE'
                else :
                    connected = 'TRUE'

            if connected == 'TRUE' :
                info_rc, result=Targets.GetInfo(check, handler, curr_connection, TargetLogger)
                TargetLogger.debug("Inventory ID: %s Attribute: %s Value: %s RC: %s" , InventoryID, result_column, result, info_rc)
                if info_rc == 1 :
                    Results.add(InventoryID, result, result_column, TargetLogger)
                else:   # connection no longer works
                  TargetLogger.debug("Check %s RC: %s returned: %s ", check, info_rc, result )

        # Targets.Disconnect(curr_connection)
        if curr_connection != '':
          curr_connection.close()

    TargetLogger.info("Completed running CheckTargets.py with TARGETTYPE=%s VENDOR=%s FREQUENCY=%s CHECKTYPE=%s", \
                       TARGETTYPE, VENDOR, FREQUENCY, CHECKTYPE )
    TargetLogger.info("====================================================================================")

# ============================================================================
# END main program
# ============================================================================

if __name__ == "__main__":
    TargetLogger=StartLogging(GlobalLogLevel, GlobalLogFile, GlobalLogName)    # Log to File
    main(sys.argv[1:])
