import paramiko  # Allows us to ssh to the target hosts
import cx_Oracle  # https://oracle.github.io/python-cx_Oracle/
import psycopg2  # https://pypi.org/project/psycopg2/
import psycopg2.extras  # This gives access to the psycopg2 error messages
import sys  # for some reason this is not included by default
import threading  # Allows us to time and kill hung db connections
import select
# from numpy import asarray # convert sql result tuples to python arrays
from datetime import date, datetime  # for some reason this is not included by default
from decouple import config  # Allows us to read .env

# Set Environment and Global Variables
DBC_USER = config('DBC_USER')
DBC_PWD = config('DBC_PWD')
SYS_USER = config('SYS_USER')
SYS_PWD = config('SYS_PWD')
OLD_DBC_PWD = config('OLD_DBC_PWD')
ORACLE_BASE = config('ORACLE_BASE')
ORACLE_HOME = config('ORACLE_HOME')
TNS_ADMIN = config('TNS_ADMIN')
LOG_DIR = config('LOG_DIR')
PKEY = config('PKEY')
NOT_EXIST = [12154, 12521, 12545, 12541, 12543, 12514, 12505, 12547, 28860]
NO_ACCESS = [1017, 1045, 1033, 15000, 28000, 28001]

CODIFYWEB_DIR = config('CODIFYWEB_DIR')
sys.path.append(CODIFYWEB_DIR)
import inventory

def connect(hostname, instance_name, owner, handler, target_logger, call_timeout=10000):
    """
    Connects to a target using the specified handler.
    :param hostname:
    :param instance_name:
    :param owner:
    :param handler:
    :param target_logger:
    :returns rc: Return code that indicates whether connection was successful (1 = Success, 0 = Fail, -1 = Could not connect)
    """
    target_logger.debug("Connecting to: %s with %s as %s", hostname, handler, owner)
    rc = 0
    curr_connection = ''
    my_dsn = instance_name + '_' + hostname

    try:
        if handler == 'Oracle' or handler == 'PLSQL':
            curr_connection = cx_Oracle.connect(DBC_USER, DBC_PWD, my_dsn)
            curr_connection.callTimeout = call_timeout  # Connection timeout is milliseconds
        elif handler == 'ssh':
            curr_connection = paramiko.SSHClient()
            curr_connection.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            if PKEY != 'NONE' :
                private_key = paramiko.RSAKey.from_private_key_file(PKEY)
                curr_connection.connect(hostname=hostname, port=22, username=owner, timeout=call_timeout/100, \
                                        banner_timeout=10, auth_timeout=10, pkey=private_key)
            else :
                curr_connection.connect(hostname=hostname, port=22, username=owner, timeout=call_timeout/100, \
                                        password=DBC_PWD, banner_timeout=10, auth_timeout=10)
        elif handler == 'OMS':
            curr_connection = cx_Oracle.connect(DBC_USER, DBC_PWD, 'DVOMS_caddld-593')
            curr_connection.callTimeout = call_timeout  # Oracle Connection timeout is milliseconds
        elif handler == 'ASM':
            if instance_name == '+ASM':
                curr_connection = cx_Oracle.connect(DBC_USER, DBC_PWD, my_dsn, mode=cx_Oracle.SYSASM)
                curr_connection.callTimeout = call_timeout  # Oracle Connection timeout is milliseconds
        elif handler == 'SYSDBA':
            curr_connection = cx_Oracle.connect(SYS_USER, SYS_PWD, my_dsn, mode=cx_Oracle.SYSDBA)
            curr_connection.callTimeout = call_timeout  # Oracle Connection timeout is milliseconds  - allow 35 seconds
        elif handler == 'Postgres':
            my_dsn = "dbname=" + instance_name + " user=" + DBC_USER + " password=" + DBC_PWD + " host=" + hostname
            curr_connection = psycopg2.connect(my_dsn)

        # Still here means connected
        rc = 1
        target_logger.debug("Connected to: %s with %s ", hostname, handler)
        timer = threading.Timer(call_timeout, curr_connection.close)
        timer.start()  # start counting right before connecting - wait longer than the longest ssh timeout value


#   Deal with possible errors
    except cx_Oracle.Error as exc:
        error, = exc.args
        target_logger.error("DatabaseError-Code: %s %s ", error.code, error.message)
        rc = error.code
        if curr_connection:
            curr_connection.close()
            curr_connection = ''

    except paramiko.ssh_exception.AuthenticationException:
        target_logger.error("Authentication failed, Host: %s    Owner: %s", hostname, owner)
        rc = "AuthenticationException"
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

# END connect

