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
# 2021/07/06     M.Pankratz       1.03      Extract common routines
# 2021/09/05     M.Pankratz       1.04      Add TargetType for OS Targets, etc.
# ============================================================================

from inv_logging import start_logging
import cx_Oracle
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
# 2021/07/06     M.Pankratz       1.03      Extract common routines
# 2021/09/05     M.Pankratz       1.04      Add TargetType for OS Targets, etc.
# ============================================================================

from inv_logging import start_logging
import cx_Oracle
import psycopg2
import sys, getopt  # Allows us to interact with the o/s
import paramiko  # Allows us to ssh to the Database Servers
import threading  # Allows us to time and kill hung db connections
from datetime import datetime
from datetime import date

from decouple import config  # Allows us to read .env
# ============================================================================
import targets
import results

# Set DBTools Environment and Global Variables
DBC_USER = config('DBC_USER')
DBC_PWD = config('DBC_PWD')
INV_USER = config('INV_USER')
INV_PWD = config('INV_PWD')
ORACLE_BASE = config('ORACLE_BASE')
ORACLE_HOME = config('ORACLE_HOME')
TNS_ADMIN = config('TNS_ADMIN')
LOG_DIR = config('LOG_DIR')
CODIFYDB_HOST = config('CODIFYDB_HOST')
CODIFYDB = config('CODIFYDB')
INVENTORYDB = "dbname=" + CODIFYDB + " user=" + INV_USER + " password=" + INV_PWD + " host=" + CODIFYDB_HOST

GLOBAL_LOG_NAME = "Check_Targets"
GLOBAL_LOG_FILE = LOG_DIR + GLOBAL_LOG_NAME + "_" + str(date.today()) + ".log"
GLOBAL_LOG_LEVEL = 'DEBUG'

# ---------------------------     MAIN PROGRAM     ---------------------------
# Description:  Monitors database targets from the DBC Inventory Database.
#               If the target exists and something has changed, then it updates
#               the entry.
#
# Input Files:  TARGETS Table
#               checklist table
#               $TNS_ADMIN/tnsnames.ora
#
# Output:       Entries into the CheckResults table
#               Log files to $LOG_DIR/check_results_$date.log
# Syntax:       check_targets.py -t target_type -v vendor -f frequency -c check_type
#
# Called Routines:    cx_Oracle - for Oracle database calls
#                     psycopg2 - for PostgreSQL database calls
#                     date, grep, awk, cat, uname - misc UNIX commands
#
# Restrictions: Enter the correct python environment prior to running.
#               ex)  "source ~/<venv>/bin/activate"
#                           to enter the necessary virtual environment
# ============================================================================


