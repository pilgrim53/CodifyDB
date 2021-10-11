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
import select
# from numpy import asarray # convert sql result tuples to python arrays
from datetime import date, datetime # for some reason this is not included by default
from decouple  import config     # Allows us to read .env

# from update_targets import check_os # Allows us to reuse the os check function
import socket
import os
import Results
import Inventory
import check_oms

# ============================================================================
# Set DBTools Environment and Global Variables
# ============================================================================
DBC_USER = config('DBC_USER')
DBC_PWD = config('DBC_PWD')
OLD_DBC_PWD = config('OLD_DBC_PWD')
INV_USER = config('INV_USER')
INV_PWD = config('INV_PWD')
ORACLE_BASE = config('ORACLE_BASE')
ORACLE_HOME = config('ORACLE_HOME')
TNS_ADMIN = config('TNS_ADMIN')
LOG_DIR = config('LOG_DIR')
CODIFYDB_HOST = config('CODIFYDB_HOST')
CODIFYDB = config('CODIFYDB')
PKEY = config('PKEY')
INVENTORYDB = "dbname=" + CODIFYDB + " user=" + INV_USER + " password=" + INV_PWD + " host=" + CODIFYDB_HOST
NOT_EXIST = [12154, 12521, 12545, 12541, 12543, 12514, 12505, 12547, 28860]
NO_ACCESS = [1017, 1045, 1033, 15000, 28000, 28001]


# ============================================================================
# Function:     connect
# Description:  Connects to a target using the specified handler
# Input:        host_name, instance_name, handler
# Output:       None
# Returns:      Return Code and the connection if successful   1=Success
# ============================================================================

def connect(host_name, instance_name, owner, handler, target_logger):
    target_logger.debug("Connecting to: %s with %s as %s", host_name, handler, owner)
    rc = 0
    curr_connection = ''

    if handler == 'OMS':
        target_logger.info("Unhandled OMS check for database: %s", instance_name)

  elif Handler == 'ASM' :
    if InstanceName == '+ASM' :
      try:
          curr_connection = cx_Oracle.connect(DBC_USER, DBC_PWD, InstanceName+'_'+HostName, encoding="UTF-8", mode=cx_Oracle.SYSASM)
          curr_connection.callTimeout=35000    # Oracle Connection timeout is milliseconds  - allow 35 seconds
          RC = 1
          TargetLogger.debug("Connected to: %s with %s ", HostName, Handler)
      except cx_Oracle.DatabaseError as exc:
          error, = exc.args
          TargetLogger.error("DatabaseError-Code: %s %s ", error.code, error.message)
          RC=error.code
          if curr_connection :
            curr_connection.close()  
            curr_connection = ''
    

  elif Handler == 'Oracle' or Handler == 'PLSQL' :
    try:
        curr_connection = cx_Oracle.connect(DBC_USER, DBC_PWD, InstanceName+'_'+HostName, encoding="UTF-8")
        curr_connection.callTimeout=35000    # Oracle Connection timeout is milliseconds  - allow 35 seconds
        RC = 1
        TargetLogger.debug("Connected to: %s with %s ", HostName, Handler)
    except cx_Oracle.DatabaseError as exc:
        error, = exc.args
        TargetLogger.error("DatabaseError-Code: %s %s ", error.code, error.message)
        RC=error.code
        if curr_connection :
          curr_connection.close()  
          curr_connection = ''

  elif Handler == 'ssh' :
    curr_connection = paramiko.SSHClient()

    curr_connection.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    private_key = paramiko.RSAKey.from_private_key_file(PKEY)

    try:
        curr_connection.connect(hostname=HostName, port=22, username=Owner, timeout=15, \
                                banner_timeout=10, auth_timeout=10, pkey=private_key)

        TargetLogger.debug('Connection Established at: %s', str(datetime.now()))
        RC=1
        timer = threading.Timer(15,curr_connection.close)
        timer.start()    # start counting right before connecting - wait longer than the longest ssh timeout value

    except paramiko.ssh_exception.AuthenticationException:
        TargetLogger.error("Authentication failed, Host: %s    Owner: %s", HostName, Owner)
        RC="AuthenticationException"
        if curr_connection != '' :
          curr_connection.close()  
          curr_connection = ''

    except paramiko.ssh_exception.BadHostKeyException as badHostKeyException:
        TargetLogger.error("Unable to verify server's host key: %s", badHostKeyException)
        RC="BadHostKeyException"
        if curr_connection != '' :
          curr_connection.close()  
          curr_connection = ''

    except    paramiko.ssh_exception.SSHException as sshException:
        TargetLogger.error("Unable to establish SSH connection: %s",    sshException)
        RC="SSHException"
        if curr_connection != '' :
          curr_connection.close()  
          curr_connection = ''

    except Exception as sshException:
        TargetLogger.error("General Exception in os command: %s ",    sshException)
        result='FAILED: general_ssh_exception'
        RC="sshException"
        if curr_connection != '' :
          curr_connection.close()  
          curr_connection = ''

  TargetLogger.debug('Connection RC: %s', str(RC))

  return RC, curr_connection

