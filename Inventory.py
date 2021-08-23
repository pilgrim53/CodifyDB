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
from datetime import date, datetime # for some reason this is not included by default
from decouple  import config     # Allows us to read .env
# from update_targets import check_os # Allows us to reuse the os check function
import socket
import os
from Inv_Logging    import StartLogging
import Results    

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
target_file="./discovery.txt"

# ============================================================================
# Function:    GetInventoryID
# Description: Creates the initial Target entry in the DBC_Target table
# Input:       Takes target in the format of host, instance, container, port
# Ouptut:      Returns a boolean if its new and the target info 
#              [instance,host,DBCreateDate,DBID,status, port]
# ============================================================================
def GetID(host, instance,  TargetLogger):

    InventoryID=0

    postgres_conn = psycopg2.connect(INVENTORYDB)

    select_cursor = postgres_conn.cursor()
    select_stmt = 'select coalesce(inventoryid,0) from public.dbc_target where hostname=\'' + host + '\' and instancename=\''+ instance +'\' order by inventoryid '

    try:
      select_cursor.execute(select_stmt)
      result = select_cursor.fetchone()
      TargetLogger.info('Check %s %s returned: ''%s''', host, instance, result )
      if result is None : 
        InventoryID=0
      else:
        InventoryID = result[0]

      TargetLogger.debug('Check for existing target returned: %s', InventoryID )

    except (psycopg2.DatabaseError, psycopg2.IntegrityError, psycopg2.DataError, psycopg2.InternalError)   as exc:
        error, = exc.args
        TargetLogger.error('Error checking existance of target: %s %s %s ', str(host),str(instance), str(error))

    postgres_conn.close()

    return InventoryID
# ============================================================================
# END GetID
# ============================================================================


# ============================================================================
# Function:    GetAttribute
# Description: Takes a target and an OS check and first obtains the FID and 
#              home_dir for the call to the check_os_target routine
# Returns:     The result of the OS check query
# ============================================================================
def GetAttribute(InventoryID, target, column, TargetLogger):
    value=''
    QUERY='select '+column+' from dbc_target where inventoryid='+str(InventoryID)+'' 

    try:
        postgres_conn = psycopg2.connect(INVENTORYDB)
        select_cursor = postgres_conn.cursor()
        # Get just the info about the target for comparison
        select_cursor.execute(QUERY)
        value = select_cursor.fetchone()
        value=value[0].strip()

    except cx_Oracle.DatabaseError as exc:
        # If there was a database error we need the ORA-##### error
        error, = exc.args
        oraerr=str(error.code)
        TargetLogger.error('Target: %s   Status: ORA- %s  Message: %s', str(target), oraerr, str(error))    

    return value

# ============================================================================
# END GetTargetOSInfo
# ============================================================================
