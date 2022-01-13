from datetime import date, datetime  # not included by default
from decouple import config  # Allows us to read .env
import sys, getopt  # Allows us to interact with the o/s
import cx_Oracle


CODIFYWEB_DIR = config('CODIFYWEB_DIR')
sys.path.append(CODIFYWEB_DIR)
import inventory
import targets  # All target functions
from inv_logging import start_logging  # Allows us to log to a file

# Set  Environment and Global Variables
TARGET_FILE = "./discovery.txt"
LOG_DIR = config('LOG_DIR')
LOG_NAME = "Scan_Targets"
LOG_FILE = LOG_DIR + LOG_NAME + "_" + str(date.today()) + ".log"
LOG_LEVEL = "INFO"
LOG_TO_CONSOLE = "ON"
ORACLE_BASE = config('ORACLE_BASE')
ORACLE_HOME = config('ORACLE_HOME')
TNS_ADMIN = "/u01/app/oracle/DBTools/"

# ---------------------------   MAIN PROGRAM   -------------------------------
# Evaluate target info and look for changes to targets. Then insert new or update existing records in Targets table
# Input:  -a (ADD) -t Database|Server -v Vendor
def main(argv):
    global check_type
    global target_type
    check_type = 'UPDATE'  # Default to scan / update existing known Targets
    target_type = 'Database'  # Default to database targets
    target_query = 'select inventory_id, instance_name, owner, home_dir, hostname, target_type, vendor \
                      from targets where decommissioned is null '

    try:
        opts, args = getopt.getopt(argv, ":t:v:adh")

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
        elif opt == "-d":
            check_type = 'DISCOVER'
                
        elif opt == "-t":
            target_type = arg
            target_query += ' and target_type = \'' + target_type + '\''
        elif opt == "-v":
            vendor = arg
            target_query += ' and vendor = \'' + vendor + '\''

    target_query += ' order by inventory_id '

    check_query = "select check_command, check_type, result_column, handler, vendor from checklist \
                    where frequency='" + target_type + "' order by handler, priority"

    target_logger.info("Running scan_target.py with target_type=%s check_type=%s", target_type, check_type)
    target_logger.info("Check Query: %s", check_query)
    target_logger.info("Target Query: %s", target_query)

    # Collect alll the applicable monitoring "checks"
    all_checks=inventory.exec_sql(check_query, 'ALL', target_logger)

    if check_type == 'UPDATE':
        # Get ALL the active targets
        all_targets=inventory.exec_sql(target_query, 'ALL', target_logger)

        # Main Loop of all in-scope Targets - check each one database by database
        for inventory_id, instance, owner, home_dir, hostname, TargetType, target_vendor in all_targets:
            result = 0
            target_logger.debug("inventory_id: %s instance: %s owner: %s home_dir: %s hostname: %s TargetType: %s",
                                inventory_id, instance, owner, home_dir, hostname, TargetType)

            old_handler = ''

            # Sub Loop of All Checks for the Target
            # Reuse the connection to the target for all similar checks with same handler
            for check, check_type, result_column, handler, check_vendor in all_checks:
              if check_vendor == "ALL" or ( check_vendor == target_vendor ) :
                result = ''
                if handler != old_handler:
                    if old_handler != '' and curr_connection != '':
                        try:
                            curr_connection.close()
                        except cx_Oracle.DatabaseError as exc:
                            error, = exc.args
                            target_logger.error("DatabaseError-Code: %s %s ", error.code, error.message)

                    old_handler = handler
                    rc, curr_connection = targets.connect(hostname, instance, owner, handler, target_logger)

                if curr_connection:  # connection still works
                    rc, result = targets.get_info(check, handler, curr_connection, target_logger)
                    if result:
                        targets.update_column(inventory_id, result_column, result, target_logger)

                else:  # connection no longer works
                    targets.update_column(inventory_id, 'status', 'No ' + handler + ' Connection', target_logger)

                target_logger.info("Inventory ID: %s Attribute: %s Value: %s", inventory_id, result_column, result)

            if curr_connection !='' :
                try:
                    curr_connection.close()
                except cx_Oracle.DatabaseError as exc:
                    error, = exc.args
                    target_logger.error("DatabaseError-Code: %s %s ", error.code, error.message)

    # Look for and add NEW Targets to the inventory
    elif check_type == 'ADD':
        # Read through the target_file record by record
        # Attempt to query that target and record the results
        # DB Record Format: 1) host_instance 2) owner FID 3) home_dir 4) listener 5) ports
        # Server Record Format: 1) hostname 2) IP Address
        with open(TARGET_FILE) as tf:
            for entry in tf:
                target_logger.info('Parsing new line: %s', entry)
                target = "NONE"
                result = "NONE"
                inventory_id = 0
                entry = entry.strip()
                scan_list = entry.split(",")
                home_dir, exists = '', ''

                if target_type == "Server":
                    if len(scan_list) == 2:
                        hostname, owner = entry.split(",")
                    else:
                        owner = "fidBIN"

                    hostname = entry.upper().strip()
                    owner = owner.strip()
                    target = hostname + "_" + hostname
                    instance_name = hostname
                    ports = '22'
                else:
                    if len(scan_list) > 4:
                        target, owner, home_dir, listener, *ports = entry.split(",")
                    elif len(scan_list) == 4:
                        target, owner, home_dir, listener = entry.split(",")
                        exists = ''
                        ports = 1521, 2349
                    elif len(scan_list) == 3:
                        target, owner, home_dir = entry.split(",")
                        ports = 1521, 2349
                    elif len(scan_list) == 2:
                        target, owner = entry.split(",")
                        ports = 1521, 2349
                    elif len(scan_list) == 1:
                        target = entry
                        owner, home_dir, exists = '', '', ''
                        ports = 1521, 2349

                    target = target.upper().strip()
                    owner = owner.strip()
                    # host, instance=target.split("_")     # Needed for oracle_discovery.ksh output
                    instance_name, hostname = target.split("_")

                if hostname > '' and instance_name > '':
                    target_logger.info('Checking target: %s', str(target))
                    # Try connecting to the database and get info if possible exists=targets.CreateDBC(target, owner,
                    # target_logger) if exists >= 0 :  # -1 does not exist     0=host exists, 1=database and Cloud_DBC
                    # exist  2=Target exists Why add if already there?
                    inventory_id = targets.add(hostname, instance_name, 'TBD', '0', owner, home_dir, exists, 0,
                                               target_type, target_logger)
                    if inventory_id > 0:
                        result = 0
                        target_logger.debug(
                            "inventory_id: %s instance_name: %s owner: %s home_dir: %s hostname: %s target_type: %s",
                            inventory_id, instance_name, owner, home_dir, hostname, target_type)

                        old_handler = ''

                        # Sub Loop of All Checks for the Target
                        # Reuse the connection to the target for all similar checks with same handler
                        for check, check_type, result_column, handler, check_vendor in all_checks:
                            result = ''
                            if handler != old_handler:
                                if old_handler != '' and curr_connection != '':
                                    try:
                                        curr_connection.close()
                                    except cx_Oracle.DatabaseError as exc:
                                        error, = exc.args
                                        target_logger.error("DatabaseError-Code: %s %s ", error.code, error.message)

                                old_handler = handler
                                rc, curr_connection = targets.connect(hostname, instance_name,
                                                                      owner, handler, target_logger)

                            if curr_connection !='' :  # connection still works
                                targets.update_column(inventory_id, 'status', handler + ' Connected', target_logger)
                                rc, result = targets.get_info(check, handler, curr_connection, target_logger)
                                if result:
                                    targets.update_column(inventory_id, result_column, result, target_logger)

                            else:  # connection no longer works
                                targets.update_column(inventory_id, 'status', 'No ' + handler + ' Connection',
                                                      target_logger)

                            target_logger.info("inventory_id: %s Attribute: %s Value: %s", inventory_id, result_column,
                                               result)

                        # targets.Disconnect(curr_connection)
                        targets.update_column(inventory_id, "last_check_date", str(datetime.now()), target_logger)
                        if curr_connection != '':
                            try:
                                curr_connection.close()
                            except cx_Oracle.DatabaseError as exc:
                                error, = exc.args
                                target_logger.error("DatabaseError-Code: %s %s ", error.code, error.message)

                        else:
                            result = targets.reject(hostname, '', instance_name, exists, owner, home_dir, entry,
                                                    target_type, target_logger)

                target_logger.info('hostname: %s instance_name: %s inventory_id: %s results: %s ',
                                   hostname, instance_name, inventory_id, result)

    # Get newly discovered databases and add them
    elif check_type == 'DISCOVER':
        # Read through the monitoring results
        # Get the delta from what is already known in the inventory
        # DB Record Format: 1) host_instance 2) instance_1 instance_2 ..... instance_n
        target_query="""select distinct a.hostname, upper(b.check_result)
                          from target a, check_results b
                           and (( check_column = 'pmon') or ( check_column = 'pdbs'))
                           and check_date > ( SELECT NOW() - INTERVAL '7 DAYS')
                           and check_result not like '%near line 1%'
                           and check_result not like ''
                  except select hostname, instance_name from target;  """

        all_targets=inventory.exec_sql(target_query, 'ALL', target_logger)

        for hostname, instance_list in all_targets :
            instance_list = instance_list.split(" ")
            for instance_name in instance_list:
                target_logger.info('Checking target Hostname: %s Instance_name: %s ', str(hostname), str(instance_name))
                # Try connecting to the database and get info if possible exists=targets.CreateDBC(target, owner,
                # target_logger) if exists >= 0 :  # -1 does not exist     0=host exists, 1=database and Cloud_DBC
                # exist  2=Target exists Why add if already there?
                inventory_id = targets.add(hostname, instance_name, 'TBD', '0', '', '', '', 0,
                                           target_type, target_logger)
                if inventory_id > 0:
                    result = 0
                    target_logger.debug(
                        "inventory_id: %s instance_name: %s hostname: %s target_type: %s",
                        inventory_id, instance_name, hostname, target_type)

                    old_handler = ''

                    # Sub Loop of All Checks for the Target
                    # Reuse the connection to the target for all similar checks with same handler
                    for check, check_type, result_column, handler, check_vendor in all_checks:
                        result = ''
                        if handler != old_handler:
                            if old_handler != '' and curr_connection != '':
                                try:
                                    curr_connection.close()
                                except cx_Oracle.DatabaseError as exc:
                                    error, = exc.args
                                    target_logger.error("DatabaseError-Code: %s %s ", error.code, error.message)

                            old_handler = handler
                            rc, curr_connection = targets.connect(hostname, instance_name, '', handler, target_logger)
                            target_logger.info("Connecting to Host: %s Instance: %s returned: %s ", hostname,
                                               instance_name, rc)

                        if curr_connection:  # connection still works
                            targets.update_column(inventory_id, 'status', handler + ' Connected', target_logger)
                            rc, result = targets.get_info(check, handler, curr_connection, target_logger)
                            if result:
                                targets.update_column(inventory_id, result_column, result, target_logger)

                        else:  # connection no longer works
                            targets.update_column(inventory_id, 'status', 'No ' + handler + ' Connection',
                                                  target_logger)

                        target_logger.info("inventory_id: %s Attribute: %s Value: %s", inventory_id, result_column,
                                           result)

                        # targets.Disconnect(curr_connection)
                        targets.update_column(inventory_id, "last_check_date", str(datetime.now()), target_logger)
                        if curr_connection != '':
                            try:
                                curr_connection.close()
                            except cx_Oracle.DatabaseError as exc:
                                error, = exc.args
                                target_logger.error("DatabaseError-Code: %s %s ", error.code, error.message)

            else:
                result = targets.reject(hostname, '', instance_name, '', '', '', '',target_type, target_logger)

            target_logger.info('hostname: %s instance_name: %s inventory_id: %s results: %s ',
                               hostname, instance_name, inventory_id, result)
    target_logger.info("Completed running scan_target.py with target_type=%s check_type=%s",
                       target_type, check_type)
    target_logger.info("====================================================================================")
                               
# END main program


if __name__ == "__main__":
    target_logger = start_logging(LOG_LEVEL, LOG_FILE, LOG_NAME, LOG_TO_CONSOLE)  # Log to File
    main(sys.argv[1:])