# ============================================================================
# Function:    CreateDBC
# Description: Force the creation or recreation of the CLOUD_DBC database user
# Returns:     status of command 1=success, 0=fail, -1=could not run
# ============================================================================
def create_dbc(target, owner, target_logger):
    instance, host = target.split('_')
    result = -1
    target_logger.debug('Fix CLOUD_DBC on: %s', str(target))

    DBC_COMMAND = """. ./.bash_profile;    sqlplus / as sysdba <<sqlOUT ALTER SESSION SET "_oracle_script"=TRUE; 
    create user Cloud_DBC identified by "Just4Now" account unlock; ALTER USER CLOUD_DBC IDENTIFIED BY VALUES 
    'S:86DFBCB95B28142998C2C27D6CC6F29F1BFFD1D15E5F996DCAAB6E2F13B1;T 
    :BA8D9BE25142F60BFBB2DBE0658D594086E583252F18CBE7B1E05AB97F3A751A258C4019A3A7247B7545B4D230D9F085A7CB0038D47272070E0
    0FA586A4D4BB104BD778E6DE6339DAB20966392D66F4C' account unlock; ALTER USER CLOUD_DBC profile NOEXPIRE_PWD; grant dba 
    to Cloud_DBC; ALTER USER Cloud_DBC SET CONTAINER_DATA=ALL CONTAINER=CURRENT; exit sqlOUT """

    try:
        ssh_connection = paramiko.SSHClient()
        ssh_connection.load_system_host_keys()
        ssh_connection.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        timer = threading.Timer(30, ssh_connection.close)
        timer.start()  # start counting right before connecting to the database

        target_logger.info("Connecting to %s as %s ", host, owner)
        ssh_connection.connect(host, 22, owner)

  else:
    try:
      if owner != '':
        TargetLogger.info("Running %s as %s on %s ", DBC_COMMAND, owner, host)
        stdin, stdout, stderr = ssh_connection.exec_command(DBC_COMMAND, timeout=15, get_pty=True)

    else:
        try:
            if owner != '':
                target_logger.info("Running %s as %s on %s ", DBC_COMMAND, owner, host)
                stdin, stdout, stderr = ssh_connection.exec_command(DBC_COMMAND, timeout=30, get_pty=True)

                result_row = stdout.readlines()
                result_err = stderr.readlines()
                target_logger.info("OS Check stdout: %s ", str(result_row))
                target_logger.info("OS Check Errors: %s ", str(result_err))
                result = 1

        except Exception as sshException:
            target_logger.error("Unable to run on host: %s as %s Result: %s",
                                host, owner, sshException)
            result = 0

    finally:
        ssh_connection.close()

    return result


# ============================================================================
# Function:    UpdatePassword
# Description: Force the creation or recreation of the CLOUD_DBC database user
# Returns:     None
# ============================================================================
def update_password(target, target_logger):
    instance, host = target.split('_')
    value = 0
    target_logger.debug('Fix CLOUD_DBC on: %s', str(target))

    try:
        connection = cx_Oracle.connect(DBC_USER, OLD_DBC_PWD, target, encoding="UTF-8")
        timer = threading.Timer(15, connection.cancel)
        db_info_cursor = connection.cursor()
        check = "select 1 from dual"
        try:
            timer.start()  # start counting right before connecting to the database
            db_info_cursor.execute(check)
            value = db_info_cursor.fetchone()
            value = str(value[0]).strip()
            target_logger.debug('Connected to: %s', str(target))

            PWD_UPDATE = 'alter user cloud_dbc identified by ' + DBC_PWD
            db_info_cursor.execute(PWD_UPDATE)

        except cx_Oracle.DatabaseError as exc:
            error, = exc.args
            oracle_error = str(error.code)

            target_logger.error('Target: %s   Status: ORA- %s  Message: %s', str(target), oracle_error, str(error))
            timer.cancel()  # cancel the timer before leaving this function

        connection.close()  # All done
        timer.cancel()  # cancel the timer before leaving this function

    # Handle all the things that could go wrong with this connection attempt
    except cx_Oracle.DatabaseError as exc:
        # If there was a database error we need the ORA-##### error
        # This might mean the database exists
        error, = exc.args
        oracle_error = str(error.code)
        target_logger.error('Target: %s   Status: ORA- %s  Message: %s', str(target), oracle_error, str(error))
        value = -1
        connection.close()  # All done

    return value


