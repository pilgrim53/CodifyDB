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
import Results    
import Inventory

# ============================================================================
# Set DBTools Environment and Global Variables
# ============================================================================
DBC_USER = config('DBC_USER')
DBC_PWD  = config('DBC_PWD')
OLD_DBC_PWD  = config('OLD_DBC_PWD')
INV_USER = config('INV_USER')
INV_PWD  = config('INV_PWD')
INVENTORYDB = "dbname=testdb user="+INV_USER+" password="+INV_PWD+" host=caddld-498.belldev.dev.bce.ca"
ORACLE_HOME="/u01/app/oracle/product/12.2.0.1"
TNS_ADMIN="/u01/app/oracle/DBTools/"
target_file="./discovery.txt"


# ============================================================================
# Function:    CreateDBC
# Description: Force the creation or recreation of the CLOUD_DBC database user
# Returns:     status of command 1=success, 0=fail, -1=could not run
# ============================================================================
def CreateDBC(target, owner, TargetLogger):
  instance, host=target.split('_')
  result=-1
  TargetLogger.debug('Fix CLOUD_DBC on: %s', str(target))

  DBC_COMMAND=""" . ./.bash_profile;    sqlplus / as sysdba <<sqlOUT
ALTER SESSION SET "_oracle_script"=TRUE;
create user Cloud_DBC identified by "Just4Now" account unlock;
ALTER USER CLOUD_DBC IDENTIFIED BY VALUES 'S:86DFBCB95B28142998C2C27D6CC6F29F1BFFD1D15E5F996DCAAB6E2F13B1;T:BA8D9BE25142F60BFBB2DBE0658D594086E583252F18CBE7B1E05AB97F3A751A258C4019A3A7247B7545B4D230D9F085A7CB0038D47272070E00FA586A4D4BB104BD778E6DE6339DAB20966392D66F4C' account unlock;
ALTER USER CLOUD_DBC profile NOEXPIRE_PWD;
grant dba to Cloud_DBC;
ALTER USER Cloud_DBC SET CONTAINER_DATA=ALL CONTAINER=CURRENT;
exit
sqlOUT"""

  try:
    ssh_connection = paramiko.SSHClient()
    ssh_connection.load_system_host_keys()
    ssh_connection.set_missing_host_key_policy(paramiko.AutoAddPolicy())
  
    timer = threading.Timer(30,ssh_connection.close)
    timer.start()    # start counting right before connecting to the database
  
    TargetLogger.info("Connecting to %s as %s ", host, owner)
    ssh_connection.connect(host, 22, owner) 

  except paramiko.ssh_exception.AuthenticationException:
    TargetLogger.error("Authentication failed, Host: %s    Owner: %s", host, owner)

  else:
    try:
      if owner != '':
        TargetLogger.info("Running %s as %s on %s ", DBC_COMMAND, owner, host)
        stdin, stdout, stderr = ssh_connection.exec_command(DBC_COMMAND, get_pty=True)

        result_row = stdout.readlines()
        result_err = stderr.readlines()
        TargetLogger.info("OS Check stdout: %s ", str(result_row) )
        TargetLogger.info("OS Check Errors: %s ", str(result_err) )
        result=1 

    except  Exception as sshException:
      TargetLogger.error("Unable to run on host: %s as %s Result: %s",   \
                               host, owner, sshException)
      result=0

  finally:
    ssh_connection.close()


  return result


# ============================================================================
# Function:    UpdatePassword
# Description: Force the creation or recreation of the CLOUD_DBC database user
# Returns:     None
# ============================================================================
def UpdatePassword(target):
    instance, host=target.split('_')
    value=0
    TargetLogger.debug('Fix CLOUD_DBC on: %s', str(target))

        
    try:
        connection = cx_Oracle.connect(DBC_USER, OLD_DBC_PWD, target, encoding="UTF-8")
        timer = threading.Timer(15,connection.cancel)
        db_info_cursor = connection.cursor()
        try:
            timer.start()  # start counting right before connecting to the database
            db_info_cursor.execute(check)
            value = db_info_cursor.fetchone()
            value=str(value[0]).strip()
            TargetLogger.debug('Connected to: %s', str(target))

            PWD_Update = 'alter user cloud_dbc identified by ' + DBC_PWD
            db_info_cursor.execute(PWD_Update)


        except cx_Oracle.DatabaseError as exc:
            error, = exc.args
            oraerr=str(error.code)

            TargetLogger.error('Target: %s   Status: ORA- %s  Message: %s', str(target), oraerr, str(error))
            timer.cancel()  # cancel the timer before leaving this function
        
        connection.close()   # All done
        timer.cancel()  # cancel the timer before leaving this function
    
    # Handle all the things that could go wrong with this connection attempt
    except cx_Oracle.DatabaseError as exc:
    # If there was a database error we need the ORA-##### error
    # This might mean the database exists
        error, = exc.args
        oraerr=str(error.code)
        TargetLogger.error('Target: %s   Status: ORA- %s  Message: %s', str(target), oraerr, str(error))
        value=-1

    return value

