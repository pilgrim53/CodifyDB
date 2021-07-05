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
# Version:            1.02
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
# ============================================================================


# ============================================================================
# Import all the external Python modules that we need
# ============================================================================
import cx_Oracle
import psycopg2
import logging
import sys, getopt               # Allows us to interact with the o/s
import paramiko                  # Allows us to ssh to the Database Servers
import threading                 # Allows us to time and kill hung db connections
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
GlobalLog_File = "/home/orac4i/Inventory/src/logs/check_targets_"+str(date.today())+".log"
GlobalLogLevel = logging.DEBUG
INVENTORYDB = "dbname=testdb user="+INV_USER+" password="+INV_PWD+" host=caddld-498.belldev.dev.bce.ca"


# ============================================================================

# ============================================================================
# Define Functions
# ============================================================================

# ============================================================================
# Function:    StartLogging
# Description: Set up the Python Logging module
# Input:       LogLevel and Log File
# Ouptut:      Returns a logger object / handler
# ============================================================================
# Logging examples
# logging.debug('This should go to the log file.')
# logging.info('So should this')
# logging.warning('And this, too')
# logging.error('And non-ASCII stuff, too, like Øresund and Malmö')
# ============================================================================
def StartLogging(LogLevel, Log_File):
    logging.basicConfig(filename = Log_File, level=LogLevel)
    logging.basicConfig(format = '%(asctime)s:%(levelname)s:%(message)s', \
                        datefmt = '%m/%d/%Y %I:%M:%S %p')
    Logger=logging.getLogger('Check_Targets')
    Logger.setLevel(LogLevel)

    # Create a console handler
    ch = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    Logger.addHandler(ch)
    Logger.info("Begin Logging Level: %s", LogLevel)

    return Logger

# ============================================================================
# END StartLogging
# ============================================================================


# ============================================================================
#    check_os_target    
# ============================================================================
def check_os_target(ID, owner, host, homedir, all_checks):
    RC=0

    ssh_connection = paramiko.SSHClient()
    ssh_connection.load_system_host_keys()
    ssh_connection.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    timer = threading.Timer(90,ssh_connection.close)
    timer.start()    # start counting right before connecting to the database

    try:
        TargetLogger.info("Connecting to %s as %s ", host, owner)
        ssh_connection.connect(host, 22, owner)

    except paramiko.ssh_exception.AuthenticationException:
        result="ssh auth error"
        TargetLogger.error("Authentication failed, Host: %s    Owner: %s", host, owner)
        
    except paramiko.ssh_exception.BadHostKeyException as badHostKeyException:
        result="bad ssh key"
        TargetLogger.error("Unable to verify server's host key: %s", badHostKeyException)

    except    paramiko.ssh_exception.SSHException as sshException:
        result="ssh exception"
        TargetLogger.error("Unable to establish SSH connection: %s",    sshException)

    except Exception as sshException:
        result="ssh exception"
        TargetLogger.error("Unable to establish SSH connection: %s ",    sshException)

    else:
        try: 
            for check, check_type, result_column in all_checks:
                if check_type == 'OS':
                    if result_column == 'swrelease':
                        check = homedir + '/OPatch/' + check

                    if result_column == 'email':
                        check = 'cd ' + homedir + '/../../DBTools;' + check

                    TargetLogger.info("Running %s as %s on %s ", check, owner, host)
                    stdin, stdout, stderr = ssh_connection.exec_command(check)

                    result_row = stdout.readlines()
                    result_err = stderr.readlines()

                    if result_row :
                        result=str(result_row[0]).strip()
                        add_result(ID, result, result_column)
                        TargetLogger.info("InventoryID: %s result: %s result_column: %s ", \
                                   ID, result, result_column)   

                    TargetLogger.debug("OS Check Errors: %s ", result_err )
                    timer.cancel()    # cancel the connection thread if it's still alive after 30 seconds

        except  Exception as sshException:
            RC=911 
            TargetLogger.error("Unable to run: %s on host: %s as %s Result: %s",   \
                               check, host, owner, sshException)
            
    finally:
        ssh_connection.close() 

    return RC

# ============================================================================
#    End check_os_target    
# ============================================================================

# ============================================================================
# Function:     check_oracle_target
# Description:  Connect to the target and check it
# Input:        Valid TNS Entry
# Ouptut:       Return code
# ============================================================================