# ============================================================================
# END UpdatePassword
# ============================================================================
def GetInfo(check, handler, connection, TargetLogger):
  rc=0
  result=''

  if connection != '':
    if handler == 'Oracle' or handler == 'ASM' :
      rc, result=GetOracleInfo(check, connection, TargetLogger)
    elif handler == 'ssh' :
      rc, result=GetOSInfo(check, connection, TargetLogger)
    elif handler == 'PLSQL' :
      rc, result=GetPLSQLInfo(check, connection, TargetLogger)

# ============================================================================
# Function:    GetOracleInfo
# Description: Checks the target database for a single spcific key attribute
# Returns:     The result of the check query
#              RC=-1 means could not connect
#              RC=0 means the command failed
#              RC=1 success
# Future:   Make the check timeout a parameter and setting for each check
# ============================================================================
def GetOracleInfo(check, connection, TargetLogger):
  RC=-1
  value=''

  try:
    timer = threading.Timer(145,connection.cancel())
    db_info_cursor = connection.cursor()
    timer.start()  # start counting right before connecting to the database
    db_info_cursor.execute(check)
    value=db_info_cursor.fetchone()
    if value:
      value=str(value[0]).strip()
      RC=1
    else:
      value = ''

    except cx_Oracle.DatabaseError as exc:
        # Now Handle all the things that could go wrong with this request
        # If there was a database error, return it as the value
        error, = exc.args
        oracle_error = str(error.code)
        target_logger.error('GetOracleInfo Error: ORA-%s  Message: %s', oracle_error, str(error))
        rc = 0
        value = error.code

    except cx_Oracle.OperationalError as exc:
        error, = exc.args
        oracle_error = str(error.code)
        target_logger.error('GetOracleInfo Error: ORA-%s  Message: %s', oracle_error, str(error))
        rc = 0
        value = error.code

    timer.cancel()  # cancel the timer before leaving this function
    target_logger.info('GetOracleInfo returning Result: %s', str(value))

  return RC, value
# ============================================================================
# END GetOracleInfo
# ============================================================================

# ============================================================================
# Function:    GetASMInfo
# Description: Checks the target database for a single spcific key attribute
# Returns:     The result of the check query
#              RC=-1 means could not connect
#              RC=0 means the command failed
#              RC=1 success
#Future:   Make the check timeout a parameter and setting for each check
# ============================================================================
def GetASMInfo(check, connection, TargetLogger):
  RC=-1
  value=''

  try:
    timer = threading.Timer(145,connection.cancel())
    db_info_cursor = connection.cursor()
    timer.start()  # start counting right before connecting to the database
    db_info_cursor.execute(check)
    value=db_info_cursor.fetchone()
    if value:
      value=str(value[0]).strip()
      RC=1
    else:
      value = ''

  except cx_Oracle.DatabaseError as exc:
  # Now Handle all the things that could go wrong with this request
  # If there was a database error, return it as the value
    error, = exc.args
    oraerr=str(error.code)
    TargetLogger.error('GetOracleInfo Error: ORA-%s  Message: %s',  oraerr, str(error))
    RC=0
    value=error.code

  except cx_Oracle.OperationalError as exc:
    error, = exc.args
    oraerr=str(error.code)
    TargetLogger.error('GetOracleInfo Error: ORA-%s  Message: %s',  oraerr, str(error))
    RC=0
    value=error.code

  timer.cancel()  # cancel the timer before leaving this function
  TargetLogger.info('GetOracleInfo returning Result: %s', str(value))

  return RC, value