def get_info(check, handler, connection, target_logger, call_timeout=2000):
    """
    Checks the target database for a single specific key attribute
    :param check:
    :param handler:
    :param connection:
    :param target_logger:
    :return: result: The result of the check query
    :return: rc: Return code that indicates whether connection was successful (1 = Success, 0 = Fail, -1 = Could not connect)
    """
    target_logger.debug('get_info with check=%s, handler=%s', check, handler)
    rc = 0
    result = ''

    if connection != '':
        if handler == 'ssh':
            rc, result = get_OS_info(check, connection, target_logger, call_timeout)
        elif handler == 'PLSQL':
            rc, result = get_PLSQL_info(check, connection, target_logger, call_timeout)
        else :
            #  handler == 'Oracle' or handler == 'ASM' or handler == 'OMS':
            rc, result = get_oracle_info(check, connection, target_logger, call_timeout)

    target_logger.debug('get_info returning Result: %s (rc = %s)', str(result), str(rc))
    return rc, result

# END get_info


def get_oracle_info(check, connection, target_logger, call_timeout=6000):
    """
    Checks the target database for a single specific key attribute
    :param check:
    :param connection:
    :param target_logger:
    :return: result: The result of the check query
    :return: rc: Return code that indicates whether connection was successful (1 = Success, 0 = Fail, -1 = Could not connect)
    """
    target_logger.debug('get_oracle_info with check=%s', check)
    rc = 0
    value = ''

    try:
        timer = threading.Timer(call_timeout, connection.cancel())
        db_info_cursor = connection.cursor()
        timer.start()  # start counting right before connecting to the database
        db_info_cursor.execute(check)
        row = db_info_cursor.fetchone()
        if row:
            # value = str(value[0]).strip()
            value = ' '.join([str(item) for item in row])
            rc = 1
        else:
            value = ''

    except cx_Oracle.Error as exc:
        # Now Handle all the things that could go wrong with this request
        # If there was a database error, return it as the value
        error, = exc.args
        oracle_err = str(error.code)
        target_logger.error('GetOracleInfo Error: ORA-%s  Message: %s', oracle_err, str(error))
        rc = 0
        value = error.code

    finally :
        try :
            timer.cancel()  # cancel the timer before leaving this function
        except :
            target_logger.error('GetOracleInfo Error: Timer not established')

    target_logger.debug('get_oracle_info returning Result: %s (rc = %s)', str(value), str(rc))
    return rc, value

# END get_oracle_info


def get_PLSQL_info(check, connection, target_logger, call_timeout):
    """
    Checks the target database for a single specific key attribute
    :param check:
    :param connection:
    :param target_logger:
    :return: result: The result of the check query
    :return: rc: Return code that indicates whether connection was successful (1 = Success, 0 = Fail, -1 = Could not connect)
    """
    target_logger.debug('get_PLSQL_info with check = %s', check)
    rc = 1

    try:
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
            target_logger.info('get_PLSQL_info: Lines: %s Count %s ', lines_var, num_lines_var)
            num_lines = num_lines_var.getvalue()
            lines = lines_var.getvalue()[:num_lines]
            # for line in lines:
            #    print(line or "")
            if num_lines < chunk_size:
                break

        value = str(lines[0])

    except cx_Oracle.Error as exc:
        # Now Handle all the things that could go wrong with this request
        # If there was a database error, return it as the value
        error, = exc.args
        oracle_err = str(error.code)
        target_logger.error('get_PLSQL_info Error: ORA-%s  Message: %s', oracle_err, str(error))
        rc = 0
        value = error.code

    target_logger.debug('get_PLSQL_info returning Result: %s (rc = %s)', str(value), str(rc))
    return rc, value

# END get_PLSQL_info


def get_OS_info(check, connection, target_logger, call_timeout=2000):
    """
    Takes a target and an OS check and first obtains the FID and home_dir for the call to the check_os_target routine
    :param check:
    :param connection:
    :param target_logger:
    :return: result: The result of the OS check query
    :return: rc: Return code that indicates whether connection was successful (1 = Success, 0 = Fail, -1 = Could not connect)
    """
    target_logger.debug('get_OS_info with check = %s', check)
    result = ''
    rc = 0
    timer = threading.Timer(call_timeout/100, connection.close)
    timer.start()  # start counting right before connecting to the target

    try:

        target_logger.info("Running %s ", check)
        stdin, stdout, stderr = connection.exec_command(check, timeout=call_timeout, get_pty=True)

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
            timeout = call_timeout / 100
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
        target_logger.debug("OS result length : %s ", str(len(stdout_chunks)))
        result = ''.join(str(stdout_chunks[len(stdout_chunks) - 1].decode("utf-8")).strip())
        result = result.replace('\n', ' ').replace('\r', '').replace('logout', '')

        # close all the pseudofiles
        stdout.close()
        stderr.close()

    except Exception as sshException:
        target_logger.error("Unable to run check: %s Result: %s", check, sshException)
        result = 'FAILED: os command failed'
        rc = -1

    finally:
        target_logger.info("Returning result from OS command: %s", result)
        timer.cancel()  # start counting right before connecting to the database

    return rc, result