# ============================================================================
# END UpdatePassword
# ============================================================================


# ============================================================================
# Function:    GetDBInfo
# Description: Checks the target database for a single spcific key attribute
# Returns:     The result of the check query
#              RC=-1 means could not connect
#              RC=0 means check failed
#Future:   Make the check timeout a parameter and setting for each check
# ============================================================================
def GetDBInfo(target, check, TargetLogger):
    instance, host=target.split('_')
    value=0

    try:
        connection = cx_Oracle.connect(DBC_USER, DBC_PWD, target, encoding="UTF-8")
        timer = threading.Timer(15,connection.cancel)
        db_info_cursor = connection.cursor()
        try:
            timer.start()  # start counting right before connecting to the database
            db_info_cursor.execute(check)
            value = db_info_cursor.fetchone()
            value=str(value[0]).strip()
            TargetLogger.debug('Connected to: %s', str(target))
        # Handle all the things that could go wrong with this connection attempt
        except cx_Oracle.DatabaseError as exc:
            # If there was a database error we need the ORA-##### error
            # This might mean the database exists
            error, = exc.args
            oraerr=str(error.code)

            TargetLogger.error('Target: %s   Status: ORA- %s  Message: %s', str(target), oraerr, str(error))
            timer.cancel()  # cancel the timer before leaving this function
            value=oraerr
        
        connection.close()   # All done
        timer.cancel()  # cancel the timer before leaving this function
    
    # Handle all the things that could go wrong with this connection attempt
    except cx_Oracle.DatabaseError as exc:
    # If there was a database error we need the ORA-##### error
    # This might mean the database exists
        error, = exc.args
        oraerr=str(error.code)
        TargetLogger.error('Target: %s   Status: ORA- %s  Message: %s', str(target), oraerr, str(error))
        value=oraerr

    TargetLogger.info('GetDBInfo result for Target: %s Result: %s', str(target), str(value))
    return value

# ============================================================================
# END GetDBInfo
# ============================================================================