# ============================================================================
# END GetASMInfo
# ============================================================================

def GetPLSQLInfo(check, connection, TargetLogger):
  TargetLogger.info('GetPLSQLInfo:  %s', check)
  RC=1
  db_info_cursor = connection.cursor()
  db_info_cursor.callproc("dbms_output.enable")
  db_info_cursor.execute(check)

  # tune this size for your application
  chunk_size = 100

  # create variables to hold the output
  lines_var = db_info_cursor.arrayvar(str, chunk_size)
  num_lines_var = db_info_cursor.var(int)
  num_lines_var.setvalue(0, chunk_size)

  # fetch the text that was added by PL/SQL
  while True:
    db_info_cursor.callproc("dbms_output.get_lines", (lines_var, num_lines_var))
    TargetLogger.info('GetPLSQLInfo: Lines:  %s Count %s ', lines_var, num_lines_var)
    num_lines = num_lines_var.getvalue()
    lines = lines_var.getvalue()[:num_lines]
    for line in lines:
        print(line or "")
    if num_lines < chunk_size:
        break

  value=lines

  return RC, value

# ============================================================================
# END GetDBInfo
# ============================================================================


# ============================================================================
# Function:    Scan
# Description: Attempts to acquire new targets by scanning a list of potential
#              targets.   If a target is found, the inventory database is
#              checked to see if it is already a known target.
# Input:       Takes target in the format of host_instance, owner, home_dir, port
# Output:      RC=0  If the target exists but login is unsuccessful
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
def Scan(target, owner, port, TARGETTYPE, TargetLogger):

  inventoryid=0
  RC = 0

  # host, instance=target.split('_')    # needed for oracle_discovery.ksh v1.0
  instance, host=target.split('_')
  inventoryid=Inventory.GetID(host, instance, TargetLogger)
  if inventoryid > 0 :
    owner=Inventory.GetAttribute(inventoryid, target, 'owner', TargetLogger)

  if TARGETTYPE == 'Database' :
    # Try a default connection to this target first. Chances are "we know dis".
    RC, value=GetInfo(target, "select \'1\' from dual", TargetLogger)

    if value in NoAccess :
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
       ping_result=os.system('ping %s -4 -c 4 -w 10 >/dev/null ' % (host))     # Ping 4 times or 10 seconds, whichever comes first

       if ping_result < 1 :
           RC = 0
           TargetLogger.info('Host: %s is pingable.', host)

           if TARGETTYPE == "Database":

             try:
               target_dsn = cx_Oracle.makedsn(host, port, service_name=instance)
               connection = cx_Oracle.connect(user=DBC_USER, password=DBC_PWD, dsn=target_dsn)
               connection.callTimeout=35000   # Oracle connection timeout is milliseconds. allow 35 seconds for checks
               timer = threading.Timer(35,connection.cancel)
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

           elif TARGETTYPE == "Server":
             TargetLogger.debug('Found an active server to add %s', host)


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
# Output:      Returns a boolean if its new and the target info
#              [host, vendor, instance, status, owner, home_dir]
# ============================================================================
def reject(host, vendor, instance, status, owner, home_dir, important_notes, target_type, target_logger):
    result = 0
    postgres_conn = psycopg2.connect(INVENTORYDB)
    insert_cursor = postgres_conn.cursor()
    insert_stmt = """INSERT INTO public.dbc_target_rejects
                       (InventoryCreate, HostName, InstanceName, vendor, status, owner, homedirectory, importantnotes)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s); """

    try:
        insert_cursor.execute(insert_stmt,
                              (date.today(), host, instance, vendor, status, owner, home_dir, important_notes))
        # Make the changes to the database persistent
        postgres_conn.commit()

    except (psycopg2.DatabaseError, psycopg2.IntegrityError, psycopg2.DataError, psycopg2.InternalError) as exc:
        error, = exc.args
        target_logger.error('Error inserting reject record: %s %s %s ', str(host), str(instance), str(error))
        result = -1

    else:
        result = 1
        target_logger.info('Rejected new target: %s %s  ', str(host), str(instance))

    target_logger.debug('Target Reject Result: %s', result)

    postgres_conn.close()

    return result

# ============================================================================
# END Reject
# ============================================================================