# END get_OS_info


def update_column(inventory_id, column_name, value, target_logger):
    """
    Checks the Inventory database for 1 target and 1 attribute / column
    :param inventory_id:
    :param column_name:
    :param value:
    :param target_logger:
    :return: rc: Return code that indicates whether connection was successful (1 = Success, 0 = Fail, -1 = Could not connect)
    """
    target_logger.debug('update_column with InventoryID: %s Column: %s New Value: %s ',
                        inventory_id, column_name, value)
    result = 0

    if column_name == 'hostname' or column_name == 'instance_name':
        target_logger.info('InventoryID: %s Column: %s New Value: %s ',
                           inventory_id, column_name, value)
        target_logger.error('TO CHANGE HOSTNAME OR INSTANCENAME PLEASE UPDATE MANUALLY')
        return 0

    if value != '' and value != 'UNKNOWN':
        # ============================================================================
        # Get the old (current) value of the attribute in the inventory
        # and update the inventory only if anything has changed about the target
        # ============================================================================

        target_query = 'select ' + column_name + ' from targets where inventory_id = \'' + str(
            inventory_id) + '\''

        curr_value = inventory.exec_sql(target_query, 'ONE', target_logger)

        if isinstance(type(curr_value), type(None)):
            curr_value = ''
        else:
            curr_value = str(curr_value[0]).strip()

        target_logger.info('InventoryID: %s Column: %s Old Value: %s New Value: %s ',
                            inventory_id, column_name, curr_value, value)

        if curr_value == value or value == 'UNKNOWN':
            target_logger.info('No change in Target Info')
        else:
            if column_name == 'blocksize' or column_name == 'port':
                insert_stmt = 'update targets set ' + column_name + '=' + str(
                    value) + ' where inventory_id=' + str(inventory_id)
            else:
                insert_stmt = 'update targets set ' + column_name + '=\'' + str(
                    value) + '\' where inventory_id=' + str(inventory_id)

            result = inventory.exec_sql(insert_stmt, 'EXEC', target_logger)

    target_logger.debug('update_column returning result = %s', str(result))
    return result

# END update_column


def reject(host, vendor, instance, status, owner, home_dir, important_notes, target_type, target_logger):
    """
    :param host:
    :param vendor:
    :param instance:
    :param status:
    :param owner:
    :param home_dir:
    :param important_notes:
    :param target_type:
    :param target_logger:
    :return: result: the target info [host, vendor, instance, status, owner, home_dir]
    """
    target_logger.debug("Creating entry in target_rejects table with host: %s instance name: %s vendor: %s status: %s"
                        " owner: %s home_dir: %s important_notes: %s",
                        host, instance, vendor, status, owner, home_dir, important_notes)
    result = 0

    insert_stmt = """INSERT INTO target_rejects
                       (Inventory_Create, HostName, Instance_Name, vendor, status, owner, home_directory, important_notes)
                       VALUES (\'{}\', \'{}\', \'{}\', \'{}\', \'{}\', \'{}\', \'{}\', \'{}\'); """

    insert_stmt = f"{insert_stmt.format(date.today(), host, instance, vendor, status, owner, home_dir, important_notes)}"

    curr_value = inventory.exec_sql((insert_stmt,date.today(), host, instance, vendor, status,
                                         owner, home_dir, important_notes) ,'ONE', target_logger)

    target_logger.debug('Target Reject Result: %s', result)

    return result


# END Reject


def add(host, instance, container, DBID, owner, home_dir, status, port, target_type, target_logger):
    """
    Creates the initial Target entry in the DBC_Target table
    :param host, instance, etc...
    :return: the target ID
    """
    target_logger.debug("Adding entry in targets table with host: %s instance name: %s container: %s DBID: %s"
                        " owner: %s home_dir: %s status: %s port: %s target_type: %s",
                        host, instance, container, DBID, owner, home_dir, status, port, target_type)

    result = inventory.get_id(host, instance, target_logger)
    if result < 1:
        insert_stmt = """INSERT INTO targets
                       (Inventory_Create, Target_Type, HostName, Instance_Name, Container, Serial_Number, owner, home_dir, Vendor, Status, Port)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s); """

        RC = inventory.exec_sql((insert_stmt, (date.today(), target_type, host, instance, container,
                                             DBID, owner, home_dir, 'ORACLE', status, port)), 'ONE', target_logger)

        result = inventory.get_id(host, instance, target_logger)

        target_logger.info('Add target Result InventoryID: %s', result)

    return result

# END Add
