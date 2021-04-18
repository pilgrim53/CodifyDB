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
from datetime import datetime
from datetime import date
from check_oms import CheckOMS   # Allows us to query the OEM Dev instance
from decouple import config      # Allows us to read .env
# ============================================================================

# ============================================================================
# Set DBTools Environment and Global Variables
# ============================================================================

DBC_USERNAME = config('DBC_USER')
DBC_PWD = config('DBC_PWD')
ORACLE_BASE = "/u01/app/oracle"
ORACLE_HOME = "/u01/app/oracle/product/12.2.0.1"
TNS_ADMIN = "/u01/app/oracle/DBTools/"
GlobalLog_File = "/home/orac4i/Inventory/src/logs/check_targets_"+str(date.today())+".log"
GlobalLogLevel = logging.DEBUG
INVENTORYDB = "database=\"testdb\", user = \"postgres\", password = DBC_PWD, \
               host = \"caddld-498.belldev.dev.bce.ca\", port = \"5432\" connect_timeout=3 "

# ============================================================================

# ============================================================================
# Define Functions
# ============================================================================

# ============================================================================
# Function:        StartLogging
# Description: Set up the Python Logging module
# Input:             LogLevel and Log File
# Ouptut:            Returns a logger object / handler
# ============================================================================
# Logging examples
# logging.debug('This should go to the log file.')
# logging.info('So should this')
# logging.warning('And this, too')
# logging.error('And non-ASCII stuff, too, like Øresund and Malmö')
# ============================================================================
def StartLogging(LogLevel, Log_File):
    # logging.basicConfig(filename=Log_File, encoding='utf-8', level=logging.INFO)
    logging.basicConfig(filename = Log_File, level=LogLevel)
    logging.basicConfig(format = '%(asctime)s:%(levelname)s:%(message)s', \
                        datefmt = '%m/%d/%Y %I:%M:%S %p')
    Logger=logging.getLogger('Check_Targets')
    Logger.setLevel(LogLevel)

    # Create a console handler
    ch = logging.StreamHandler()
    #ch.setLevel(logging.LogLevel)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    Logger.addHandler(ch)

    return Logger

# ============================================================================
# END StartLogging
# ============================================================================


# ============================================================================
#    check_os_target    
# ============================================================================
def check_os_target(owner, host, homedir, command):

    ssh_connection = paramiko.SSHClient()
    ssh_connection.load_system_host_keys()
    ssh_connection.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    timer = threading.Timer(90,ssh_connection.close)
    timer.start()    # start counting right before connecting to the database
    TargetLogger.info("Connecting to %s as %s to run %s ", host, owner, command)

    try:
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
            stdin, stdout, stderr = ssh_connection.exec_command(command)
            result_row = stdout.readlines()
            result=str(result_row[0]).strip()
            TargetLogger.info("Result: %s ", result)
            timer.cancel()    # cancel the connection thread if it's still alive after 30 seconds
    
        except  Exception as sshException:
            result="ssh exception"
            TargetLogger.error("Unable to run: %s on host: %s as %s Result: %s",   \
                               command, host, owner, sshException)
            
    finally:
        ssh_connection.close() 

    return result
# ============================================================================
#    End check_os_target    
# ============================================================================

# ============================================================================
# Function:     check_oracle_target
# Description:  Connect to the target and check it
# Input:        Valid TNS Entry
# Ouptut:       A check object array and Status
# ============================================================================