# ============================================================================
# Function:    Add
# Description: Creates the initial Target entry in the DBC_Target table
# Input:       Takes target in the format of host, instance, container, port
# Output:      Returns a boolean if its new and the target info
#              [instance,host,DBCreateDate,DB_ID,status, port]
# ============================================================================
def add(host, instance, container, DB_ID, owner, home_dir, status, port, target_type, target_logger):
    result = 0
    count = 0

    postgres_conn = psycopg2.connect(INVENTORYDB)
    result = Inventory.get_id(host, instance, target_logger)
    if result < 1:

        insert_cursor = postgres_conn.cursor()
        insert_stmt = """INSERT INTO public.dbc_target (InventoryCreate, TargetType, HostName, InstanceName, 
        Container, SerialNumber, owner, home_directory, Vendor, Status, Port) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 
        %s, %s, %s); """

        try:
            insert_cursor.execute(insert_stmt, (
                date.today(), target_type, host, instance, container, DB_ID, owner, home_dir, 'ORACLE', status, port))
            # Make the changes to the database persistent
            postgres_conn.commit()

        except (psycopg2.DatabaseError, psycopg2.IntegrityError, psycopg2.DataError, psycopg2.InternalError) as exc:
            error, = exc.args
            target_logger.error('Error inserting new target: %s %s %s ', str(host), str(instance), str(error))
            result = -1

        except Exception as exc:
            error, = exc.args
            target_logger.error('Exception occurred inserting target: %s %s Container: %s %s',
                                str(host), str(instance), str(container), str(error))
            result = -1

        else:
            result = Inventory.get_id(host, instance, target_logger)

        target_logger.info('Add target Result InventoryID: %s', result)

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
def get_os_info(check, connection, target_logger):
  result=''
  RC=0
  timer = threading.Timer(15,connection.close)
  timer.start()    # start counting right before connecting to the database

  try:

    TargetLogger.info("Running %s ", check)
    stdin, stdout, stderr = connection.exec_command(check, timeout=15, get_pty=True)

    # get the shared channel for stdout/stderr/stdin
    channel = stdout.channel

    # we do not need stdin.
    stdin.close()
  
    # indicate that we're not going to write to that channel anymore
    channel.shutdown_write()
  
    # read stdout/stderr in order to prevent read block hangs
    stdout_chunks = []
    stdout_chunks.append(stdout.channel.recv(len(stdout.channel.in_buffer)))
    # chunked read to prevent stalls
    while not channel.closed or channel.recv_ready() or channel.recv_stderr_ready():
        # stop if channel was closed prematurely, and there is no data in the buffers.
        TargetLogger.debug('Reading stdout at: %s', str(datetime.now()))
        timeout=15
        got_chunk = False
        readq, _, _ = select.select([stdout.channel], [], [], timeout)
        for c in readq:
            if c.recv_ready():
                stdout_chunks.append(stdout.channel.recv(len(c.in_buffer)))
                got_chunk = True
            if c.recv_stderr_ready():
                # make sure to read stderr to prevent stall
                stderr.channel.recv_stderr(len(c.in_stderr_buffer))
                got_chunk = True
        '''
        1) make sure that there are at least 2 cycles with no data in the input buffers in order to not exit too early (i.e. cat on a >200k file).
        2) if no data arrived in the last loop, check if we already received the exit code
        3) check if input buffers are empty
        4) exit the loop
        '''
        if not got_chunk \
            and stdout.channel.exit_status_ready() \
            and not stderr.channel.recv_stderr_ready() \
            and not stdout.channel.recv_ready():
            # indicate that we're not going to read from this channel anymore
            stdout.channel.shutdown_read()
            # close the channel
            stdout.channel.close()
            break    # exit as remote side is finished and our bufferes are empty


    RC=stdout.channel.recv_exit_status()
    if RC==0: RC=1
    TargetLogger.info("OS result length : %s ", str(len(stdout_chunks)))
    result=''.join(str(stdout_chunks[len(stdout_chunks)-1].decode("utf-8")).strip())

    # result_list=[ str(v) for lst in stdout_chunks for key, value in lst.decode('utf-8').items() ]
    # TargetLogger.info("OS result length: %s result: %s", str(len(result_list)), str(result_list) )

    if stderr :
      TargetLogger.info("OS Check Errors: %s ", stderr )

    # if result != '' :
      # result=str(result[2].strip())
      #if result=="logout" :
      #  result=str(result[len(result)-2].strip())

    # close all the pseudofiles
    stdout.close()
    stderr.close()

  finally:
    TargetLogger.info("Returning result from OS command: %s ", result )
    timer.cancel()    # start counting right before connecting to the database

    return rc, result

