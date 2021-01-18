#!/home/orac4i/venv/bin/python
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
# Version:              1.01
#
# Purpose:              This script adds new targets from DBList into the 
#                       DBC Inventory Database. If the targe exists and 
#                       something has changed, then it updates the entry.
#
# Input files:          /u01/app/oracle/DBTools/DBList.txt
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
# Restrictions:         You must first run "source ~/venv/bin/activate
#                       to enter the necessary Python virtual environment
#
# Abend instructions:   Resolve and rerun
#
# ============================================================================
# History of Changes
# ============================================================================
# Date         Person            Version  Comments
# 2021/01/13   M.Pankratz        1.00     Created
# 2021/01/15   M.Pankratz        1.01     rename, add logging, restructure
# ============================================================================


# ============================================================================
# Import all the external Python modules that we need
# ============================================================================
import cx_Oracle          # https://oracle.github.io/python-cx_Oracle/
import psycopg2           # https://pypi.org/project/psycopg2/
import psycopg2.extras    # This gives access to the psycopg2 error messages
import sys                # for some reason this is not included by default
import logging            # https://docs.python.org/3/library/logging.html
import threading          # Allows us to time and kill hung db connections
from datetime import date # for some reason this is not included by default
# ============================================================================

# ============================================================================
# Set DBTools Environment Variables
# ============================================================================
ORACLE_HOME="/u01/app/oracle/product/12.2.0.1"
TNS_ADMIN="/u01/app/oracle/DBTools/"
target_file="/u01/app/oracle/DBTools/DBList.txt"
LOG_File="./logs/update_targets_"+str(date.today())+".log"
# ============================================================================

TargetLogger=StartLogging("Info", Log_File)  # Log to File 

# ============================================================================
# Read through the DBList.txt file database by database
# Attempt to query that target and record the results
# ============================================================================
with open(target_file) as tf:
  for target in tf:
    TargetLogger.info('Connecting to target: %s', str(target))
   
    # Try connecting to the database and get info if possible
    TargetInfo=pingTarget(target)

    if TargetInfo: 
        TargetLogger.info('Target %s exists. Checking Inventory DB', str(target))
        result=UpdateTarget(TargetInfo)  # Update if it exists and there is new info 

    else:
        # This was not a valid reachable target
        TargetLogger.info('Target was not valid or not reachable: Host: %s  Instance: %s ', str(host), str(instance))
        TargetLogger.info('Target %s info should be corrected or removed from DBList.txt', str(target))




# ============================================================================
# Functions
# ============================================================================

# ============================================================================
# Set up logging
# Logging examples
# ============================================================================
# logging.debug('This should go to the log file.')
# logging.info('So should this')
# logging.warning('And this, too')
# logging.error('And non-ASCII stuff, too, like Øresund and Malmö')

def StartLogging(LogLevel, Log_File):
    logging.basicConfig(filename=Log_File, encoding='utf-8', level=LogLevel)
    logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
    TargetLogger=logging.getLogger('Target_Update')
    TargetLogger.setLevel(logging.LogLevel)

    # Create a console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.LogLevel)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    TargetLogger.addHandler(ch)
ret(TargetLogger)
# ============================================================================


# ============================================================================
# Function:  pingTarget
#            Takes target in the format of host_instance 
#            Checks the Inventory database and retuns the result
# ============================================================================
def pingTarget(target):
    # Set some initial values each time we do a check
    NewTarget=False  # Set to False until we determine if it's True
    TargetRow='Empty'

    try:
        connection = cx_Oracle.connect("Cloud_DBC", "DBC#4Cloud2", target.strip(), encoding="UTF-8")
        timer = threading.Timer(30,connection.cancel)
        db_info_cursor = connection.cursor()
        timer.start()  # start counting right before connecting to the database
        db_info_cursor.execute("""
            select db.created, db.dbid, instance_name, host_name, version, db.log_mode, status
            from v$instance, v$database db 
            where instance_name = db.name """)
        TargetRow = db_info_cursor.fetchone()
        timer.cancel()  # cancel the connection thread if it's still alive after 30 seconds

        if TargetRow != None:
            # This target is reachable as Cloud_DBC!!
            TargetLogger.debug('Connected to: %s', str(TargetRow))
            NewTarget = True

        # All done with the Target Oracle connection
        connection.close()
    
    # Handle all the things that could go wrong with this connection attempt
    except cx_Oracle.DatabaseError as exc:
    # If there was a database error we need the ORA-##### error
    # This might mean the database exists
        error, = exc.args
        oraerr=error.code
        NotExist=['12545','12514','12505']
        if str(oraerr) in NotExist :
            TargetLogger.error('Target: %s   Status: ORA- %s  Message: %s', str(target), str(oraerr), str(error))
            TargetLogger.error('TNS Error: Target DB not added to inventory. Correct the issue or remove from DBList')
        else:
            TargetLogger.warning('Target: %s   Status: ORA- %s  Message: %s', str(target), str(oraerr), str(error))
            # We can add this target to inventory even though we can't log in
            NewTarget=True  
            TargetLogger.info('Target %s exists, but couldn''t log in. Setting blank initial values.', str(target))
            instance, host=target.split('_')
            DBCreateDate, DBID, version, logMode, status = "1900-01-01","","","",str(oraerr)

    except Exception as exc:
    # ============================================================================
    # There was a problem that was not database related
    # ============================================================================
        error, = exc.args
        oraerr=error.message
        TargetLogger.error('Target: %s   Status: ORA-%s  Message: %s', str(target), str(oraerr), str(error.message))
        TargetLogger.error('Target DB not added to inventory. Correct the issue or remove from DBList')


ret(NewTarget)