def check_oracle_target(instance, host, check):

    try:
        connection = cx_Oracle.connect("Cloud_DBC", "DBC#4Cloud2", tns, encoding="UTF-8")
        # lets only allow a few seconds per database query to collect what we want
        # note:  summing used space on some databases can take overa minute
        timer = threading.Timer(90,connection.cancel)
        timer.start()    # start counting right before connecting to the database
        
        db_info_cursor = connection.cursor()
        db_info_cursor.execute(check, instance, host)
        result = db_info_cursor.fetchone()

    except (OSError, ValueError, RuntimeError, TypeError, NameError) as exc:
        error, = exc.args
        TargetLogger.error("Error:    %s ", error)
    except cx_Oracle.DatabaseError as exc:
        error, = exc.args
        TargetLogger.error("DatabaseError-Code:    %s %s ", error.code, error.message)
        result=str(error.code)
    except cx_Oracle.OperationalError as exc:
        error, = exc.args
        TargetLogger.error("OperationalError-Code:    %s %s", error.code, error.message)
    except cx_Oracle.InternalError as exc:
        error, = exc.args
        TargetLogger.error("OperationalError-Code:    %s %s    ", error.code, error.message)
    except cx_Oracle.InterfaceError as exc:
        error, = exc.args
        TargetLogger.error("InterfaceError-Code:    %s %s ", error.code, error.message)
    except cx_Oracle.ProgrammingError as exc:
        error, = exc.args
        TargetLogger.error("ProgrammingError-Code:    %s %s ", error.code, error.message)
    except cx_Oracle.NotSupportedError as exc:
        error, = exc.args
        TargetLogger.error("NotSupportedError-Code:    %s %s ", error.code, error.message)
    except cx_Oracle.Error as exc:
        error, = exc.args
        TargetLogger.error("Error-Code:    %s %s", error.code, error.message)
    except:
        TargetLogger.error("Unexpected error:    %s    ", sys.exc_info()[0])
        raise

    else:
        timer.cancel() 
        
    finally:    
        connection.close()

    return result

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
    postgres_insert_connection = psycopg2.connect(INVENTORYDB)
    insert_cursor = postgres_insert_connection.cursor()
    insert_statement  =  "INSERT INTO CheckResults (inventoryid, checkdate," \
                         + column_name + " ) VALUES ( %s, %s, %s); "
    check_date = datetime.now()

    # Pass data to fill a query placeholders and let Psycopg perform
    # the correct conversion (no more SQL injections!)
    try:
        insert_cursor.execute(insert_statement, ( ID, check_date, check_result ))

    except psycopg2.Error as exc:
        error, = exc.args
        TargetLogger.error("Data Exception: %s %s", error.code, error.message) 

    else:
        TargetLogger.info("Added: %s  %s  %s  %s", ID, column_name, check_result, check_date) 

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
    VENDOR='ALL'
    FREQUENCY='ALL'
    CHECKTYPE='ALL'
    
    try:
        opts = getopt.getopt(argv,"h:vft")
    except getopt.GetoptError:
        print ('check_targets.py -v <vendor> -f <frequency> -t <type>')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print ('check_targets.py -v <vendor> -f <frequency> -t <type>')
            sys.exit()
        elif opt in ("-v"):
            VENDOR = arg
        elif opt in ("-f"):
            FREQUENCY = arg
        elif opt in ("-t"):
            CHECKTYPE = arg
    
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
    all_targets = target_cursor.fetchall()
    
    # Get ALL the checks to perform on these targets     
    target_cursor.execute("""
            select check, checktype, resultcolumn
                from public.checklist
                 where vendor = %s
                   and frequency = %s
                   and type = %s""",  VENDOR, FREQUENCY, CHECKTYPE )
    all_checks = target_cursor.fetchall()

    for InventoryID, InstanceName, Owner, HomeDir, HostName in all_targets:
        for check, checktype, result_column in all_checks:
            if (checktype == 'ORACLE') and ((CHECKTYPE == 'ALL') or (CHECKTYPE == 'ORACLE')):
                result = check_oracle_target(InstanceName, HostName, check)
                add_result(InventoryID, result, result_column)
                CheckOMS(InstanceName, HostName)
            if (checktype == 'OS') and ((CHECKTYPE == 'ALL') or (CHECKTYPE == 'OS')):
                result = check_os_target(Owner, HostName, HomeDir, check)
                add_result(InventoryID, result, result_column)
# ============================================================================
# END main program
# ============================================================================

if __name__ == "__main__":
    TargetLogger=StartLogging(GlobalLogLevel, GlobalLog_File)    # Log to File 
    main(sys.argv[1:])