# ============================================================================
# Function:    Scan
# Description: Attempts to acquire new targets by scanning a list of potential
#              targets.   If a target is found, the inventory database is 
#              checked to see if it is already a known target.
# Input:       Takes target in the format of host_instance, owner, homedir, port
# Ouptut:      RC=0  If the target exists but login is unsuccessful
#            RC=2  If the target is already in the inventory DB
#            RC=1  If it is a new target ready to be added
#            RC=-1 If the potential target is not reachable, a REJECT record is created.  
# 
# Recommended action for calling routine:
# RC=-1   REJECT - Review connectivity to host and target. Fix and/or update candidate list
# RC=0    Deploy standard credentials / tools to target and re-run / Record Target Info
# RC=1    Add this target
# RC=2    Update this target
# ============================================================================
def Scan(target, owner, port, TargetLogger):

  inventoryid=0
  # host, instance=target.split('_')    # needed for oracle_discovery.ksh v1.0
  instance, host=target.split('_')
  inventoryid=Inventory.GetID(host, instance, TargetLogger)
  if inventoryid > 0 :
    owner=Inventory.GetAttribute(inventoryid, target, 'owner', TargetLogger)

  # Try a default connection to this target first. Chances are "we know dis".
  RC=GetDBInfo(target, "select \'1\' from dual", TargetLogger)
  NoAccess=['1017','1045', '1033', '28000', '28001']


  if RC in NoAccess :
    RC=CreateDBC(target, owner, TargetLogger)
  
  if int(RC) == 1 :
      inventoryid=Inventory.GetID(host, instance, TargetLogger)
      if inventoryid > 0:
         TargetLogger.info('Target: %s corresponds to active InventoryID: %s', target, inventoryid )
         RC=2 # Elevate this to an existing target status
      elif inventoryid == 0:
	  # if inventoryid == 0:
         TargetLogger.info('Target: %s has working TNSNames but no InventoryID' )
         RC=1  # Ready to be added to Inventory


  else:   # Try making our own TNS String 
       ping_result=os.system('ping %s -4 -c 4 >/dev/null ' % (host))
       if ping_result < 1 :
           TargetLogger.info('Host: %s is pingable.', host)
           try:
               target_dsn = cx_Oracle.makedsn(host, port, service_name=instance)
               connection = cx_Oracle.connect(user=DBC_USER, password=DBC_PWD, dsn=target_dsn)
               timer = threading.Timer(5,connection.cancel)
               timer.start()  # start counting right before connecting to the database
               db_info_cursor = connection.cursor()
               TargetLogger.info('Connected Port: %s Host: %s Instance: %s', port, host, instance)
               RC=1
               timer.cancel()  # cancel the timer
               connection.close()
               # CreateTNS(target_dsn)

           except cx_Oracle.DatabaseError as exc:
         # Handle all the things that could go wrong with this connection attempt
         # If there was a database error we need the ORA-##### error
         # This might mean the database exists
             error, = exc.args
             oraerr=str(error.code)
             NotExist=['12545','12541','12543','12514','12505']
             NoAccess=['1017','1045', '1033', '28000', '28001']
             if oraerr in NotExist :
                 TargetLogger.error('Target: %s   Status: ORA- %s  Message: %s', str(target), oraerr, str(error))
                 TargetLogger.error('TNS Error: Correct the issue or remove from DBList')
                 RC=-1
             elif oraerr in NoAccess:
                 # We can add this target to inventory even though we can't log in
                 TargetLogger.info('Target %s exists, but couldn''t log in. %s', str(target), oraerr)
                 RC=0
             else:
                 TargetLogger.error('Other Error: %s', str(error))
                 RC=-1
             
        
       else:
           TargetLogger.info('Skipping host %s is not pingable. Please check. %s', host, ping_result)
           RC=-1
      
  TargetLogger.info('Target: %s Scan result: %s InventoryID: %s', target, RC, inventoryid)
      
  return RC
# ============================================================================
# END Scan
# ============================================================================


# ============================================================================
# Function:    Reject
# Description: Creates the initial Target entry in the DBC_Target table
# Input:       Takes target in the format of host, instance, container, port
# Ouptut:      Returns a boolean if its new and the target info 
#              [instance,host,DBCreateDate,DBID,status, port]
# ============================================================================
def Reject(host, vendor, instance, status, owner, homedir, importantnotes, TargetLogger):

    result=0
    postgres_conn = psycopg2.connect(INVENTORYDB)
    insert_cursor = postgres_conn.cursor()
    insert_stmt = """INSERT INTO public.dbc_target_rejects 
                       (InventoryCreate, HostName, InstanceName, vendor, status, owner, homedirectory, importantnotes) 
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s); """
              
    try:
          insert_cursor.execute(insert_stmt, ( date.today(),host,instance,vendor,status,owner,homedir,importantnotes ))
          # Make the changes to the database persistent
          postgres_conn.commit()
  
    except (psycopg2.DatabaseError, psycopg2.IntegrityError, psycopg2.DataError, psycopg2.InternalError)   as exc:
          error, = exc.args
          TargetLogger.error('Error inserting reject record: %s %s %s ', str(host),str(instance),str(error))
          result=-1

    else:
          result=1
          TargetLogger.info('Rejected new target: %s %s  ', str(host),str(instance))

    TargetLogger.debug('Target Reject Result: %s', result)

    postgres_conn.close()

    return result
# ============================================================================
# END Reject
# ============================================================================