def main(argv):
    global vendor
    global frequency
    global check_type
    global target_type
    vendor = '%'
    frequency = 'HOURLY'  # Default to the hourly checks if not specified
    check_type = '%'
    target_type = 'Database'  # Default to Database right now for development

    check_query = 'select check_command, check_type, result_column, handler, database_type from public.checklist where 1=1 '
    target_query = 'select inventory_id, instance_name, owner, home_dir, hostname,' \
                   ' target_type, database_type from target where decommissioned is null '

    try:
        opts, args = getopt.getopt(argv,":t:c:v:f:h")

    except getopt.GetoptError:
        print('check_targets.py [ -t Database|Server -c DB|OS -v <vendor> -f <frequency> ]')
        sys.exit(2)

    target_logger.info('Command Options: %s  Arguments: %s ', opts, args)

    for opt, arg in opts:
        print("Option: {} Argument: {}".format(opt, arg))
        if opt == '-h':
            print('check_targets.py -t [Database|Server] -c [DB|OS] -v [ORACLE|SUNOS|LINUX|AIX] -f [HOURLY|DAILY|WEEKLY] ')
            sys.exit()

        elif opt == "-t":
            target_type = arg
            if target_type == 'Server' :
              check_type='OS'
              check_query += ' and vendor != \'ORACLE\' and check_type = \'' + check_type + '\''
            elif opt == "-c":
              check_type = arg
              check_query += ' and check_type = \'' + check_type + '\''

        elif opt == "-v":
            vendor = arg
            check_query += ' and vendor = \'' + vendor + '\''
            target_query += ' and vendor =  \'' + vendor + '\''

        elif opt == "-v":
            vendor = arg
            check_query += ' and vendor = \'' + vendor + '\''
            target_query += ' and vendor =  \'' + vendor + '\''

        elif opt == "-c":
            check_type = arg
            check_query += ' and check_type = \'' + check_type + '\''

        elif opt == "-f":
            frequency = arg

    check_query += ' and frequency = \'' + frequency + '\'  order by handler, priority'
    target_query += ' and target_type = \'' + target_type + '\' order by inventory_id'

    target_logger.info("Running CheckTargets.py with TARGETTYPE=%s VENDOR=%s FREQUENCY=%s CHECKTYPE=%s", target_type,
                       vendor, frequency, check_type)
    target_logger.info("Check Query: %s", check_query)
    target_logger.info("Target Query: %s", target_query)

    # Fetch all the valid database targets from the Inventory DB and
    # check each one database by database
    # Attempt to query that target and record the results

    # Connect to the Inventory DB
    inventory_conn = psycopg2.connect(INVENTORYDB)
    target_cursor = inventory_conn.cursor()

    # Get ALL the active targets
    target_cursor.execute(target_query)
    all_targets = target_cursor.fetchall()
    target_logger.debug("# of Targets: %s", len(all_targets))

    # Get ALL the checks to perform on these targets
    target_cursor.execute(check_query)
    all_checks = target_cursor.fetchall()
    target_logger.info("All Checks: %s", all_checks)
    inventory_conn.close()


    # Main Loop of all in-scope Targets
    for inventory_id, instance_name, owner, home_dir, hostname, target_type, target_database_type in all_targets:
        target_logger.debug("inventory_id: %s instance_name: %s owner: %s home_dir: %s hostname: %s target_type: %s target_database_type: %s",
                            inventory_id, instance_name, owner, home_dir, hostname, target_type, target_database_type)

        # Sub Loop of All Checks for the Target
        # Reuse the connection to the target for all similar checks with same handler
        old_handler = ''
        rc = 1
        connected = 'FALSE'

        for check, check_type, result_column, handler, check_database_type in all_checks:
            result = ''
            if handler != old_handler:
                old_handler = handler
                if connected == 'TRUE':
                    try:
                        connected = 'FALSE'
                        curr_connection.close()
                    except cx_Oracle.DatabaseError as exc:
                        error, = exc.args
                        target_logger.error("DatabaseError-Code: %s %s ", error.code, error.message)

                rc, curr_connection = targets.connect(hostname, instance_name, owner, handler, target_logger)
                target_logger.info("Connecting to Host: %s Instance: %s returned: %s ", hostname, instance_name, rc)
                if rc != 1:
                    results.add(inventory_id, handler + ':' + str(rc), 'access', target_logger)
                    target_logger.debug("%s connection failed to Host: %s Instance: %s Error: %s", handler, hostname,
                                        instance_name, rc)
                    connected = 'FALSE'
                else:
                    connected = 'TRUE'

            target_logger.debug("Check %s Handler: %s Connected: %s ", check, handler, connected)

            if connected == 'TRUE':
                if check_database_type == "" or ( check_database_type == target_database_type) :
                    if handler == 'OMS':
                        check = f"{check.format(hostname, instance_name)}"

                    info_rc, result = targets.get_info(check, handler, curr_connection, target_logger)
                    target_logger.debug("Inventory ID: %s Attribute: %s Value: %s RC: %s", inventory_id, result_column,
                                        result, info_rc)
                    if info_rc == 1:
                        results.add(inventory_id, result, result_column, target_logger)
                    else:  # connection no longer works
                        target_logger.debug("Check %s RC: %s returned: %s ", check, info_rc, result)
                        connected = 'FALSE'
                        try:
                           curr_connection.close()
                        except cx_Oracle.DatabaseError as exc:
                           error, = exc.args
                           target_logger.error("DatabaseError-Code: %s %s ", error.code, error.message)

        try:
            if curr_connection != '' :
                curr_connection.close()
        except cx_Oracle.DatabaseError as exc:
            error, = exc.args
            target_logger.error("DatabaseError-Code: %s %s ", error.code, error.message)
        except cx_Oracle.InterfaceError as exc:
            error, = exc.args
            target_logger.error("InterfaceError-Code: %s %s ", error.code, error.message)

    target_logger.info("Completed running CheckTargets.py with target_type=%s vendor=%s frequency=%s check_type=%s",
                       target_type, vendor, frequency, check_type)
    target_logger.info("====================================================================================")

# END main program

if __name__ == "__main__":
    target_logger = start_logging(GLOBAL_LOG_LEVEL, GLOBAL_LOG_FILE, GLOBAL_LOG_NAME)    # Log to File
    main(sys.argv[1:])
