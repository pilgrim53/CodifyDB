#!/home/orac4i/Inventory/bin/python

# ============================================================================
# Import all the external Python modules that we need
# ============================================================================
from datetime import date, datetime  # not included by default
from decouple import config  # Allows us to read .env
from inv_logging import start_logging  # Allows us to log to a file
import targets  # All target functions
import sys, getopt  # Allows us to interact with the o/s
import psycopg2  # for PostgreSQL database calls

# ============================================================================
# Set DBTools Environment and Global Variables
# ============================================================================
TARGET_FILE = "./discovery.txt"
LOG_DIR = config('LOG_DIR')
LOG_NAME = "Scan_Targets"
LOG_FILE = LOG_DIR + LOG_NAME + "_" + str(date.today()) + ".log"
LOG_LEVEL = "DEBUG"
DBC_USER = config('DBC_USER')
DBC_PWD = config('DBC_PWD')
INV_USER = config('INV_USER')
INV_PWD = config('INV_PWD')
ORACLE_BASE = config('ORACLE_BASE')
ORACLE_HOME = config('ORACLE_HOME')
TNS_ADMIN = "/u01/app/oracle/DBTools/"
CODIFYDB_HOST = config('CODIFYDB_HOST')
CODIFYDB = config('CODIFYDB')
INVENTORYDB = "dbname=" + CODIFYDB + " user=" + INV_USER + " password=" + INV_PWD + " host=" + CODIFYDB_HOST


# ============================================================================

