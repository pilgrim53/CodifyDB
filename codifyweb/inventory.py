"""
# ============================================================================
# Name:         inventory.py
# Description:  This is the utility class of methods for managing the
#               Inventory. The Inventory has the following primary objects.

OBJECT_TYPE          OBJECT_NAME
-------------------- -------------------------
TABLE                CHECKLIST
TABLE                CHECK_RESULTS
TABLE                NOTIFICATIONS
TABLE                TARGETS
TABLE                TARGET_REJECTS
TABLE                PATCHING
TRIGGER              PATCHING_AFTER_INSERT
TABLE                PATCHES

# Input Files:  .env
#               checklist table
#               .env
#
# Calls:        cx_Oracle.connect   to access the inventory database
#
# Restrictions: check_filter parameter must not be empty
# ========================================================================
"""
import cx_Oracle  # https://oracle.github.io/python-cx_Oracle/
import psycopg2  # https://pypi.org/project/psycopg2/
import psycopg2.extras  # This gives access to the psycopg2 error messages
from datetime import date, datetime, timedelta  # not included by default
from decouple import config  # Allows us to read .env
from inv_logging import start_logging
# ========================================================================
from check import Check
from target import Target
from patch import Patch
from password_manager import PasswordManager
delta = int(config('PATCH_WINDOW'))


