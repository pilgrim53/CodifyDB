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
# History of Changes
# ============================================================================
# Date         Person            Version  Comments
# 2021/02/15   M.Pankratz        1.00     Created
# ============================================================================

import paramiko  # Allows us to ssh to the target hosts
import cx_Oracle  # https://oracle.github.io/python-cx_Oracle/
import psycopg2  # https://pypi.org/project/psycopg2/
import psycopg2.extras  # This gives access to the psycopg2 error messages
import sys  # for some reason this is not included by default
import logging  # https://docs.python.org/3/library/logging.html
import threading  # Allows us to time and kill hung db connections
# from numpy import asarray # convert sql result tuples to python arrays
from datetime import date  # for some reason this is not included by default


# Set DBTools Environment and Global Variables
ORACLE_HOME = "/u01/app/oracle/product/12.2.0.1"
TNS_ADMIN = "/u01/app/oracle/DBTools/"
LOG_FILE = "/home/orac4i/Inventory/src/logs/check_sqlpatch_" + str(date.today()) + ".log"
LOG_LEVEL = "DEBUG"


def start_logging(log_level, log_file):
    """
    Checks to see if a particular target is registered in the non-prod Patch repository
    Input Files:  DBC_TARGET  Table

    Output:       DBC_TARGET.in_sqlpatch
                  Log files to ./logs directory

    Syntax:       check_sqlpatch.py

    Called Routines:  cx_Oracle - for Oracle database calls
                      psycopg2 - for PostgreSQL database calls
                      date, grep, awk, cat, uname - misc UNIX commands


    Restrictions: You must first run "source ~/Inventory/bin/activate
                  to enter the necessary Python virtual environment
    """

    logging.basicConfig(filename=log_file, level=logging.DEBUG)
    logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
    target_logger = logging.getLogger('Check_Patch')
    target_logger.setLevel(logging.DEBUG)

    # Create a console handler
    ch = logging.StreamHandler()
    # ch.setLevel(logging.LogLevel)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    target_logger.addHandler(ch)

    return target_logger
    # End StartLogging


def check_patch(target):
    """
    Checks the DBC NonProd Patch Repository to see if it contains the requested target.
    :param target: in the format of host_instance
    :return: patch: a "Y/N" result
    """
    # Set some initial values each time we do a check
    patch = 'Unknown'  # Set to Unknown until it is known

    if "+ASM" in target:
        # TargetLogger.info('ASM Instance found: %s', str(target))
        a = 1
        # Build connection to
        # return NewTarget, TargetRow
    else:
        instance, host = target.split('_')
        TargetLogger.info('Check Patch on Target:  %s ', str(target))

        try:
            connection = cx_Oracle.connect("Cloud_DBC", "DBC#4Cloud2", target, encoding="UTF-8")
            # lets allow 45 seconds per database to collect what we want
            timer = threading.Timer(45, connection.cancel)
            timer.start()  # start counting right before connecting to the database

            db_info_cursor = connection.cursor()
            plsql_stmt = """
begin
declare 
  ver number(2);
  psu varchar2(100);
  sql_text varchar2(1000);
begin
 select substr(version,1,instr(version, '.')-1) into ver from v$instance;
--  dbms_output.put_line ( 'Version is: '||ver ) ;
  case 
    when ver = 9
    then sql_text := 'select max (PS) from 
                      ((select max(substr(version, instr(version, :1||''.'',1,1))) PS
                         from dba_registry
                         where upper(comp_name) like ''%CATALOG%'') 
                        union
                        (select version PS from v$instance))';
    when ver = 10
    then sql_text := 'select max (PS) from 
                       ((select max(substr(version, instr(version, :1||''.'',1,1))) PS
                          from dba_registry
                          where upper(comp_name) like ''%CATALOG%'') 
                         union
                        (select nvl(max(substr(comments, instr(comments, ''10.'',1,1))),0) PS
                          from dba_registry_history
                          where upper(comments) like ''PSU%'' or upper(comments) like ''CPU%''))';
    when ver = 11
    then sql_text := 'select nvl(max(substr(COMMENTS, instr(comments, :1||''.'',1,1))),''None'') 
                      from DBA_REGISTRY_HISTORY 
                      where upper(comments) like ''PSU%''
                         or upper(comments) like ''CPU%''';
    when ver = 12
    then sql_text := 'select nvl(max(substr(DESCRIPTION, instr(description, :1||''.'',1,1))),''None'') 
                      from dba_registry_sqlpatch 
                      where upper(description) like ''DATABASE%''';   
    when ver = 18
    then sql_text := 'select nvl(max(substr(description, instr(description, :1||''.'',1,1))),''None'') 
                      from dba_registry_sqlpatch 
                      where upper(description) like ''DATABASE%''';   
    when ver = 19
    then sql_text := 'select nvl(max(substr(description, instr(description, :1||''.'',1,1))),''None'') 
                      from dba_registry_sqlpatch 
                      where upper(description) like ''DATABASE%''';   
    when ver > 19
    then sql_text := 'select ''Need new CASE for v''||:1 from dual';   
  end case;
--  dbms_output.put_line ( sql_text ) ;
  execute immediate sql_text into psu using ver;
  -- dbms_output.put_line ( psu ) ;
  return psu;
end;
end;"""

            db_info_cursor.execute(plsql_stmt)
            # Patch = db_info_cursor.fetchone()

        except (OSError, ValueError, RuntimeError, TypeError, NameError) as exc:
            error, = exc.args
            patch = 'FAILED'
            TargetLogger.error('Error:  %s ', error)

        except cx_Oracle.DatabaseError as exc:
            error, = exc.args
            patch = 'FAILED'
            TargetLogger.error('DatabaseError-Code:  %s %s ', error.code, error.message)

        except:
            TargetLogger.error('Failed to check Patch:  %s %s ', str(target), str(patch))
            patch = 'FAILED'

        # finally:
        #  connection.close()

    return patch[0]

# END CheckPatch


# ---------------------------   MAIN PROGRAM   -------------------------------
if __name__ == '__main__':
    TargetLogger = start_logging(LOG_LEVEL, LOG_FILE)  # Log to File

    # Fetch all the valid database targets from the InventoryDB and
    # check each one database by database
    # Attempt to query that target and record the results

    # Connect to the Inventory DB

    postgres_conn = psycopg2.connect(INVENTORYDB)
    target_cursor = postgres_conn.cursor()

    # Get ALL the active targets
    target_cursor.execute("""select InventoryID, instance_name, owner, home_directory, hostname from 
    public.dbc_target where decommissioned is null and hostname like 'AIAL%' order by InventoryID """)
    targets = target_cursor.fetchall()

    for InventoryID, instance_name, owner, home_directory, hostname in targets:
        target = instance_name + '_' + hostname
        Patch = check_patch(target)

        update_cursor = postgres_conn.cursor()

        try:
            update_cursor.execute("""
         UPDATE public.dbc_target
            set in_sqlpatch=%s
          WHERE InventoryID=%s """, (str(Patch), str(InventoryID)))

            # Make the changes to the database persistent
            # # TargetLogger.info("InventoryID %s Updated to %s.", InventoryID, in_sqlpatch)
            postgres_conn.commit()
            update_cursor.close()
        except:
            # TargetLogger.error("Error setting Patch flag for InventoryID %s to Patch %s ", str(InventoryID),
            # str(in_sqlpatch))
            a = 1

    postgres_conn.close()