# ============================================================================
# ============================================================================
# ---------------------------   MAIN PROGRAM   -------------------------------
# ============================================================================
# ============================================================================
# Function:     scan_target
# Description:  Evaluate target info and look for changes to targets.
# Input:        -a (ADD) -t Database|Server -v Vendor
# Output:       Insert new or update existing records in Targets table
# Returns:      None
# ============================================================================
def main(argv):
    global check_type
    global target_type
    check_type = 'UPDATE'  # Default to scan / update existing known Targets
    target_type = 'Database'  # Default to database targets

    target_logger = start_logging(LOG_LEVEL, LOG_FILE, LOG_NAME)  # Log to File
    target_query = 'select inventory_id, instance_name, owner, home_dir, host_name, target_type \
                from public.dbc_target where decommissioned is null '

    try:
        opts, args = getopt.getopt(argv, ":t:v:ah")

    except getopt.GetoptError:
        print('scan_targets.py [ -a (ADD) -t Database|Server -v Vendor  ] | -h (help) ')
        sys.exit(2)

    target_logger.debug("All Options passed: {}".format(opts))
    target_logger.debug("All arguments passed: {}".format(args))

    for opt, arg in opts:
        target_logger.debug("Option: {} Argument: {}".format(opt, arg))
        if opt == '-h':
            print('scan_targets.py [ -t Database|Server -v Vendor -a (ADD) ] | -h (help) ')
            sys.exit()

        elif opt == "-a":
            check_type = 'ADD'

        elif opt == "-t":
            target_type = arg
            target_query += ' and target_type = \'' + target_type + '\''
        elif opt == "-v":
            vendor = arg
            target_query += ' and vendor = \'' + vendor + '\''

    target_query += ' order by inventory_id'

    check_query = "select check_command, check_type, result_column, handler from public.checklist \
               where frequency='" + target_type + "' order by handler, priority"

    # Connect to the Inventory DB
    inventory_conn = psycopg2.connect(INVENTORYDB)
    target_cursor = inventory_conn.cursor()

    # Get ALL the checks to perform on these targets
    target_cursor.execute(check_query)
    all_checks = target_cursor.fetchall()
    target_logger.debug("All Checks: %s", all_checks)

    if check_type == 'UPDATE':
        # ============================================================================
        # Update existing targets that match the target criteria
        # ============================================================================
        # ============================================================================
        # Fetch all the valid database targets from the InventoryDB and
        # check each one database by database
        # Attempt to query that target and record the results
        # ============================================================================

        # Get ALL the active targets
        target_cursor.execute(target_query)
        all_targets = target_cursor.fetchall()
        # TargetLogger.debug("All Targets: %s" , all_targets)

        inventory_conn.close()

        ######################################################
        # * * * *  Main Loop of all in-scope Targets * * * * #
        ######################################################
        for inventory_id, instance_name, owner, home_dir, host_name, target_type in all_targets:
            result = 0
            target_logger.debug("inventory_id: %s instance_name: %s owner: %s home_dir: %s host_name: %s target_type: "
                                "%s",
                                inventory_id, instance_name, owner, home_dir, host_name, target_type)

            old_handler = ''
            ###############################################################################
            # Sub Loop of All Checks for the Target
            # Reuse the connection to the target for all similar checks with same handler
            ###############################################################################
            for check, check_type, result_column, handler in all_checks:
                result = ''
                if handler != old_handler:
                    if old_handler != '' and curr_connection != '':
                        # Targets.Disconnect(curr_connection)
                        curr_connection.close()
                    old_handler = handler
                    rc, curr_connection = targets.connect(host_name, instance_name, owner, handler, target_logger)

                if curr_connection:  # connection still works
                    rc, result = targets.get_info(check, handler, curr_connection, target_logger)
                    print('Result: %s', result)
                    if result:
                        targets.update_column(inventory_id, result_column, result, target_logger)

                else:  # connection no longer works
                    targets.update_column(inventory_id, 'status', 'No ' + handler + ' Connection', target_logger)

                target_logger.info("Inventory ID: %s Attribute: %s Value: %s", inventory_id, result_column, result)

            # Targets.Disconnect(curr_connection)
            curr_connection.close()

    # ============================================================================
    # Look for and add NEW Targets to the inventory
    # ============================================================================

    elif check_type == 'ADD':
        # ============================================================================
        # Read through the target_file record by record
        # Attempt to query that target and record the results
        # DB Record Format: 1) host_instance 2) owner FID 3) homedir 4) listener 5) ports
        # Server Record Format: 1) hostname 2) IP Address
        # ============================================================================
        with open(TARGET_FILE) as tf:
            for entry in tf:
                target_logger.info('Parsing new line: %s', entry)
                target = "NONE"
                result = "NONE"
                inventory_id = 0
                entry = entry.strip()
                scan_list = entry.split(",")

                if target_type == "Server":
                    if len(scan_list) == 2:
                        host_name, owner = entry.split(",")
                    else:
                        owner = "fidBIN"

                    host_name = entry.upper().strip()
                    owner = owner.strip()
                    target = host_name + "_" + host_name
                    instance_name = host_name
                    ports = '22'
                    home_dir, exists = '', ''
                else:

                    if len(scan_list) > 4:
                        target, owner, home_dir, listener, *ports = entry.split(",")
                    elif len(scan_list) == 4:
                        target, owner, home_dir, listener = entry.split(",")
                        ports = 1521, 2349
                    elif len(scan_list) == 3:
                        target, owner, home_dir = entry.split(",")
                        exists = ''
                        ports = 1521, 2349
                    elif len(scan_list) == 2:
                        target, owner = entry.split(",")
                        home_dir, exists = '', ''
                        ports = 1521, 2349
                    elif len(scan_list) == 1:
                        target = entry
                        owner, home_dir, exists = '', '', ''
                        ports = 1521, 2349

                    target = target.upper().strip()
                    owner = owner.strip()
                    # host, instance=target.split("_")     # Needed for oracle_discovery.ksh output
                    instance_name, host_name = target.split("_")

                if host_name > '' and instance_name > '':
                    target_logger.info('Checking target: %s', str(target))
                    # Try connecting to the database and get info if possible exists=Targets.CreateDBC(target, owner,
                    # TargetLogger) if exists >= 0 :  # -1 does not exist     0=host exists, 1=database and Cloud_DBC
                    # exist  2=Target exists Why add if already there?
                    inventory_id = targets.add(host_name, instance_name, 'TBD', '0', owner, home_dir, exists, 0,
                                               target_type, target_logger)
                    if inventory_id > 0:
                        result = 0
                        target_logger.debug(
                            "inventory_id: %s instance_name: %s owner: %s home_dir: %s host_name: %s target_type: %s",
                            inventory_id, instance_name, owner, home_dir, host_name, target_type)

                        old_handler = ''
                        ###############################################################################
                        # Sub Loop of All Checks for the Target
                        # Reuse the connection to the target for all similar checks with same handler
                        ###############################################################################
                        for check, check_type, result_column, handler in all_checks:
                            result = ''
                            if handler != old_handler:
                                if old_handler != '' and curr_connection != '':
                                    # Targets.Disconnect(curr_connection)
                                    curr_connection.close()
                                old_handler = handler
                                rc, curr_connection = targets.connect(host_name, instance_name,
                                                                      owner, handler, target_logger)

                            if curr_connection:  # connection still works
                                targets.update_column(inventory_id, 'status', handler + ' Connected', target_logger)
                                rc, result = targets.get_info(check, handler, curr_connection, target_logger)
                                print('Result: %s', result)
                                if result:
                                    targets.update_column(inventory_id, result_column, result, target_logger)

                            else:  # connection no longer works
                                targets.update_column(inventory_id, 'status', 'No ' + handler + ' Connection',
                                                      target_logger)

                            target_logger.info("inventory_id: %s Attribute: %s Value: %s", inventory_id, result_column,
                                               result)

                        # Targets.Disconnect(curr_connection)
                        targets.update_column(inventory_id, "lastcheckdate", str(datetime.now()), target_logger)
                        if curr_connection != '':
                            curr_connection.close()

                    else:
                        result = targets.reject(host_name, '', instance_name, exists, owner, home_dir, entry,
                                                target_type,
                                                target_logger)

                target_logger.info('host_name: %s instance_name: %s inventory_id: %s results: %s ',
                                   host_name, instance_name, inventory_id, result)


# ============================================================================
# END main program
# ============================================================================

if __name__ == "__main__":
    TargetLogger = start_logging(LOG_LEVEL, LOG_FILE, LOG_NAME)  # Log to File
    main(sys.argv[1:])