def UpdateTarget(target):
        # ============================================================================
        # Open a connection to the Inventory Database 
        # Insert or update the results if:
        #   1) The target is not already there
        #   2) If anything has changed about the target (i.e. version or logmode)
        # ============================================================================
         
        postgres_conn = psycopg2.connect(database="testdb", user = "postgres", password = "sys4Bell", host = "caddld-498.belldev.dev.bce.ca", port = "5432", connect_timeout=3 )
   
        # ============================================================================
        # 1) See if the target is in the inventory database
        # ============================================================================

        select_cursor = postgres_conn.cursor()
        TargetLogger.info('Checking if Target %s exists in inventory.', str(target))
   
        try: 
            select_cursor.execute("""
                select InventoryID, DBCreatedDate, DBID, InstanceName, HostName, Version, ArchiveLogMode, Status
                    from public.DBC_Target
                    where InstanceName = %s
                    and HostName = %s; 
                    """, (instance, host ))
   
            row = select_cursor.fetchone()

        except (psycopg2.DataError) as exc:
            errormsg = psycopg2.errors.lookup(exc.pgcode)
            TargetLogger.error('Target: %s  DataError: %s', str(target), str(errormsg))
            if ((errormsg == '02000' ) or ( errormsg == NoData )): 
                # Try to detect and flag "No Data Found" as it means we don't have this target
                TargetLogger.info('Is this a New Target Found!?!?')
                TargetLogger.info('Host: %s  Instance: %s  Message: %s', str(host), str(instance), str(errormsg))
                TargetLogger.error('Target DB not added to inventory. Correct the issue or remove from DBList')

                NewTarget=True

                # ============================================================================
                # Now lets insert or update if we got data above
                # ============================================================================
                #if DBCreateDate != '1900-01-01':
                DBCreateDate=str(TargetRow[0])
                DBID        =str(TargetRow[1])
                instance    =str(TargetRow[2])
                host        =str(TargetRow[3])
                version     =str(TargetRow[4])
                logMode     =str(TargetRow[5])
                status      =str(TargetRow[6])
                # ============================================================================

                pass
            else:
                NewTarget=False
                TargetLogger.info('Skipping Target: %s  DataError: %s', str(target), str(errormsg))
                
        except (psycopg2.DatabaseError, psycopg2.IntegrityError, psycopg2.InternalError)   as exc:
            error, = exc.args
            errormsg=error.code
            TargetLogger.error('Host: %s  Instance: %s  Message: %s', str(target),  str(errormsg))

   
        except Exception as exc:
            error, = exc.args
            errormsg=error.code
            TargetLogger.error('Postgres Exception on target: %s  Message: %s', str(target),  str(errormsg))
   

        if (NewTarget and (row == None)):
            TargetLogger.info('New Target Found. Host: %s Instance: %s ', str(host), str(instance))

            insert_cursor = postgres_conn.cursor()
   
            try:
                insert_cursor.execute("""
                    INSERT INTO public.dbc_target (InventoryCreate, DBCreatedDate, DBID, InstanceName, 
                                                HostName, Version, ArchiveLogMode, Status	) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
                """, ( date.today(), DBCreateDate, DBID, instance, host, version, logMode, status ))
       
                # Make the changes to the database persistent
                postgres_conn.commit()

            except (psycopg2.DatabaseError, psycopg2.IntegrityError, psycopg2.DataError, psycopg2.InternalError)   as exc:
                error, = exc.args
                TargetLogger.error('Error inserting new target: %s %s %s ', str(host),str(instance),str(error))
         
            except Exception as exc:
                error, = exc.args
                TargetLogger.error('Exception occurred inserting target: %s %s %s ', str(host), str(instance), str(error))
   
        else:
            if NewTarget:
                # see if something changed about the database info and UPDATE it.
                # select InventoryID, DBCreatedDate, DBID, InstanceName, HostName, Version, ArchiveLogMode 
                oldInventoryID =str(row[0])
                oldDBCreateDate=str(row[1])
                oldDBID        =str(row[2])
                oldinstance    =str(row[3])
                oldhost        =str(row[4])
                oldversion     =str(row[5])
                oldlogMode     =str(row[6])
                oldStatus      =str(row[7])

                if TargetRow != row:
                    TargetLogger.info('Target known. Status has changed. Host: %s  Instance: %s ', str(host), str(instance))
                    TargetLogger.info('New data: %s %s %s %s %s', str(logMode), str(version), str(DBID), str(DBCreateDate), str(status))
                    TargetLogger.info('Old data: %s %s %s %s %s', str(oldlogMode), str(oldversion), str(oldDBID), str(oldDBCreateDate), str(oldStatus))

                    # Pass data to fill a query placeholders and let Psycopg perform
                    # the correct conversion (no more SQL injections!)
                    update_cursor = postgres_conn.cursor()

                    try:
                        update_cursor.execute("""
                        UPDATE public.dbc_target 
                            set DBCreatedDate=%s, DBID=%s, Version=%s, ArchiveLogMode=%s, Status=%s
                        WHERE InventoryID=%s; 
                        """, ( DBCreateDate, DBID, version, logMode, status, oldInventoryID ))
          
                        # Make the changes to the database persistent
                        postgres_conn.commit()
   
                    except (psycopg2.DatabaseError, psycopg2.IntegrityError, psycopg2.DataError, psycopg2.InternalError)   as exc:
                        error, = exc.args
                        dberr=error.code
                        TargetLogger.error('Postgres DB Error: %s %s %s %s', str(host), str(instance), str(dberr), str(error))
            
                    except Exception as exc:
                        error, = exc.args
                        TargetLogger.error('Postgres Exception: %s %s %s', str(host), str(instance), str(error))

            else:
                TargetLogger.info('Target known and no change in status: Host: %s  Instance: %s ', str(host), str(instance))
        postgres_conn.close()
ret(result)
