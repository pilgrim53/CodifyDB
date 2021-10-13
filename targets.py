# ============================================================================
# Import all the external Python modules that we need
# ============================================================================
import paramiko  # Allows us to ssh to the target hosts
import cx_Oracle  # https://oracle.github.io/python-cx_Oracle/
import psycopg2  # https://pypi.org/project/psycopg2/
import psycopg2.extras  # This gives access to the psycopg2 error messages
import sys  # for some reason this is not included by default
import logging  # https://docs.python.org/3/library/logging.html
import threading  # Allows us to time and kill hung db connections
import select
# from numpy import asarray # convert sql result tuples to python arrays
from datetime import date, datetime  # for some reason this is not included by default
from decouple import config  # Allows us to read .env

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
# Input:        host_name, instance_name, owner, handler, target_logger
# Output:       None
# Returns:      Return Code and the connection if successful   1=Success
# ============================================================================

def connect(host_name, instance_name, owner, handler, target_logger):
    target_logger.debug("Connecting to: %s with %s as %s", host_name, handler, owner)
    rc = 0
    curr_connection = ''

    if handler == 'OMS':
        target_logger.info("Unhandled OMS check for database: %s", instance_name)

    elif handler == 'ASM':
        if instance_name == '+ASM':
            try:
                curr_connection = cx_Oracle.connect(DBC_USER, DBC_PWD, instance_name + '_' + host_name,
                                                    encoding="UTF-8",
                                                    mode=cx_Oracle.SYSASM)
                curr_connection.callTimeout = 35000  # Oracle Connection timeout is milliseconds  - allow 35 seconds
                rc = 1
                target_logger.debug("Connected to: %s with %s ", host_name, handler)
            except cx_Oracle.DatabaseError as exc:
                error, = exc.args
                target_logger.error("DatabaseError-Code: %s %s ", error.code, error.message)
                rc = error.code
                if curr_connection:
                    curr_connection.close()
                    curr_connection = ''
    elif handler == 'Oracle' or handler == 'PLSQL':
        try:
            curr_connection = cx_Oracle.connect(DBC_USER, DBC_PWD, instance_name + '_' + host_name, encoding="UTF-8")
            curr_connection.callTimeout = 35000  # Oracle Connection timeout is milliseconds  - allow 35 seconds
            rc = 1
            target_logger.debug("Connected to: %s with %s ", host_name, handler)
        except cx_Oracle.DatabaseError as exc:
            error, = exc.args
            target_logger.error("DatabaseError-Code: %s %s ", error.code, error.message)
            rc = error.code
            if curr_connection:
                curr_connection.close()
                curr_connection = ''

    elif handler == 'ssh':
        curr_connection = paramiko.SSHClient()

        curr_connection.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        private_key = paramiko.RSAKey.from_private_key_file(PKEY)

        try:
            curr_connection.connect(hostname=host_name, port=22, username=owner, timeout=15, \
                                    banner_timeout=10, auth_timeout=10, pkey=private_key)

            target_logger.debug('Connection Established at: %s', str(datetime.now()))
            rc = 1
            timer = threading.Timer(15, curr_connection.close)
            timer.start()  # start counting right before connecting - wait longer than the longest ssh timeout value

        except paramiko.ssh_exception.AuthenticationException:
            target_logger.error("Authentication failed, Host: %s    Owner: %s", host_name, owner)
            rc = "AuthenticationException"
            if curr_connection != '':
                curr_connection.close()
                curr_connection = ''

        except paramiko.ssh_exception.BadHostKeyException as badHostKeyException:
            target_logger.error("Unable to verify server's host key: %s", badHostKeyException)
            rc = "BadHostKeyException"
            if curr_connection != '':
                curr_connection.close()
                curr_connection = ''

        except paramiko.ssh_exception.SSHException as sshException:
            target_logger.error("Unable to establish SSH connection: %s", sshException)
            rc = "SSHException"
            if curr_connection != '':
                curr_connection.close()
                curr_connection = ''

        except Exception as sshException:
            target_logger.error("General Exception in os command: %s ", sshException)
            result = 'FAILED: general_ssh_exception'
            rc = "sshException"
            if curr_connection != '':
                curr_connection.close()
                curr_connection = ''

        else:
            timer.cancel()  # cancel the connection thread if it's still alive after 30 seconds

    target_logger.debug('Connection rc: %s', str(rc))

    return rc, curr_connection