# ============================================================================
# END GetOSInfo
# ============================================================================


# ============================================================================
# Function:    UpdateColumn
# Description: Checks the Inventory database for 1 target and 1 attribute / column
# Input:       inventory_ID, column_name, value
# Output:      Updates dbc_target attribute if it has changed
# RC=-1   Target no longer exists
# RC=0    No change
# RC=1    Target updated
# ============================================================================
def update_column(inventory_id, column_name, value, target_logger):
    result = 0

    if column_name == 'hostname' or column_name == 'instancename':
        target_logger.info('InventoryID: %s Column: %s New Value: %s ', \
                           inventory_id, column_name, value)
        target_logger.error('TO CHANGE HOSTNAME OR INSTANCENAME PLEASE UPDATE MANUALLY')
        return 0

    if value != '':
        # ============================================================================
        # Open a connection to the Inventory Database
        # Update the results if anything has changed about the target (i.e. version or logmode)
        # ============================================================================

        postgres_conn = psycopg2.connect(INVENTORYDB)
        select_cursor = postgres_conn.cursor()
        TARGET_QUERY = 'select ' + column_name + ' from public.DBC_Target where inventoryid = \'' + str(
            inventory_id) + '\''
        target_logger.info('QUERY: %s', TARGET_QUERY)

        try:
            # Get just the info about the target for comparison
            select_cursor.execute(TARGET_QUERY)
            curr_value = select_cursor.fetchone()

            if type(curr_value) == type(None):
                curr_value = ''
            else:
                curr_value = str(curr_value[0]).strip()

            target_logger.info('InventoryID: %s Column: %s Old Value: %s New Value: %s ',
                               inventory_id, column_name, curr_value, value)

        except (psycopg2.DataError, psycopg2.DatabaseError, psycopg2.IntegrityError, psycopg2.InternalError) as exc:
            error, = exc.args
            error_msg = psycopg2.errors.lookup(exc.pgcode)
            target_logger.error('Failed to get %s from InventoryID: %s  DataError: %s',
                                column_name, str(inventory_id), str(error_msg))

        if curr_value == value or value == 'UNKNOWN':
            target_logger.info('No change in Target Info')
        else:
            insert_cursor = postgres_conn.cursor()
            if column_name == 'blocksize' or column_name == 'port':
                insert_stmt = 'UPDATE public.dbc_target set ' + column_name + '=' + str(
                    value) + ' where inventoryid=' + str(inventory_id)
            else:
                insert_stmt = 'UPDATE public.dbc_target set ' + column_name + '=\'' + str(
                    value) + '\' where inventoryid=' + str(inventory_id)

            try:
                insert_cursor.execute(insert_stmt)
                # Make the changes to the database persistent
                postgres_conn.commit()

            except (psycopg2.DatabaseError, psycopg2.IntegrityError, psycopg2.DataError, psycopg2.InternalError) as exc:
                error, = exc.args
                target_logger.error('Error updating target: %s Column_name %s from %s to %s',
                                    inventory_id, column_name, curr_value, value)
                result = -1

            except Exception as exc:
                error, = exc.args
                target_logger.error('Error updating target: %s Column_name: %s Error:  %s ',
                                    inventory_id, column_name, str(error))
                result = -1

            else:
                result = 1

        postgres_conn.close()

    return result

# ============================================================================
# END UpdateColumn
# ============================================================================