class Inventory:
    CREDENTIALS = PasswordManager()

    def __init__(self, logger):
        self.credentials = PasswordManager
        self.logger = logger
        self.connection = ''
        self.INV_USER = self.CREDENTIALS.get('INV_USER')
        # self.INV_USER = config('INV_USER')

    def connect(self):
        """
        Initialize the connection to the Inventory Database.
        If database is already connected, do nothing
        :return RC:  1 = Success, 0 = Fail
        """

        RC = 1
        INV_PWD = self.CREDENTIALS.get('INV_PWD')
        # INV_PWD = config('INV_PWD')
        DBNAME = config('DBNAME')
        INVENTORY_HOST = config('INVENTORY_HOST')
        dsn = ''

        # Database_Team Schema
        if self.INV_USER == "DBC_TEAM":
            dsn = DBNAME + '_' + INVENTORY_HOST
        # Server_Team Schema
        else:
            INVENTORY_PORT = config('INVENTORY_PORT')
            dsn = cx_Oracle.makedsn(INVENTORY_HOST,
                                    INVENTORY_PORT,
                                    service_name=DBNAME)

        self.logger.debug("Attempt to connect to the Inventory.")
        try:
            if self.connection == '':
                self.connection = cx_Oracle.connect(
                    self.INV_USER, INV_PWD, dsn,
                    mode=cx_Oracle.DEFAULT_AUTH)
                self.connection.autocommit = True
                self.connection.callTimeout = 60000
                self.logger.debug("Connected to Inventory with 10 minute timeout.")
        except cx_Oracle.DatabaseError as exc:
            error, = exc.args
            self.connection = ''
            self.logger.error("DSN: %s DatabaseError-Code: %s %s ", dsn, error.code, error.message)
            RC = 0

        return RC
    # End connect

    def disconnect(self):
        """
        Close the connection to the Inventory Database
        :return RC:  1 = Success, 0 = Fail
        """

        RC = 1
        try:
            # self.logger.debug("Attempt to disconnect from Inventory.")
            if self.connection != '':
                self.connection.close()
                self.connection = ''
                # self.logger.debug("Disconnected from the Inventory.")
            # else :
                # self.logger.debug("No active connection to Inventory.")

        except cx_Oracle.DatabaseError as exc:
            error, = exc.args
            self.logger.error("DatabaseError-Code: %s %s ",
                              error.code, error.message)
            self.connection = ''
            RC = 0

        return RC
    # End disconnect

    def exec_sql(self, inventory_query, scale):
        """
        Run a SQL query on the central inventory.
        :param inventory_query:  The SQL command
        :param scale:   ONE, ALL, EXEC    corresponds to the cursor handling.
        :return query_result: a row or list of rows returned from the database
        :return RC:  1 = Success, 0 = Fail
        """

        RC = 1
        query_result = ''
        self.logger.debug("Scale: %s, Inventory Query: %s", scale, inventory_query)

        # Query the Inventory DB
        try:
            # Run the SQL query
            with self.connection.cursor() as inventory_cursor:
                inventory_cursor.execute(inventory_query)
                if scale == 'ALL':
                    query_result = inventory_cursor.fetchall()
                elif scale == 'ONE':
                    self.logger.debug("Fetching")
                    query_result = inventory_cursor.fetchone()
                elif scale == 'EXEC':
                    inventory_cursor.connection.commit()
                    query_result = 1

        except cx_Oracle.DatabaseError as exc:
            error, = exc.args
            self.logger.error("DatabaseError-Code: %s %s ", error.code, error.message)
            RC = 0
        
        except cx_Oracle.NameError as exc:
            error, = exc.args
            self.logger.error("DatabaseError-Code: %s %s ", error.code, error.message)
            RC = 0


        except :
            self.logger.error("Unknown Error in SQL")
            RC = 0


        if not query_result:
            RC = 0

        # self.logger.debug("Query result: %s", query_result)

        return RC, query_result
    # END exec_sql

    def add_result(self, inventory_id, check_result, column_name):
        """
        Insert the check results into the inventory database.
        (CHECK_RESULTS table)
        :param inventory_id:   Inventory ID
        :param column_name:    Attribute name being stored
        :param check_result:   Attribute value
        :return 0
        """

        self.logger.debug("Insert check result: %s into %s for ID: %s",
                          check_result, column_name, inventory_id)

        check_date = datetime.now()
        data=dict(id=f"{inventory_id}", check_date=f"{str(check_date)}", check_column=f"{column_name}", result=f"{check_result}")
        if self.INV_USER == "DBC_TEAM":
            # DBC_Team Schema uses Inventory_id in check_results
            insert_stmt = """INSERT INTO check_results (inventory_id,check_date,check_result,check_column)
                VALUES (:id, to_timestamp(:check_date,'YYYY-MM-DD HH24:MI:SS.FF'), :result, :check_column)"""

        else:
            # Server_Team Schema uses hostname in check_results
            insert_stmt = """INSERT INTO check_results (hostname,check_date,check_result,check_column)
                VALUES (:id, to_timestamp(:check_date,'YYYY-MM-DD HH24:MI:SS.FF'), :result, :check_column)"""

        self.logger.debug("Insert Statement: %s %s", insert_stmt, data)

        # run the insert command and check for errors
        try:
            with self.connection.cursor() as inventory_cursor:
                inventory_cursor.execute(insert_stmt, data)

        except psycopg2.Error as exc:
            error, = exc.args
            self.logger.error("Data Exception: %s ", error)

        except cx_Oracle.DatabaseError as exc:
            error, = exc.args
            self.logger.error("Data Exception: %s ", error)

        else:
            self.logger.info("Result added: %s  %s  %s  %s",
                             inventory_id, column_name, check_result,
                             check_date)

        return 0
    # END add_result

    def get_result(self, inventory_id, column):
        """
        Returns the most recent value of an target's attribute
        :param inventory_id:  The Inventory_ID of the object
        :param column:   The column or "attribute" you want to retrieve
        :return: value: the current value (most recent) of the attribute
          for the target
        """

        self.logger.debug(f"get last check result of "
                          f"inventory_id={inventory_id} for column={column}")

        query = (f"select nvl(check_result,'') from "
                 f"check_results\nwhere inventory_id='{str(inventory_id)}'"
                 f" and\n(check_column = '{column}' and check_date = ( "
                 f"\n\tselect max(check_date) from check_results"
                 f"\n\twhere (inventory_id = '{str(inventory_id)}' "
                 f"and check_column = '{column}' )))")

        try: 
            RC, value = self.exec_sql(query, 'ONE')

        except TypeError:
            self.logger.debug('TypeError')
            value = ''

        except ValueError:
            self.logger.debug('ValueError')
            value = ''

        else:
            if value:
                value = value[0]
            else:
                value = ''
            self.logger.debug("get_result returning value = %s", value)

        return value
    # END get_result

    def add(self, target):
        """
        Creates the initial Target entry in the DBC_Target table
        :param host, instance, etc...    NEEDS TO BE CHANGED TO A DICTIONARY
        :return: the target ID
        """
        rc = 0
        self.logger.debug(f"Adding entry in target table with host: "
                          f"{target.hostname} "
                          f"instance name: {target.instance_name} "
                          f"container: {target.container} "
                          f"DBID: {target.serial_number} "
                          f"owner: {target.owner} "
                          f"home_dir: {target.home_dir} "
                          f"status: {target.status} "
                          f"port: {target.port} "
                          f"target_type: {target.target_type}")

        if not self.contains(target):
            # insert_stmt = """INSERT INTO targets
            #             (Inventory_Create, Target_Type, HostName,
            # Instance_Name, Container, Serial_Number, owner, home_dir,
            # Vendor, Status, Port)
            # VALUES (to_timestamp(\'{}\',\'YYYY-MM-DD HH24:MI:SS.FF\'),
            # \'{}\', \'{}\', \'{}\', \'{}\', \'{}\', \'{}\', \'{}\', \'{}\',
            # \'{}\', \'{}\') """
            # insert_stmt = f"{insert_stmt.format(datetime.now(), target_type,
            # host, instance, container, DBID, owner, home_dir, vendor, status,
            # port)}"

            insert_stmt = (f"INSERT INTO targets "
                           f"(Inventory_Create, Target_Type, HostName, "
                           f"Instance_Name, Container, Serial_Number, "
                           f"owner, home_dir, Vendor, Status, Port)\nVALUES "
                           f"(to_timestamp('{datetime.now()}',"
                           f"'YYYY-MM-DD HH24:MI:SS.FF'), "
                           f"'{target.target_type}','{target.hostname}',"
                           f"'{target.instance_name}','{target.container}',"
                           f"'{target.serial_number}','{target.owner}',"
                           f"'{target.home_dir}','{target.vendor}',"
                           f"'{target.status}','{target.port}')")

            rc, _ = self.exec_sql(insert_stmt, 'EXEC')
            self.logger.debug('Insert: %s', insert_stmt)

            self.logger.info('Add target Result InventoryID: %s',
                             target.inventory_id)

            if rc == 0:
                rc = self.reject(target)
                self.logger.info('Rejecting:  hostname: %s instance_name: %s '
                                 'inventory_id: %s results: %s ',
                                 target.hostname, target.instance_name,
                                 target.inventory_id, rc)
        return rc
    # END Add

    def reject(self, target):
        """
        When an ADD fails,  record the data in the target_rejects table for
        future reference.
        :param target: target to be added to target_rejects
        :return: the result of the insert into target_rejects
        """
        self.logger.debug("Creating entry in target_rejects table with "
                          "host: %s instance name: %s vendor: %s "
                          "status: %s owner: %s home_dir: %s "
                          "important_notes: %s",
                          target.hostname, target.instance_name, target.vendor,
                          target.status, target.owner, target.home_dir,
                          'Failed to add')

        rc = 0

        # insert_stmt = """INSERT INTO target_rejects
        #                 (Inventory_Create, HostName, Instance_Name, vendor,
        # status, owner, home_directory, important_notes)
        #                 VALUES (\'{}\', \'{}\', \'{}\', \'{}\', \'{}\',
        # \'{}\', \'{}\', \'{}\'); """

        # insert_stmt = "{insert_stmt.format(date.today(), host, instance,
        # vendor, status, owner, home_dir, important_notes)}"

        insert_stmt = (f"INSERT INTO target_rejects"
                       f"(Inventory_Create, HostName, Instance_Name, vendor,"
                       f"status, owner, home_directory, important_notes) "
                       f"VALUES (to_timestamp('{datetime.today()}',"
                       f"'{target.hostname}','{target.instance_name}',"
                       f"'{target.vendor}','{target.status}','{target.owner}',"
                       f"'{target.home_dir}','{target.notes}')")

        rc = self.exec_sql(insert_stmt, 'ONE')

        self.logger.debug('Target Reject Result: %s', rc)

        return rc
    # END Reject

    def contains(self, target, target_type='Database'):
        """
        See if target exists in inventory
        :param host:            the host or server name
        :param instance_name:   the instance_name of the target
        :return: exists:  Sets the inventory_id of the target
                          and returns True if found, false otherwise
        """
        id = self.get_id(target.hostname, target.instance_name, target_type)

        if id == 0:
            exists = False
            target.inventory_id = id
        else:
            exists = True
            target.inventory_id = id

        self.logger.debug(f"inventory_contains got "
                          f"inventory_id = {target.inventory_id} "
                          f"and is returning {exists}")
        return exists
    # END inventory_contains

    def get_id(self, host, instance_name, target_type='Database'):
        """
        Look up the Inventory_ID of a target based on the hostname
        and instance_name
        :param host:            the host or server name
        :param instance_name:   the instance_name of the target
        :return: inventory_id:  Returns the inventory_id of the target
                                or 0 if not found
        """
        self.logger.debug("get_id with host = %s, instance_name = %s",
                          host, instance_name)
        inventory_id = 0

        if target_type == 'Server':
            select_stmt = ('select nvl(inventory_id,0) from server_team.targets where '
                           'upper(hostname)=\'' + host.upper()+'\'')
        else:
            select_stmt = (f"select nvl(inventory_id,0) from dbc_team.targets\n"
                           f"where upper(hostname) = "
                           f"'{host.upper()}' "
                           f"and upper(instance_name) = "
                           f"'{instance_name.upper()}'")

        RC, result = self.exec_sql(select_stmt, 'ONE')
        self.logger.info('Check %s %s returned: ''%s''',
                         host, instance_name, result)
        if result is None:
            inventory_id = 0
        else:
            inventory_id = result[0]

        self.logger.debug("get_id returning inventory_id = %s", inventory_id)
        return inventory_id
    # END get_id

    def set_target_attribute(self, inventory_id, update_column, update_value):
        """
        Checks the Inventory database and sets 1 attribute for target
        :param inventory_id:    The ID of the target to set
        :param column_name:     The attribute to set
        :param value:           The new value for the attribute
        :return: rc: Return code that indicates whether connection was
            successful (1 = Success, 0 = Fail, -1 = Could not connect)
        """
        self.logger.debug(f"Set attribute for InventoryID: {inventory_id} "
                          f"Attribute: {update_column} "
                          f"New Value: {update_value} ")
        result = 0

        if update_column == 'hostname':
            self.logger.info('InventoryID: %s Column: %s New Value: %s ',
                             inventory_id, update_column, update_value)
            self.logger.error('TO CHANGE HOSTNAME PLEASE UPDATE MANUALLY')
            return 0

        elif update_column == 'instance_name' and self.INV_USER == 'DBC_TEAM':
            self.logger.info('InventoryID: %s Column: %s New Value: %s ',
                             inventory_id, update_column, update_value)
            self.logger.error('TO CHANGE INSTANCE_NAME PLEASE UPDATE MANUALLY')
            return 0

        if update_value != '' and update_value != 'UNKNOWN':
            # ============================================================================
            # Get the old (current) value of the attribute in the inventory
            # and update the inventory only if anything has changed about the
            # target
            # ============================================================================

            target_query = (f"select {update_column} from targets "
                            f"where inventory_id = '{str(inventory_id)}'")

            rc, curr_value = self.exec_sql(target_query, 'ONE')

            if curr_value:
                curr_value = str(curr_value[0]).strip()
            else:
                curr_value = ''

            self.logger.info('InventoryID: %s Column: %s Old Value: %s '
                             'New Value: %s ',
                             inventory_id, update_column, curr_value,
                             update_value)

            if curr_value == update_value or update_value == 'UNKNOWN':
                self.logger.info('No change in Target Info')
            else:
                if update_column == 'blocksize' or update_column == 'port':
                    insert_stmt = (f"update targets set {update_column} "
                                   f" = {str(update_value)}\n"
                                   f"where inventory_id = {str(inventory_id)}")
                elif update_column == 'owner' and update_value == 'oraasm' and curr_value != 'oraasm':
                    self.logger.info('InventoryID: %s Column: %s New Value: %s SKIPPED',
                             inventory_id, update_column, update_value)
                    self.logger.error('Skipping changing owner to oraasm. ')
                    return 0

                else:
                    insert_stmt = (f"update targets set {update_column} "
                                   f"= '{str(update_value)}'\n"
                                   f"where inventory_id = {str(inventory_id)}")

                result, _ = self.exec_sql(insert_stmt, 'EXEC')

        self.logger.debug('set_target_attribute return code: %s', str(result))
        return result
    # END set_target_attribute

    def get_checks(self, filter):
        """
        Returns list of checks from the checklist table that match the filter
        conditions
        :param filter: filter used on the query to the checklist table. Filter
        should be formatted simmilar to below
        filter = {
            'AND': {
                'frequency': 'HOURLY',
                'target_type'': 'Database'
            },
            'OR': {
                'vendor': ['ORACLE', 'ALL']
            }
        }


        """

        check_query = ('select check_command, check_type, result_column, handler, vendor, '
                       'frequency, sub_type from checklist where 1=1 '
                       'AND (')

        if 'AND' in filter:
            join = ''
            for col in filter['AND']:
                check_query += (f'{join}upper({col}) = '
                                f'\'{filter["AND"][col].upper()}\'')
                join = ' AND '
            if 'OR' in filter:
                check_query += ') AND ('
        if 'OR' in filter:
            join = ''
            for key in filter['OR']:
                for value in filter['OR'][key]:
                    check_query += f"{join}upper({key}) = '{value.upper()}'"
                    join = ' OR '
        check_query += ')'

        # Get ALL the checks using the supplied filters
        # self.logger.info("Check Query: %s", check_query)
        rc, all_checks = self.exec_sql(check_query, 'ALL')
        self.logger.debug("# of Checks: %s", len(all_checks))

        checks_list = []
        for check_command, check_type, result_column, \
                handler, vendor, frequency, sub_type in all_checks:
            check = Check(check_command, check_type,
                          result_column, handler, vendor, frequency, sub_type)
            checks_list.append(check)
        # self.logger.info("All Checks: %s", all_checks)

        return checks_list

    def get_targets(self, target_type, vendor, low_id, high_id):

        target_query = ("select inventory_id, instance_name, owner, home_dir, "
                        "upper(hostname), target_type, vendor, sub_type, version\n"
                        "from targets where support_tier = 'Test' "
                        "and decommissioned is null ")

        if target_type != "Database":
            target_query += f" and upper(target_type)='{target_type.upper()}'"

        if vendor != "ALL":
            target_query += f" and upper(vendor) = '{vendor.upper()}'"

        if low_id != "1":
            target_query += f' and inventory_id >= {str(low_id)}'

        if high_id != '999999':
            target_query += f' and inventory_id < {str(high_id)}'

        target_query += ' order by inventory_id '

        self.logger.info("Target Query: %s", target_query)

        rc, all_targets = self.exec_sql(target_query, 'ALL')
        self.logger.debug("# of Targets: %s", len(all_targets))

        target_counter = 0
        target_list = []

        try:
            for inventory_id, instance_name, owner, home_dir,\
                    hostname, target_type, vendor, sub_type, version in all_targets:
                
                if owner is None or owner == '':
                    owner = 'oracle'
                if target_type == 'Server' and instance_name is not None:
                    if hostname.upper() in instance_name.upper() :
                        hostname = instance_name

                target = Target(inventory_id=inventory_id,
                                hostname=hostname,
                                instance_name=instance_name,
                                owner=owner,
                                home_dir=home_dir,
                                target_type=target_type,
                                vendor=vendor,
                                sub_type=sub_type,
                                version=version,
                                logger=self.logger)
                self.logger.debug(f"Adding Target: {target}")
                target_list.append(target)
                target_counter += 1

        except AttributeError as Exc:
            self.logger.debug(f"AttributeError: {Exc}")
            value=''
            
        except TypeError as Exc:
            self.logger.debug(f"TypeError: {Exc}")
            value=''

        except Exception as Exc: 
            self.logger.debug(f"Unknown Error getting targets: {Exc}")

        return target_list

    def get_patches(self):
        
        # rc, curr_release = self.exec_sql("select max(release_date) from dbc_team.patches where combo='Y' ", 'ONE')
        
        target_query = (f"select id, upper(hostname), instance_name, vendor,"
                        f"check_date, sched_date_time, pre_req_issues, "
                        f"rollback, oneoff, nvl(ticket,''), sw_release"
                        f"\n  from dbc_team.patching "
                        f"where SCHED_DATE_TIME > ( sysdate -1/24 ) "
                        f"and SCHED_DATE_TIME < ( sysdate + 30 ) "
                        f"and nvl(PATCH_ISSUES,1) != 0 "
                        f"and nvl(IN_PROGRESS,'XXX') != 'Y' "
                        f"order by SCHED_DATE_TIME, TICKET")

        rc, patches = self.exec_sql(target_query, 'ALL')

        patch_counter = 0
        patch_list = []

        if len(patches) == 0:
            self.logger.info("Nothing to patch in patching table.")
        else:
            for inventory_id, hostname, instance_name, vendor, check_date, \
                    sched_date_time, issues, rollbacks, oneoffs, ticket, sw_release in patches:
                self.logger.info(
                    "Hostname: %s Database: %s Scheduled date: %s",
                    hostname, instance_name,
                    str(sched_date_time.strftime("%m/%d/%Y %H:%M:%S")))

                scp_copy = False
                if rollbacks is None:
                    rollbacks = ''

                if oneoffs is None:
                    oneoffs = ''

                if not (check_date and issues == '0'):
                    # Not ready to apply. We have not had pre-check yet.
                    # Check/recheck
                    APPLY = ''
                else:
                    self.logger.info(
                        "Pre-checks Were completed Successfully "
                        f"for {instance_name} at " +
                        str(check_date.strftime("%m/%d/%Y %H:%M:%S")))

                    time_buffer = timedelta(minutes=delta)
                    if (sched_date_time > datetime.now() - time_buffer) \
                            and (sched_date_time < datetime.now()
                                 + time_buffer):
                        self.logger.info("Proceeding with patching scheduled "
                                         "in %s minutes ", str(datetime.now() - sched_date_time))
                        APPLY = 'APPLY'
                    else:
                        self.logger.info("Patching is %s minutes outside of "
                                         "window. Buffer is only %s minutes.",
                                         str(sched_date_time - datetime.now()), str(time_buffer))
                        APPLY = 'SKIP'

                if APPLY == 'APPLY':
                    self.logger.info(f"Performing Database Patching on Host: "
                                     f"{hostname} Database: {instance_name}")
                else:
                    if APPLY == '':
                        self.logger.info(f"Performing Prep only on Host: "
                                         f"{hostname} Database: "
                                         f"{instance_name}")
                        scp_copy = True

                patch = Patch(inventory_id, hostname, instance_name, vendor,
                              sched_date_time, APPLY, rollbacks, oneoffs,
                              scp_copy, ticket, sw_release)

                patch_list.append(patch)
                self.logger.debug(f'Adding Patch: {str(patch_counter)} '
                                  f'{str(patch)}')
                patch_counter += 1

        return patch_list

    def patch_running(self, hostname, instance_name):
        is_running = False
        in_progress_query = (f'select nvl(in_progress,\'N\') from '
                             f'dbc_team.patching where upper(hostname)='
                             f' \'{str(hostname.upper())}\' and upper(instance_name) = '
                             f' \'{str(instance_name.upper())}\' and '
                             f'sched_date_time > (sysdate-1/24)')

        rc, result = self.exec_sql(in_progress_query, 'ONE')
        if result and result[0] == 'Y':
            is_running = True
        return is_running

    def patch_progress_update(self, hostname, instance_name, flag):
        in_progress_update = (f'update dbc_team.patching set '
                              f'in_progress=\'{flag}\' where upper(hostname)='
                              f' \'{str(hostname.upper())}\' and upper(instance_name)= '
                              f' \'{str(instance_name.upper())}\' and '
                              f'sched_date_time > (sysdate-1/24)')

        self.logger.debug("Saving result data: %s",  str(in_progress_update))
        self.logger.debug(f"Updating running status to: {flag}")
        rc, _ = self.exec_sql(in_progress_update, 'EXEC')
        return rc

    def get_attribute(self, inventory_id, column):
        """
        Checks the Inventory database for 1 target and 1 attribute
        :param inventory_id:    The ID of the target to get
        :param target:          The target to get.  (UNUSED)
        :param column:          The attribute to get
        :param value:           The current value for the attribute
        :return: rc: Return code that indicates whether connection was
                     successful (1 = Success, 0 = Fail, -1 = Could not connect)
        """

        self.logger.debug(f"get_attribute with inventory_id={inventory_id}, column={column}")

        query = ('select nvl(' + column + ',\'\') from targets where inventory_id=' + str(inventory_id) + '')
        
        try:
            RC, value = self.exec_sql(query, 'ONE')

        except AttributeError as Exc:
            self.logger.debug(f"AttributeError: {Exc}")
            value=''

        except TypeError as Exc:
            self.logger.debug(f"TypeError: {Exc}")
            value=''

        except:
            self.logger.debug(f"AttributeError")
            value=''

        else:
            if value:
                value = value[0]
            else:
                value = ''

        self.logger.debug("get_attribute returning value = %s", value)

        return value
    # END get_attribute