# ============================================================================
# END connect
# ============================================================================

# ============================================================================
# Function:    create_DBC
# Description: Force the creation or recreation of the CLOUD_DBC database user
# Returns:     status of command 1=success, 0=fail, -1=could not run
# ============================================================================


def create_DBC(target, owner, target_logger):
    instance, host = target.split('_')
    result = -1
    target_logger.debug('Fix CLOUD_DBC on: %s', str(target))

    DBC_COMMAND = """ . ./.bash_profile;    sqlplus / as sysdba <<sqlOUT
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

        timer = threading.Timer(30, ssh_connection.close)
        timer.start()  # start counting right before connecting to the database

        target_logger.info("Connecting to %s as %s ", host, owner)
        ssh_connection.connect(host, 22, owner)

    except paramiko.ssh_exception.AuthenticationException:
        target_logger.error("Authentication failed, Host: %s    Owner: %s", host, owner)
    except paramiko.TimeoutError:
        target_logger.error("Timeout connecting to Host: %s    Owner: %s", host, owner)
    else:
        try:
            if owner != '':
                target_logger.info("Running %s as %s on %s ", DBC_COMMAND, owner, host)
                stdin, stdout, stderr = ssh_connection.exec_command(DBC_COMMAND, timeout=15, get_pty=True)

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
# END create_DBC
# ============================================================================

# ============================================================================
# Function:    get_info
# Description: Checks the target database for a single specific key attribute
# Returns:     The result of the check query
#              RC=-1 means could not connect
#              RC=0 means the command failed
#              RC=1 success
# Future:   Make the check timeout a parameter and setting for each check
# ============================================================================


def get_info(check, handler, connection, target_logger):
    rc = 0
    result = ''

    if connection != '':
        if handler == 'Oracle' or handler == 'ASM':
            rc, result = get_oracle_info(check, connection, target_logger)
        elif handler == 'ssh':
            rc, result = get_OS_info(check, connection, target_logger)
        elif handler == 'PLSQL':
            rc, result = get_PLSQL_info(check, connection, target_logger)

    return rc, result


# ============================================================================
# END get_info
# ============================================================================

# ============================================================================
# Function:    get_oracle_info
# Description: Checks the target database for a single specific key attribute
# Returns:     The result of the check query
#              RC=-1 means could not connect
#              RC=0 means the command failed
#              RC=1 success
# Future:   Make the check timeout a parameter and setting for each check
# ============================================================================


def get_oracle_info(check, connection, target_logger):
    rc = -1
    value = ''

    try:
        timer = threading.Timer(145, connection.cancel())
        db_info_cursor = connection.cursor()
        timer.start()  # start counting right before connecting to the database
        db_info_cursor.execute(check)
        value = db_info_cursor.fetchone()
        if value:
            value = str(value[0]).strip()
            rc = 1
        else:
            value = ''

    except cx_Oracle.DatabaseError as exc:
        # Now Handle all the things that could go wrong with this request
        # If there was a database error, return it as the value
        error, = exc.args
        oracle_err = str(error.code)
        target_logger.error('GetOracleInfo Error: ORA-%s  Message: %s', oracle_err, str(error))
        rc = 0
        value = error.code

    except cx_Oracle.OperationalError as exc:
        error, = exc.args
        oracle_err = str(error.code)
        target_logger.error('GetOracleInfo Error: ORA-%s  Message: %s', oracle_err, str(error))
        rc = 0
        value = error.code

    timer.cancel()  # cancel the timer before leaving this function
    target_logger.info('GetOracleInfo returning Result: %s', str(value))

    return rc, value


# ============================================================================
# END get_oracle_info
# ============================================================================

# ============================================================================
# Function:    get_ASM_info
# Description: Checks the target database for a single specific key attribute
# Returns:     The result of the check query
#              RC=-1 means could not connect
#              RC=0 means the command failed
#              RC=1 success
# Future:   Make the check timeout a parameter and setting for each check
# ============================================================================
def get_ASM_info(check, connection, target_logger):
    rc = -1
    value = ''

    try:
        timer = threading.Timer(145, connection.cancel())
        db_info_cursor = connection.cursor()
        timer.start()  # start counting right before connecting to the database
        db_info_cursor.execute(check)
        value = db_info_cursor.fetchone()
        if value:
            value = str(value[0]).strip()
            rc = 1
        else:
            value = ''

    except cx_Oracle.DatabaseError as exc:
        # Now Handle all the things that could go wrong with this request
        # If there was a database error, return it as the value
        error, = exc.args
        oracle_err = str(error.code)
        target_logger.error('GetOracleInfo Error: ORA-%s  Message: %s', oracle_err, str(error))
        rc = 0
        value = error.code

    except cx_Oracle.OperationalError as exc:
        error, = exc.args
        oracle_err = str(error.code)
        target_logger.error('GetOracleInfo Error: ORA-%s  Message: %s', oracle_err, str(error))
        rc = 0
        value = error.code

    timer.cancel()  # cancel the timer before leaving this function
    target_logger.info('GetOracleInfo returning Result: %s', str(value))

    return rc, value


# ============================================================================
# END get_ASM_info
# ============================================================================

# ============================================================================
# Function:    get_PLSQL_info
# Description: Checks the target database for a single specific key attribute
# Returns:     The result of the check query
#              RC=-1 means could not connect
#              RC=0 means the command failed
#              RC=1 success
# Future:   Make the check timeout a parameter and setting for each check
# ============================================================================


def get_PLSQL_info(check, connection, target_logger):
    target_logger.info('GetPLSQLInfo:  %s', check)
    rc = 1
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
        target_logger.info('GetPLSQLInfo: Lines:  %s Count %s ', lines_var, num_lines_var)
        num_lines = num_lines_var.getvalue()
        lines = lines_var.getvalue()[:num_lines]
        for line in lines:
            print(line or "")
        if num_lines < chunk_size:
            break

    value = lines

    return rc, value


# ============================================================================
# END get_PLSQL_info
# ============================================================================

# ============================================================================
# Function:    get_OS_info
# Description: Takes a target and an OS check and first obtains the FID and
#              home_dir for the call to the check_os_target routine
# Returns:     The result of the OS check query
# ============================================================================


def get_OS_info(check, connection, target_logger):
    result = ''
    rc = 0
    timer = threading.Timer(15, connection.close)
    timer.start()  # start counting right before connecting to the database

    try:

        target_logger.info("Running %s ", check)
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
            target_logger.debug('Reading stdout at: %s', str(datetime.now()))
            timeout = 15
            got_chunk = False
            read_q, _, _ = select.select([stdout.channel], [], [], timeout)
            for c in read_q:
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
                break  # exit as remote side is finished and our buffers are empty

        rc = stdout.channel.recv_exit_status()
        if rc == 0:
            rc = 1
        target_logger.info("OS result length : %s ", str(len(stdout_chunks)))
        result = ''.join(str(stdout_chunks[len(stdout_chunks) - 1].decode("utf-8")).strip())

        # result_list=[ str(v) for lst in stdout_chunks for key, value in lst.decode('utf-8').items() ]
        # TargetLogger.info("OS result length: %s result: %s", str(len(result_list)), str(result_list) )

        if stderr:
            target_logger.info("OS Check Errors: %s ", stderr)

        # if result != '' :
        # result=str(result[2].strip())
        # if result=="logout" :
        #  result=str(result[len(result)-2].strip())

        # close all the pseudofiles
        stdout.close()
        stderr.close()

    except Exception as sshException:
        target_logger.error("Unable to run check: %s Result: %s", check, sshException)
        result = 'FAILED: os command failed'
        rc = -1

    finally:
        target_logger.info("Returning result from OS command: %s ", result)
        timer.cancel()  # start counting right before connecting to the database

    return rc, result


# ============================================================================
# END get_OS_info
# ============================================================================

# ============================================================================
# Function:    update_column
# Description: Checks the Inventory database for 1 target and 1 attribute / column
# Input:       InventoryID, column_name, value
# Output:      Updates dbc_target attribute if it has changed
# rc=-1   Target no longer exists
# rc=0    No change
# rc=1    Target updated
# ============================================================================
def update_column(inventory_id, column_name, value, target_logger):
    result = 0

    if column_name == 'hostname' or column_name == 'instancename':
        target_logger.info('InventoryID: %s Column: %s New Value: %s ',
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
        target_query = 'select ' + column_name + ' from public.DBC_Target where inventoryid = \'' + str(
            inventory_id) + '\''
        target_logger.info('QUERY: %s', target_query)

        try:
            # Get just the info about the target for comparison
            select_cursor.execute(target_query)
            curr_value = select_cursor.fetchone()

            if isinstance(type(curr_value), type(None)):
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
# END update_column
# ============================================================================