# ============================================================================
# Function:    Add
# Description: Creates the initial Target entry in the DBC_Target table
# Input:       Takes target in the format of host, instance, container, port
# Ouptut:      Returns a boolean if its new and the target info 
#              [instance,host,DBCreateDate,DBID,status, port]
# ============================================================================
def Add(host, instance, container, DBID, owner, homedir, status, port, TargetLogger):

    result=0
    count=0

    postgres_conn = psycopg2.connect(INVENTORYDB)
    result=Inventory.GetID(host, instance, TargetLogger)
    if result < 1:

      insert_cursor = postgres_conn.cursor()
      insert_stmt = """INSERT INTO public.dbc_target 
                       (InventoryCreate, HostName, InstanceName, Container, DBID, owner, homedirectory, Vendor, Status, Port) 
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s); """
              
      try:
          insert_cursor.execute(insert_stmt, ( date.today(),host,instance,container,DBID,owner,homedir,'ORACLE',status,port) )
          # Make the changes to the database persistent
          postgres_conn.commit()
  
      except (psycopg2.DatabaseError, psycopg2.IntegrityError, psycopg2.DataError, psycopg2.InternalError)   as exc:
          error, = exc.args
          TargetLogger.error('Error inserting new target: %s %s %s ', str(host),str(instance), str(error))
          result=-1
           
      except Exception as exc:
          error, = exc.args
          TargetLogger.error('Exception occurred inserting target: %s %s Container: %s %s', \
                              str(host), str(instance), str(container), str(error))
          result=-1

      else:
          result=Inventory.GetID(host, instance, TargetLogger)

      TargetLogger.info('Add target Result InventoryID: %s', result)

      postgres_conn.close()

    return result
# ============================================================================
# END Add
# ============================================================================


# ============================================================================
# Function:    GetOSInfo
# Description: Takes a target and an OS check and first obtains the FID and 
#              home_dir for the call to the check_os_target routine
# Returns:     The result of the OS check query
# ============================================================================
def GetOSInfo(InventoryID, target, check, result_column, TargetLogger):
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
  
          value=check_os(InventoryID, owner, host, homedir, check, result_column, TargetLogger)
          if "FAILED" in value:
            TargetLogger.error('Target: %s Owner: %s Command: %s Result: $s ', str(target), str(owner), str(check), str(value))    
            value=''
 
    
      except cx_Oracle.DatabaseError as exc:
      # If there was a database error we need the ORA-##### error
          error, = exc.args
          oraerr=str(error.code)
          TargetLogger.error('Target: %s   Status: ORA- %s  Message: %s', str(target), oraerr, str(error))    

    return value

# ============================================================================
# END GetOSInfo
# ============================================================================


# ============================================================================
# Function:    UpdateColumn
# Description: Checks the Inventory database for 1 target and 1 attribute / column
# Input:       InventoryID, column_name, value
# Ouptut:      Updates dbc_target attribute if it has changed 
# RC=-1   Target no longer exists
# RC=0    No change
# RC=1    Target updated
# ============================================================================
def UpdateColumn(inventoryid, column_name, value, TargetLogger):
    result = 0

    if column_name == 'hostname' or column_name == 'instancename' :
        TargetLogger.info('InventoryID: %s Column: %s Old Value: %s New Value: %s ',\
                                inventoryid, column_name, Curr_Value, value)
        TargetLogger.error('TO CHANGE HOSTNAME OR INSTANCENAME PLEASE UPDATE MANUALLY') 
        return 0


 
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

        if Curr_Value == value or value=='UNKNOWN' :
            TargetLogger.info('No change in Target Info')
        else:
            insert_cursor = postgres_conn.cursor()
            if column_name == 'blocksize' or column_name == 'port' :
              INSERT_STMT='UPDATE public.dbc_target set '+column_name+'='+ str(value) +' where inventoryid=' + str(inventoryid)
            else:
              INSERT_STMT='UPDATE public.dbc_target set '+column_name+'=\''+ str(value) + '\' where inventoryid=' + str(inventoryid)
             
            try:
                insert_cursor.execute(INSERT_STMT)
                # Make the changes to the database persistent
                postgres_conn.commit()

            except (psycopg2.DatabaseError, psycopg2.IntegrityError, psycopg2.DataError, psycopg2.InternalError)   as exc:
                error, = exc.args
                TargetLogger.error('Error updating target: %s Column_name %s from %s to %s', \
                                    inventoryid, column_name, Curr_Value, value )
                result=-1
         
            except Exception as exc:
                error, = exc.args
                TargetLogger.error('Error updating target: %s Column_name: %s Error:  %s ', \
                                    inventoryid, column_name, str(error))
                result=-1

            else:
                result=1

        postgres_conn.close()

    return result