def check_oracle_target(ID, tns, all_db_checks):

    TargetLogger.info("Start Oracle DB Check on: %s ", tns)
    result='TBD'
    RC=0

    try:
        target = cx_Oracle.connect(DBC_USER, DBC_PWD, tns, encoding="UTF-8")
        result=target

        # lets only allow a few seconds per database query to collect what we want
        # note:  summing used space on some databases can take overa minute
        timer = threading.Timer(90,target.cancel)
        timer.start()    # start counting right before connecting to the database
        
        for check, check_type, result_column in all_db_checks:
            if check_type == 'DB':
                if (VENDOR == 'ORACLE') or (VENDOR == '%') :
                    #print( all_checks)
                    TargetLogger.info("check: %s checktype: %s result_column: %s ", \
                                       check, check_type, result_column)
    
                    target_cursor = target.cursor()
                    target_cursor.execute(check)
                    result = target_cursor.fetchone()
    
                    add_result(ID, result, result_column)
                    TargetLogger.info("InventoryID: %s result: %s result_column: %s ", \
                                       ID, result, result_column)               

            # CheckOMS(InstanceName, HostName)

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
# Function:     add_result
# Description:  Insert the check results into the inventory database
# Input:        Check results and column_name for the results to be stored
# Ouptut:       Single entry into CheckResults table
# ============================================================================

def add_result(ID, check_result, column_name):
    TargetLogger.debug("Insert check result: %s into %s for ID: %s", check_result, column_name, ID)
    postgres_insert_connection = psycopg2.connect(INVENTORYDB)
    insert_cursor = postgres_insert_connection.cursor()
    insert_statement  =  "INSERT INTO checkresults (inventoryid, checkdate, check_result, check_column) \
                          VALUES ( %s, %s, %s, %s ); "
    # insert_statement  =  "INSERT INTO checkresults (inventoryid, checkdate," \
    #                      + column_name + " ) VALUES ( %s, %s, %s); "
    check_date = datetime.now()

    # Pass data to fill a query placeholders and let Psycopg perform
    # the correct conversion (no more SQL injections!)
    try:
        insert_cursor.execute(insert_statement, ( ID, check_date, check_result, column_name ))

    except psycopg2.Error as exc:
        error, = exc.args
        TargetLogger.error("Data Exception: %s ", error) 

    else:
        TargetLogger.info("Result added: %s  %s  %s  %s", ID, column_name, check_result, check_date) 

        # Make the changes to the database persistent
        postgres_insert_connection.commit()

    finally:
        postgres_insert_connection.close()

# ============================================================================
# END add_result
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
    VENDOR = '%'
    FREQUENCY = '%'
    CHECKTYPE = '%'

    CHECKQUERY='select check_command, check_type, result_column from public.checklist where 1=1'
    
    try:
        opts, args = getopt.getopt(argv,"h:v:f:t")
        
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

        elif opt in ("-f"):
            FREQUENCY = arg
            CHECKQUERY += ' and frequency = \'' + FREQUENCY + '\''


    TargetLogger.info("Running CheckTargets.py with VENDOR=%s FREQUENCY=%s CHECKTYPE=%s", VENDOR, FREQUENCY, CHECKTYPE )
    TargetLogger.debug("Query: %s", CHECKQUERY)

    # ============================================================================
    # Fetch all the valid database targets from the InventoryDB and
    # check each one database by database
    # Attempt to query that target and record the results
    # ============================================================================
    
    # Connect to the Inventory DB 
    
    inventory_conn = psycopg2.connect(INVENTORYDB)
    target_cursor = inventory_conn.cursor()
    
    # Get ALL the active targets     
    target_cursor.execute("""
            select inventoryid, instancename, owner, homedirectory, hostname 
                from public.dbc_target
                 where decommissioned is null
            order by inventoryid """)
    all_targets = target_cursor.fetchall()
    
    # Get ALL the checks to perform on these targets     
    target_cursor.execute(CHECKQUERY)
    all_checks = target_cursor.fetchall()
    TargetLogger.debug("All Checks: %s" , all_checks)

    for InventoryID, InstanceName, Owner, HomeDir, HostName in all_targets:
        OracleRC=0
        RC=0
        TargetLogger.debug("InventoryID: %s InstanceName: %s Owner: %s HomeDir: %s HostName: %s ", \
                          InventoryID, InstanceName, Owner, HomeDir, HostName)

        OracleRC=check_oracle_target(InventoryID, InstanceName+'_'+HostName, all_checks)
        add_result(InventoryID, OracleRC, 'dbstatus')

        OSRC=check_os_target(InventoryID, Owner, HostName, HomeDir, all_checks)

    if OracleRC > 0 :
        TargetLogger.info("Inventory ID: %s Returned Error Code: %s" , InventoryID, OracleRC)
   
                                    
    inventory_conn.close()           
# ============================================================================
# END main program
# ============================================================================

if __name__ == "__main__":
    TargetLogger=StartLogging(GlobalLogLevel, GlobalLog_File)    # Log to File 
    main(sys.argv[1:])
    
