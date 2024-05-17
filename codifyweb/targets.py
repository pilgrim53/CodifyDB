import select
import threading  # Allows us to time and kill hung db connections
import time
# for some reason this is not included by default
from datetime import datetime

import cx_Oracle  # https://oracle.github.io/python-cx_Oracle/
import paramiko  # Allows us to ssh to the target hosts
# paramiko.common.logging.basicConfig(level=paramiko.common.DEBUG)
# import logging
# logging.basicConfig()
# logging.getLogger("paramiko").setLevel(logging.DEBUG) # for example

import psycopg2  # https://pypi.org/project/psycopg2/
import psycopg2.extras  # This gives access to the psycopg2 error messages
import pyodbc  # Allows us to connect to MS SQL Server
from decouple import config

from password_manager import PasswordManager

import sys
import os

class Target:
    CREDENTIALS = PasswordManager()
    TNS_NOT_EXIST = [1034, 12154, 12514, 12521, 12545, 12541, 12543, 12505,
                     12547, 28860]
    # Account locked, insufficient privs, wrong pwd, expired
    DBC_NO_ACCESS = [1017, 1031, 1045, 28000, 28001]
    # Archiver, Standby DB, Incompatible Version, Timeout
    TNS_OTHER = [257, 1033, 15000, 3134, 12170]
    OEM_USER = CREDENTIALS.get('OEM_USER')
    OEM_PWD = CREDENTIALS.get('OEM_PWD')
    WIN_PWD = CREDENTIALS.get('WIN_PWD')
    WIN_USER = CREDENTIALS.get('WIN_USER')
    MSSQL_PWD = CREDENTIALS.get('MSSQL_PWD')
    MSSQL_USER = CREDENTIALS.get('MSSQL_USER')
    DBC_USER = CREDENTIALS.get('DBC_USER')
    DBC_PWD = CREDENTIALS.get('DBC_PWD')
    SYS_USER = CREDENTIALS.get('SYS_USER')
    SYS_PWD = CREDENTIALS.get('SYS_PWD')
    TMP_PWD = CREDENTIALS.get('TMP_PWD')
    DBSNMP_PWD = CREDENTIALS.get('DBSNMP_PWD')
    PKEY = CREDENTIALS.get('PKEY')
    #  Backout pgp
    # OEM_USER = config('OEM_USER')
    # OEM_PWD = config('OEM_PWD')
    # WIN_PWD = config('WIN_PWD')
    # WIN_USER = config('WIN_USER')
    # MSSQL_PWD = config('MSSQL_PWD')
    # MSSQL_USER = config('MSSQL_USER')
    # DBC_USER = config('DBC_USER')
    # DBC_PWD = config('DBC_PWD')
    # SYS_USER = config('SYS_USER')
    # SYS_PWD = config('SYS_PWD')
    # TMP_PWD = config('TMP_PWD')
    # DBSNMP_PWD = config('DBSNMP_PWD')
    # PKEY = config('PKEY')
    ORACLE_BASE = config('ORACLE_BASE')
    ORACLE_HOME = config('ORACLE_HOME')
    TNS_ADMIN = config('TNS_ADMIN')
    LOG_DIR = config('LOG_DIR')

    SQL_DRIVER_NAME = 'FreeTDS'

    def __init__(self, inventory_id, hostname, instance_name, owner,
                 home_dir, target_type, vendor, sub_type, version, logger, container='',
                 serial_number='', status='', port=0, notes=''):
        self.inventory_id = inventory_id
        self.hostname = hostname
        self.instance_name = instance_name
        self.vendor = vendor
        self.sub_type = sub_type
        self.owner = owner
        self.home_dir = home_dir
        self.target_type = target_type
        self.container = container
        self.serial_number = serial_number
        self.status = status
        self.port = port
        self.notes = notes
        self.logger = logger
        self.connection = ''
        self.version = version
        from inventory import Inventory
        self.inventory = Inventory(self.logger)
        self.timer = None

    def __str__(self):
        target_dict = {
            'inventory_id': self.inventory_id,
            'hostname': self.hostname,
            'instance_name': self.instance_name,
            'vendor': self.vendor,
            'version': self.version,
            'sub_type':self.sub_type,
            'owner': self.owner,
            'home_dir': self.home_dir,
            'target_type': self.target_type,
            'container': self.container,
            'serial_number': self.serial_number,
            'status': self.status,
            'port': self.port
        }
        return str(target_dict)

    def connect(self, handler, inventory, call_timeout=240):
        """
        Connects to a target using the specified handler.
        :param fqdn:             The FQDN of the hostname.
        :param instance_name:    The name of the target on the host.
        :param owner:            The username with which to connect
                                 to the target.
        :param handler:          The name of the method for connecting.
                                 (ex ssh, oracle, etc..)
        :param call_timeout:     The max number of seconds to allow the
                                 connection to stay open.
        :returns rc, connection: A connection object and/or a return code
                                 that indicates whether connection was
                                 successful (1 = Success, 0 = Fail,
                                 -1 = Could not connect)
        """
        rc = 1

        self.logger.debug(f"Connecting to: {self.hostname} with {handler} ")

        if handler in ['Oracle', 'PLSQL', 'ASM', 'OMS', 'SYSDBA']:
            # make sure hostname is never fqdn during the "create_oracle_connection"
            fqdn = self.hostname
            self.hostname = self.hostname.split('.')[0].upper()
            rc = self.create_oracle_connection(handler,call_timeout,inventory)
            self.hostname = fqdn

        elif handler in ['ssh', 'oem_ssh', 'win_ssh', 'os_proc', 'oraoemag','rsh_978']:
            rc = self.create_ssh_connection(handler, call_timeout)

        elif handler == 'Postgres':
            rc = self.create_postgres_connection()

        elif handler == 'MSSQL':
            rc = self.create_mssql_connection()

        if self.connection != '':
            rc = 1
            self.logger.debug("Connected to: %s with %s ", self.hostname, handler)
            self.timer = threading.Timer(call_timeout, self.disconnect)
            self.timer.start()  # start counting on the timeout timer

        self.logger.debug('Connection rc: %s', str(rc))

        return rc

    def create_oracle_connection(self, handler, call_timeout, inventory):
        dsn = self.instance_name + '_' + self.hostname
        user = self.DBC_USER
        psswd = self.DBC_PWD
        conn_mode = cx_Oracle.DEFAULT_AUTH

        if handler == 'SYSDBA':
            conn_mode = cx_Oracle.SYSDBA
            user = self.SYS_USER
            psswd = self.SYS_PWD
        elif handler == 'ASM':
            conn_mode = cx_Oracle.SYSASM
        elif handler == 'OMS':
            user = 'OMS_VIEWER'
            dsn = 'DVOMS_CADDLD-593'

        rc = 1

        try:
            self.connection = cx_Oracle.connect(user, psswd, dsn, mode=conn_mode)
            # Connection timeout is milliseconds
            self.connection.callTimeout = call_timeout*1000

        except cx_Oracle.DatabaseError as exc:
            error, = exc.args
            self.logger.error(f"Connection Failed to Target DSN: {dsn} "
                              f"DatabaseError-Code: {error.code} "
                              f"MSG: {error.message}")
            rc = error.code

            if error.code in self.DBC_NO_ACCESS:
                self.logger.info(f"Attempting to restore "
                                 f"access to Target DSN: {dsn}")
                rc = self.restore_access_to_target_DSN(dsn, handler,
                                                       call_timeout)

            elif error.code in self.TNS_NOT_EXIST:
                rc = self.create_TNS_entry(dsn, call_timeout, inventory)
                self.logger.info(f"returned from tns_update with RC: {rc} ")
        
        self.logger.info(f"Exiting Oracle Connect with RC: {rc} ")

        if rc == 1 :
            rc2 = inventory.set_target_attribute(self.inventory_id, 'status', 'OPEN')
        else :
            rc2 = inventory.set_target_attribute(self.inventory_id, 'status', 'NOT OPEN')

        return rc

    def append_tns_entry(self, dsn, new_line):
        with open(self.TNS_ADMIN + '/tnsnames.ora', 'r+') as file:
            content = file.read()
            file.seek(0)
            file.write(new_line + content)
        self.logger.info(f"tnsnames.ora update complete {dsn}")

    def create_TNS_entry(self, dsn, call_timeout, inventory):
        rc = 0
        created = False
        for port in ['1521', '2349', '2350']:
            new_dsn = f"//{self.hostname}:{port}/{self.instance_name}"
            try:
                self.connection = cx_Oracle.connect(self.DBC_USER, self.DBC_PWD, new_dsn)
                self.connection.callTimeout = call_timeout*1000
                self.logger.info("Found working EZ Connect: %s ", dsn + '=' + new_dsn)
                rc = 1
                self.logger.info(f"Pre-pending new tns entry to tnsnames.ora for {dsn}")
                new_line = (f'# AUTOMATION {dsn}=(DESCRIPTION=(ADDRESS='
                            f'(PROTOCOL=TCP)(HOST={self.hostname})(PORT={port}'
                            f'))(CONNECT_DATA=(SERVICE_NAME='
                            f'{self.instance_name}))) \n')
                self.append_tns_entry(dsn, new_line)
                created = True
            except cx_Oracle.Error as exc:
                error, = exc.args
                if error.code in self.DBC_NO_ACCESS or error.code in self.TNS_OTHER:
                    rc = 1
                    self.logger.info(f"Appending new tns entry to tnsnames.ora for {dsn}")
                    new_line = (f'# AUTOMATION {dsn}=(DESCRIPTION=(ADDRESS='
                                f'(PROTOCOL=TCP)(HOST={self.hostname})'
                                f'(PORT={port}))(CONNECT_DATA='
                                f'(SERVICE_NAME={self.instance_name}))) \n')
                    self.append_tns_entry(dsn, new_line)
                else:
                    self.logger.error(f"Port Check Failed: {new_dsn} Code: {error.code} MSG: {error.message}")
            except Exception as e:
                self.logger.error(f"Unexpected error: {str(e)}")
        if not created:
            tns_entry = inventory.get_result(self.inventory_id, 'tns_entry')
            if tns_entry is None or tns_entry == '':
                self.logger.info(f"No other TNS Entry available yet for this instance: {self.instance_name}")
            else:
                try:
                    self.connection = cx_Oracle.connect(self.DBC_USER, self.DBC_PWD, tns_entry)
                    self.connection.callTimeout = call_timeout*1000
                    self.logger.info("Discovered TNS: %s IS WORKING for %s", tns_entry, dsn)
                    self.logger.info(f"Pre-pending new tns entry to tnsnames.ora for {dsn}")
                    new_line = '# AUTOMATION ' + tns_entry + '\n'
                    self.append_tns_entry(dsn, new_line)


                except cx_Oracle.Error as exc:
                    error, = exc.args
                    if error.code in self.DBC_NO_ACCESS \
                            or error.code in self.TNS_OTHER:
                        self.logger.info("Discovered TNS: %s IS WORKING for %s",
                                        tns_entry, dsn)
                        self.logger.info("Pre-pending new tns entry to "
                                        "tnsnames.ora for %s", dsn)
                        new_line = '# AUTOMATION ' + tns_entry + '\n'
                        rc = error.code
                        with open(self.TNS_ADMIN + '/tnsnames.ora', 'r+') \
                                as file:
                            content = file.read()
                            file.seek(0)
                            file.write(new_line + content)
                    else:
                        self.logger.info(f"Discovered TNS: {tns_entry} "
                                        f"is not working for {dsn}")
                        self.logger.info(f"Other connection issue.  Requires "
                                        f"manual intervention on {dsn}")
                        self.logger.error(f"TNS Check Failed: {tns_entry} "
                                        f"Code: {error.code} "
                                        f"MSG: {error.message}")

        self.logger.info(f"Exiting create_TNS_entry with RC: {rc} ")
        return rc


    def create_ssh_connection(self, handler, call_timeout):
        
        rc = 0
        if handler == 'ssh':
            PWD = self.DBC_PWD
            user = self.owner
        elif handler == 'oem_ssh':
            PWD = self.OEM_PWD
            user = self.OEM_USER
        elif handler == 'win_ssh':
            PWD = self.WIN_PWD
            user = self.WIN_USER
        elif handler == 'oraoemag':
            PWD = 'self.oms_pwd'
            user = 'oraoemag'
        elif handler == 'os_proc':
            if self.inventory.INV_USER == 'DBC_TEAM':
                localhost = DBC_SERVER
                user = 'orac4i'
            else: 
                localhost = OS_SERVER
                user = 'fidBIN'
        elif handler == 'rsh_978' :
                self.PKEY = os_key
                localhost = OS_SERVER
                user = 'fidBIN'

        self.logger.debug(f"Arrived at create_ssh_connection Host: {self.hostname} User: {user} ")

        self.connection = paramiko.SSHClient()
        self.connection.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        if self.PKEY != 'NONE' : 
            private_key = paramiko.RSAKey.from_private_key_file(self.PKEY)

        if handler == 'os_proc' or handler == 'rsh_978':
            try:
                self.connection.connect(hostname=localhost,
                                        port=22, username=user, timeout=call_timeout,
                                        banner_timeout=30, auth_timeout=30, pkey=private_key)
                rc = 1

            except Exception as sshException:
                    result = 'FAILED: general_ssh_exception'
                    rc = "sshException"
                    self.disconnect()
                    self.logger.error(f"OS Connection failed to local host {localhost}")
            
            else:
                self.logger.debug(f"Connection succeeded, Host: {localhost} User: {user}")
  
        else:
            if self.PKEY != 'NONE' and handler != 'oem_ssh' and handler != 'win_ssh' and handler != 'oraoemag':
                self.logger.debug(f"ssh key attempt here, Host: {self.hostname} User: {user}")
                # This is an ssh connection using ssh key
                try:
                    self.connection.connect(hostname=self.hostname, port=22, username=user, timeout=call_timeout,
                                            banner_timeout=30, auth_timeout=30,pkey=private_key)
                    rc = 1
                    
                except paramiko.ssh_exception.AuthenticationException:
                    try:   # this is required for https://github.com/paramiko/paramiko/issues/1961
                        self.connection.connect(hostname=self.hostname, port=22, username=user, timeout=call_timeout,
                                                banner_timeout=30, auth_timeout=30,pkey=private_key, 
                                                disabled_algorithms={'pubkeys': ['rsa-sha2-256', 'rsa-sha2-512']})
                        rc = 1
                        
                    except paramiko.ssh_exception.AuthenticationException:
                        self.logger.error(f"Authentication failed, Host: {self.hostname} User: {user}")
                        rc = "AuthenticationException"
                        self.disconnect()  
                
            else:  #  Connecting with User and Password
                self.logger.debug(f"User/pwd attempt here, Host: {self.hostname} User: {user}")
                try: 
                    self.connection.connect(hostname=self.hostname, port=22, username=user, timeout=call_timeout, 
                                            password=PWD, banner_timeout=30, auth_timeout=30)
                    rc = 1


                except paramiko.ssh_exception.AuthenticationException:
                    self.logger.error(f"Authentication failed, Host: {self.hostname} User: {user}")
                    rc = "AuthenticationException"
                    self.disconnect()

                except Exception as sshException:
                    self.logger.error(f"General Exception in os command: {sshException}")
                    result = 'FAILED: general_ssh_exception'
                    rc = "sshException"
                    self.disconnect()

            self.logger.debug(f"Connection succeeded, Host: {self.hostname} User: {user}")

        return rc

    def create_postgres_connection(self):
        rc = 0
        try:
            my_dsn = (f"dbname={self.instance_name} user={self.DBC_USER} "
                      f"password={self.DBC_PWD} host={self.hostname}")
            self.connection = psycopg2.connect(my_dsn)
        except psycopg2 as exc:
            error, = exc.args
            self.logger.error(f"Postgres Connection Error: {my_dsn} "
                              f"Code: {error.code} MSG: {error.message} ")
            rc = error.code
        return rc

    def create_mssql_connection(self):
        rc = 0
        try:
            my_dsn = (f'DRIVER={self.SQL_DRIVER_NAME}; '
                      f'SERVER={self.hostname}; '
                      f'DATABASE=master; PORT=1433; UID={self.MSSQL_USER}; '
                      f'pwd={self.MSSQL_PWD}; TDS_Version=7.4;')
            self.logger.debug("SQL DSN: %s",  my_dsn)
            self.connection = pyodbc.connect(my_dsn)

        except Exception as exc:
            error  = exc.args
            self.logger.error(f"SQL ODBC Connection Error: {self.hostname} as {self.MSSQL_USER} Code: {error[0]} ")
            rc = error[0]
        return rc

    def disconnect(self):
        # if connection exists, close it and set connection to ''

        try:
            if self.connection != '':
                # self.logger.debug("Disconnecting from :  %s ", str(self.connection))
                self.connection.close()
                # self.logger.debug("Disconnected from :  %s ", str(self.connection))
                self.connection = ''
                if self.timer:
                    self.timer.cancel()
                    self.timer = None
        except Exception:
            self.logger.error(f'Error when disconnecting from target: {self.hostname}')
            self.connection = ''

    def exec_sql(self, inventory_query):
        """
        Run a SQL query on the target
        :param inventory_query:  The SQL command
        :return RC:
        """

        if self.DBC_PWD not in inventory_query \
                and self.SYS_PWD not in inventory_query \
                and self.DBSNMP_PWD not in inventory_query:
            self.logger.debug("Exec SQL on Inventory: %s", inventory_query)

        # Run the SQL Command
        with self.connection.cursor() as exec_cursor:
            exec_cursor.execute(inventory_query)
            rc = self.connection.commit()

        self.logger.debug("SQL exec result: %s", rc)

        return rc

    def get_info(self, check, handler, call_timeout=240):
        """
        Get_Info is a wrapper function that passes parameters through
        to sub-routines based on the handler an then passes results back
        to the calling function.

        It ensures that calling programs and functions are written generically
        and do not need custom code depending on the type of target they are
        monitoring.

        :param check:            The monitoring command to run
        :param handler:          The name of the method for connecting.
                                 (ex ssh, oracle, etc..)
        :param call_timeout:     The max number of seconds to allow the
                                 connection to stay open.

        :return: rc, command_result: The result of the command and return code
                                     that indicates whether connection was
                                     successful (1 = Success, 0 = Fail,
                                     -1 = Could not connect)
        """

        if self.DBC_PWD not in check \
                and self.SYS_PWD not in check \
                and self.DBSNMP_PWD not in check:
            self.logger.debug('get_info with check=%s, handler=%s',
                              check, handler)
        rc = 0
        result = ''

        if self.connection != '':
            if handler in ['ssh', 'oem_ssh', 'win_ssh', 'os_proc', 'oraoemag','rsh_978']:
                rc, result = self.get_OS_info(check,call_timeout)
                if handler == 'win_ssh' and 'only' in result:
                    rc = 2

            elif handler in [ 'PLSQL', 'SYSDBA' ] :
                rc, result = self.get_PLSQL_info(check)
            else:
                #  handler == 'Oracle', 'ASM', 'OMS', or 'MSSQL':
                rc, result = self.get_oracle_info(check)

        if self.DBC_PWD not in check and self.SYS_PWD not in check \
                and self.DBSNMP_PWD not in check:
            self.logger.debug('get_info returning Result: %s (rc = %s) for check: %s',
                              str(result), str(rc), str(check))

        return rc, result

    def get_oracle_info(self, check):
        """
        Performs a monitoring check command on an Oracle Database Target
        :param check:           The monitoring command to be run
        :param connection:      The active target connection to run the check
        :param call_timeout:    The # of MILLISECONDS to give Oracle call
        :return: value:         The result of the check query
        :return: rc:            Return code that indicates whether connection
                                was successful (1 = Success, 0 = Fail,
                                -1 = Could not connect)
        """
        rc = 0
        value = ''

        try:
            with self.connection.cursor() as db_info_cursor:
                db_info_cursor.execute(check)
                row = db_info_cursor.fetchone()
                if row:
                    # value = str(value[0]).strip()
                    value = ' '.join([str(item) for item in row]).strip()
                    rc = 1
                else:
                    value = ''

        except cx_Oracle.Error as exc:
            # Now Handle all the things that could go wrong with this request
            # If there was a database error, return it as the check result.
            error, = exc.args
            oracle_err = str(error.code)
            self.logger.error('GetOracleInfo Error: ORA-%s  Message: %s',
                              oracle_err, str(error))
            rc = 0
            value = error.code

        self.logger.debug('get_oracle_info returning Result: %s (rc = %s)',
                          str(value), str(rc))
        return rc, value
        # END get_oracle_info

    def get_PLSQL_info(self, check):
        """
        Performs a monitoring check command on an Oracle Database Target
        :param check:           The monitoring command to be run
        :param connection:      The active target connection to run the check
        :param call_timeout:    The # of MILLISECONDS to give Oracle call
        :return: value:         The result of the check query
        :return: rc:            Return code that indicates whether connection
                                was successful (1 = Success, 0 = Fail,
                                -1 = Could not connect)
        """
        rc = 1

        try:
            with self.connection.cursor() as db_info_cursor:
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
                    db_info_cursor.callproc("dbms_output.get_lines",
                                            (lines_var, num_lines_var))
                    self.logger.info('get_PLSQL_info: Lines: %s Count %s ',
                                     lines_var, num_lines_var)
                    num_lines = num_lines_var.getvalue()
                    lines = lines_var.getvalue()[:num_lines]
                    # for line in lines:
                    #    print(line or "")
                    if num_lines < chunk_size:
                        break

                if len(lines) == 0:
                    value = ''
                elif len(lines) == 1:
                    value = str(lines[0])
                else:
                    value = str(lines)

        except cx_Oracle.Error as exc:
            # Now Handle all the things that could go wrong with this request
            # If there was a database error, return it as the value
            error, = exc.args
            oracle_err = str(error.code)
            self.logger.error('get_PLSQL_info Error: ORA-%s  Message: %s',
                              oracle_err, str(error))
            rc = 0
            value = error.code

        self.logger.debug('get_PLSQL_info returning Result: %s (rc = %s)',
                          str(value), str(rc))
        return rc, value
        # END get_PLSQL_info

    def get_OS_info(self, check, call_timeout=240):
        """
        Performs a monitoring check command at the o/s level of the
        :param check:           The monitoring command to be run
        :param connection:      The active target connection to run the check
        :param call_timeout:    The # of seconds to give the o/s command
                                (default 20)
        :return: value:         The result of the check query
        :return: rc:            Return code that indicates whether connection
                                was successful (1 = Success, 0 = Fail,
                                -1 = Could not connect)
        """
        result = ''
        rc = 0

        try:
            stdin, stdout, stderr = self.connection.exec_command(check, timeout=call_timeout, get_pty=False)
            time.sleep(1)

            # get the shared channel for stdout/stderr/stdin
            channel = stdout.channel

            # we do not need stdin.
            stdin.close()

            # indicate that we're not going to write to that channel anymore
            channel.shutdown_write()

            # read stdout/stderr in order to prevent read block hangs
            stdout_chunks = []
            stdout_chunks.append(stdout.channel.recv(
                len(stdout.channel.in_buffer)))
            # chunked read to prevent stalls

            while not channel.closed or channel.recv_ready() \
                    or channel.recv_stderr_ready():
                # stop if channel was closed prematurely, and there is no data
                # in the buffers.
                self.logger.debug('Reading stdout at: %s',
                                  str(datetime.now()))
                timeout = call_timeout / 10
                got_chunk = False
                read_q, _, _ = select.select([stdout.channel], [], [], timeout)
                for c in read_q:
                    if c.recv_ready():
                        stdout_chunks.append(stdout.channel.recv(
                            len(c.in_buffer)))
                        got_chunk = True
                    if c.recv_stderr_ready():
                        # make sure to read stderr to prevent stall
                        stderr.channel.recv_stderr(len(c.in_stderr_buffer))
                        got_chunk = True
                '''
            1) make sure that there are at least 2 cycles with no data in th
               input buffers in order to not exit too early
               (i.e. cat on a >200k file).
            2) if no data arrived in the last loop, check if we already
               received the exit code
            3) check if input buffers are empty
            4) exit the loop
            '''
                if not got_chunk \
                        and stdout.channel.exit_status_ready() \
                        and not stderr.channel.recv_stderr_ready() \
                        and not stdout.channel.recv_ready():
                    # We're not going to read from this channel anymore
                    stdout.channel.shutdown_read()
                    # close the channel
                    stdout.channel.close()
                    # exit as remote side is finished and our buffers are empty
                    break

            rc = stdout.channel.recv_exit_status()
            if rc != 0:
                self.logger.error("Unable to run check: %s return code: %s",
                                  check, rc)
                # close all the pseudofiles
                stdout.close()
                stderr.close()
                channel.close()
                return -1, ''

            if rc == 0:
                rc = 1

            self.logger.debug("OS result length : %s ",
                              str(len(stdout_chunks)))
            result = ''.join(str(stdout_chunks[len(stdout_chunks) - 1].decode(
                "utf-8")).strip().replace('logout', ''))

            # close all the pseudofiles
            stdout.close()
            stderr.close()
            channel.close()

        except Exception as sshException:
            if (self.DBC_PWD not in check) \
                    and (self.SYS_PWD not in check) \
                    and (self.DBSNMP_PWD not in check):
                self.logger.error("Unable to run check: %s Result: %s",
                                  check, sshException)
            else:
                self.logger.error("Unable to run check: %s ", sshException)
            result = 'FAILED: os command failed'
            rc = -1

        finally:
            if result is None:
                result=''
            self.logger.info("Returning result from OS command: %s", result)

        return rc, result
        # END get_OS_info

    def do_checks(self, checks):
        """
        Performs a list of monitoring checks on the target
        :param checks:          A list of checks to perform on the target
        """

        # open a connection to the inventory
        rc = self.inventory.connect()

        # sort into dictionary by handler type
        checks_by_handler = {}
        for check in checks:
            if check.vendor == self.vendor or check.vendor == 'ALL':
                if check.sub_type == self.sub_type or check.sub_type == 'ALL' or \
                     ( check.sub_type == 'Non-PDB' and self.sub_type != 'PDB') :
                    if check.handler not in checks_by_handler:
                        checks_by_handler.update({check.handler: []})
                    checks_by_handler[check.handler].append(check)

        if rc == 1 and checks_by_handler:
            for check_handler in checks_by_handler:
                rc = self.connect(check_handler, self.inventory)
                
                # Database_Team Schema
                if self.inventory.INV_USER == 'DBC_TEAM':
                    self.inventory.add_result(self.inventory_id,f'{check_handler}:{rc}','access')
                # Server_Team Schema
                else:
                    self.inventory.add_result(self.hostname,f'{check_handler}:{rc}','access')
                
                if rc != 1:
                    self.disconnect()
                else:
                    # self.timer = threading.Timer(120, self.disconnect)
                    # self.timer.start()  # start counting on the timeout timer

                    for target_check in checks_by_handler[check_handler]:
                        # Need to do this here because we need hostname and
                        # instance_name
                        if check_handler == 'OMS':
                            target_check.check = target_check.check.format(
                                self.hostname.upper(),
                                self.instance_name.upper(),
                                self.instance_name.upper())
                        # if check_handler == 'os_proc':
                        #    target_check.check = target_check.check.format( self.hostname.upper())
                        
                        temp_check=target_check.check
                            
                        try: 
                            self.logger.debug(f"Checking check:  {str(target_check.check) }")

                            if '$ORACLE_HOME' in target_check.check:
                                self.logger.debug(f"Found \"$ORACLE_HOME\" - Changing: {str(target_check.check)} to {str(target_check.check.replace('$ORACLE_HOME', self.home_dir ))}")
                                temp_check = target_check.check.replace('$ORACLE_HOME', self.home_dir)
                            if '${ORACLE_HOME}' in target_check.check:
                                temp_check = target_check.check.replace('${ORACLE_HOME}', str(self.home_dir))
                            if '$ORACLE_SID' in target_check.check:
                                temp_check = target_check.check.replace('$ORACLE_SID', self.instance_name)
                            if '${ORACLE_SID}' in target_check.check:
                                temp_check = target_check.check.replace('${ORACLE_SID}', self.instance_name)
                            if '$HOSTNAME' in target_check.check:
                                temp_check = target_check.check.replace('$HOSTNAME', self.hostname)
                            if '${HOSTNAME}' in target_check.check:
                                temp_check = target_check.check.replace('${HOSTNAME}', self.hostname)
                        except: 
                            self.logger.debug("Unable to substitute: %s", str(target_check.check) )

                        info_rc, result = self.get_info(temp_check, check_handler)

                        self.logger.debug(f"Inventory ID: {self.inventory_id} "
                                          f"Attribute: "
                                          f"{target_check.result_column} "
                                          f"Value: {result} RC: {info_rc}")
                        if info_rc == 1:
                            if target_check.frequency == 'Database' \
                                    or target_check.frequency == 'Server':
                                rc = self.inventory.set_target_attribute(
                                    self.inventory_id,
                                    target_check.result_column,
                                    result)

                            # Standard Schema
                            if self.inventory.INV_USER == 'DBC_TEAM':
                                rc = self.inventory.add_result(
                                    self.inventory_id,
                                    result,
                                    target_check.result_column)

                            # Server_Team Schema
                            else:
                                rc = self.inventory.add_result(
                                    self.hostname,
                                    result,
                                    target_check.result_column)
                self.disconnect()
        self.inventory.disconnect()