# ============================================================================
# END UpdateColumn
# ============================================================================



# ============================================================================
# Function:    Update
# Description: Recheck an item in the inventory ie dbc_target.
# Input:       Takes a target in the format of InventoryID, host, instance
# Ouptut:      Updates dbc_target attributes that have changed. 
# RC=-1   Target no longer exists
# RC=0    No change
# RC=1    Target updated
# ============================================================================


def Update(InventoryID, host, instance, TargetLogger):
  RC=0  
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
  DBConnection='TRUE'
  for check, check_type, result_column in all_checks:
      value=-1
      if check_type == 'DB' and DBConnection == 'TRUE' :
          # if (VENDOR == 'ORACLE') or (VENDOR == '%') :
             if "+ASM" not in instance:
                 value=GetDBInfo(instance+'_'+host, check, TargetLogger)
                 NotExist=['12545','12541','12543','12514','12505']
                 NoAccess=['1017','1045', '1033', '28000', '28001']
                 if value in NotExist or value in NoAccess :
                   DBConnnection='FALSE'
                   value = -1

      elif check_type == 'OS':
          value=GetOSInfo(InventoryID, instance+'_'+host, check, result_column, TargetLogger)

      if value != -1 :
        COL_RC=UpdateColumn(InventoryID, result_column, value, TargetLogger )

    # Lastly Update the Last Updated Column
  UpdateColumn(InventoryID, "lastcheckdate", str(datetime.now()), TargetLogger)

  return
  
# ============================================================================
# END Update  
# ============================================================================


# ============================================================================
# Function:    Check_OS
# Description: Performs an operating system based check.  
#              i.e. login as the Oracle owner and run a unix command
# Input:       ID, owner, host, homedir, check, result_column, TargetLogger
# Ouptut:      Returns the output of the command as a string.
# Future       Make the timer timeout a parameter for each check
# ============================================================================

def check_os(ID, owner, host, homedir, command, result_column, TargetLogger):
    result=''
    ssh_connection = paramiko.SSHClient()
    ssh_connection.load_system_host_keys()
    ssh_connection.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    timer = threading.Timer(10,ssh_connection.close)
    timer.start()    # start counting right before connecting to the database

    try:
        TargetLogger.info("Connecting to %s as %s to run %s ", host, owner, command)
        ssh_connection.connect(host, 22, owner) 

    except paramiko.ssh_exception.AuthenticationException:
        TargetLogger.error("Authentication failed, Host: %s    Owner: %s", host, owner)
        result='FAILED: ssh_exception.AuthenticationException'
        
    except paramiko.ssh_exception.BadHostKeyException as badHostKeyException:
        TargetLogger.error("Unable to verify server's host key: %s", badHostKeyException)
        result='FAILED: ssh_exception.BadHostKeyException'

    except    paramiko.ssh_exception.SSHException as sshException:
        result='FAILED: ssh_exception.SSHException'
        TargetLogger.info("Returning result from OS command: %s ", result )
        TargetLogger.error("Unable to establish SSH connection: %s",    sshException)

    except Exception as sshException:
        TargetLogger.error("General Exception in os command: %s ",    sshException)
        result='FAILED: general_ssh_exception'

    else:
        try: 
            if result_column == 'swrelease':
               command = homedir + '/OPatch/' + command

            TargetLogger.info("Running %s as %s on %s ", command, owner, host)
            stdin, stdout, stderr = ssh_connection.exec_command(command, get_pty=True)

            result_row = stdout.readlines()
            result_err = stderr.readlines()

            if result_row :
                result=str(result_row[len(result_row)-1].strip())
                if result=="logout" :
                  result=str(result_row[len(result_row)-2].strip())
                TargetLogger.info("InventoryID: %s result: %s result_column: %s ", \
                            ID, result, result_column)   

            if result_err :
                TargetLogger.info("OS Check Errors: %s ", result_err )
                result='FAILED: command failed'

            timer.cancel()    # cancel the connection thread if it's still alive after 30 seconds

        except  Exception as sshException:
            TargetLogger.error("Unable to run: %s on host: %s as %s Result: %s",   \
                               command, host, owner, sshException)
            result='FAILED: command failed'
            
    finally:
        ssh_connection.close() 
        TargetLogger.info("Returning result from OS command: %s ", result )

    return result

# ============================================================================
# END check_os   
# ============================================================================