# ============================================================================
# Function:    Update
# Description: Recheck an item in the inventory ie dbc_target.
# Input:       Takes a target in the format of inventory_id, host, instance
# Output:      Updates dbc_target attributes that have changed.
# RC=-1   Target no longer exists
# RC=0    No change
# RC=1    Target updated
# ============================================================================
def update(inventory_id, host, instance, owner, target_type, target_logger):
    rc = 0
    target_logger.debug("Update Target: InventoryID: %s Host: %s Instance: %s", inventory_id, host, instance)

    postgres_conn = psycopg2.connect(INVENTORYDB)
    target_cursor = postgres_conn.cursor()

    # Get ALL the checks to perform on these targets
    CHECK_QUERY = "select check_command, check_type, result_column from public.checklist where frequency='" \
                  + target_type + "' order by handler, priority"
    target_cursor.execute(CHECK_QUERY)
    all_checks = target_cursor.fetchall()
    target_logger.debug("All Checks: %s", all_checks)

    target_logger.info("Updating Host: %s Instance: %s", host, instance)

    if target_type == 'Database':
        # Try connecting to the database and get info if possible
        dbrc, db_connection = connect(host, instance, owner, 'Oracle', target_logger)

    osrc, os_connection = connect(host, instance, owner, 'ssh', target_logger)
    target_logger.info("connection result to Host: %s Result: %s", host, osrc)

    for check, check_type, result_column in all_checks:
        value = -1
        if check_type == 'DB' and db_connection != '':
            # if (VENDOR == 'ORACLE') or (VENDOR == '%') :
            if "+ASM" not in instance:
                rc, value = get_oracle_info(check, db_connection, target_logger)
                if value in NOT_EXIST or value in NO_ACCESS:
                    db_connnection = 'FALSE'
                    value = -1

      elif check_type == 'OS' and OSConnection :
        if osrc == 1:  
          RC, value=GetOSInfo(check, OSConnection, TargetLogger)

        if value != -1:
            col_rc = update_column(inventory_id, result_column, value, target_logger)

    # Lastly Update the Last Updated Column
    update_column(inventory_id, "lastcheckdate", str(datetime.now()), target_logger)

    if target_type == 'Server' and os_connection != '':
        os_connection.close

    if target_type == 'Database' and db_connection != '':
        db_connection.close

    return

# ============================================================================
# END Update
# ============================================================================


# ============================================================================
# Function:    Check_OS
# Description: Performs an operating system based check.
#              i.e. login as the Oracle owner and run a unix command
# Input:       id, owner, host, home_dir, check, result_column, target_logger
# Output:      Returns the output of the command as a string.
# Future       Make the timer timeout a parameter for each check
# ============================================================================

def check_os(id, owner, host, home_dir, command, result_column, target_logger):
    result = ''
    ssh_connection = paramiko.SSHClient()
    ssh_connection.load_system_host_keys()
    ssh_connection.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    timer = threading.Timer(15,ssh_connection.close)
    timer.start()    # start counting right before connecting to the database

    try:
        target_logger.info("Connecting to %s as %s to run %s ", host, owner, command)
        ssh_connection.connect(host, 22, owner)

    except paramiko.ssh_exception.AuthenticationException:
        target_logger.error("Authentication failed, Host: %s    Owner: %s", host, owner)
        result = 'FAILED: ssh_exception.AuthenticationException'

    except paramiko.ssh_exception.BadHostKeyException as badHostKeyException:
        target_logger.error("Unable to verify server's host key: %s", badHostKeyException)
        result = 'FAILED: ssh_exception.BadHostKeyException'

    except paramiko.ssh_exception.SSHException as sshException:
        result = 'FAILED: ssh_exception.SSHException'
        target_logger.info("Returning result from OS command: %s ", result)
        target_logger.error("Unable to establish SSH connection: %s", sshException)

    except Exception as sshException:
        target_logger.error("General Exception in os command: %s ", sshException)
        result = 'FAILED: general_ssh_exception'

    else:
        try:
            if result_column == 'swrelease':
                command = home_dir + '/OPatch/' + command

            target_logger.info("Running %s as %s on %s ", command, owner, host)
            stdin, stdout, stderr = ssh_connection.exec_command(command, timeout=30, get_pty=True)

            result_row = stdout.readlines()
            result_err = stderr.readlines()

            if result_row:
                result = str(result_row[len(result_row) - 1].strip())
                if result == "logout":
                    result = str(result_row[len(result_row) - 2].strip())
                target_logger.info("InventoryID: %s result: %s result_column: %s ",
                                   id, result, result_column)

            if result_err:
                target_logger.info("OS Check Errors: %s ", result_err)
                result = 'FAILED: command failed'

            timer.cancel()  # cancel the connection thread if it's still alive after 30 seconds

        except Exception as sshException:
            target_logger.error("Unable to run: %s on host: %s as %s Result: %s",
                                command, host, owner, sshException)
            result = 'FAILED: command failed'

    finally:
        ssh_connection.close()
        target_logger.info("Returning result from OS command: %s ", result)

    return result

# ============================================================================
# END check_os
# ============================================================================
