import cx_Oracle
from inv_logging import start_logging
import sys, getopt  # Allows us to interact with the o/s
from datetime import date
from decouple import config  # Allows us to read .env
# ============================================================================
CODIFYWEB_DIR = config('CODIFYWEB_DIR')
sys.path.append(CODIFYWEB_DIR)
import targets
import results
import inventory

# Set  Environment and Global Variables
LOG_DIR = config('LOG_DIR')
GLOBAL_LOG_NAME = "Check_Targets"
GLOBAL_LOG_FILE = LOG_DIR + GLOBAL_LOG_NAME + "_" + str(date.today()) + ".log"
GLOBAL_LOG_LEVEL = 'DEBUG'
GLOBAL_LOG_TO_CONSOLE = "ON"

def main(argv):    
    """
# ============================================================================
# Name:         check_targets.py
# Description:  Monitors IT targets currently stored in the Codify "TARGETS" 
#               check results are stored and viewable in "CHECK_RESULTS"
#
# Input Files:  TARGETS Table
#               checklist table
#               $TNS_ADMIN/tnsnames.ora
#
# Output:       Monitoring Entries saved to the Check_Results table
#               Log files to $LOG_DIR/check_results_$date.log
# Syntax:       check_targets.py -t target_type -v vendor -f frequency -c check_type
#
# Calls:        cx_Oracle - for Oracle database calls
#               psycopg2 - for PostgreSQL database calls
#               date, grep, awk, cat, uname - misc UNIX commands
#
# Restrictions: Enter the correct python environment prior to running.
#               ex)  "source ~/<venv>/bin/activate"
#                           to enter the necessary virtual environment
# ============================================================================
#     """
    global vendor
    global frequency
    global check_type
    global target_type
    vendor = '%'
    frequency = 'HOURLY'  # Default to the hourly checks if not specified
    check_type = '%'
    target_type = 'Database'  # Default to Database right now for development

    check_query = 'select check_command, check_type, result_column, handler, sub_type, vendor from checklist where 1=1 '
    target_query = 'select inventory_id, instance_name, owner, home_dir, hostname,' \
                   ' target_type, sub_type, vendor from targets where decommissioned is null '

    try:
        opts, args = getopt.getopt(argv,":t:c:v:f:s:h")

    except getopt.GetoptError:
        print('check_targets.py [ -t Database|Server -c DB|OS -v <vendor> -f <frequency> -s <sub_type> ]')
        sys.exit(2)

    target_logger.info('Command Options: %s  Arguments: %s ', opts, args)

    for opt, arg in opts:
        print("Option: {} Argument: {}".format(opt, arg))
        if opt == '-h':
            print('check_targets.py -t [Database|Server] -c [DB|OS] -v [ORACLE|SUNOS|LINUX|AIX] -f [HOURLY|DAILY|WEEKLY] -s [CDB|PDB|STANDALONE]')
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

        elif opt == "-s":
            sub_type = arg
            target_query += ' and sub_type =  \'' + sub_type + '\''
            check_query += ' and sub_type = \'' + sub_type + '\''

        elif opt == "-f":
            frequency = arg

    check_query += ' and frequency = \'' + frequency + '\'  order by handler, priority'
    target_query += ' and target_type = \'' + target_type + '\' order by inventory_id'

    target_logger.info("Running check_targets.py with TARGETTYPE=%s VENDOR=%s FREQUENCY=%s CHECKTYPE=%s", target_type,
                       vendor, frequency, check_type)
    target_logger.info("Check Query: %s", check_query)
    target_logger.info("Target Query: %s", target_query)

    # Get ALL the matching active targets from the inventory
    RC, all_targets=inventory.exec_sql(target_query, 'ALL', target_logger)
    target_logger.debug("# of Targets: %s", len(all_targets))

    # Get ALL the checks to perform on these targets
    RC, all_checks=inventory.exec_sql(check_query, 'ALL', target_logger)  
    target_logger.info("All Checks: %s", all_checks)
    
    # Build the set of handlers required 
    handlers=set()
    for check, check_type, result_column, handler, check_sub_type, check_vendor in all_checks:
        handlers.add(handler)

    handler_list=list(handlers)

    for inventory_id, instance_name, owner, home_dir, hostname, target_type, target_sub_type, vendor in all_targets:
        target_logger.debug("inventory_id: %s instance_name: %s owner: %s home_dir: %s hostname: %s target_type: %s target_sub_type: %s",
                            inventory_id, instance_name, owner, home_dir, hostname, target_type, target_sub_type)

        connection = {} # dictionary of connections
        x = 0
        for handler in handler_list :
            rc, curr_connection = targets.connect(hostname, instance_name, owner, handler, target_logger)
            if rc == 1 : 
                connection[x] = curr_connection
            else :
                 connection[x] = ''
            x = +x

        # Sub Loop of All Checks for the Target
        for check, check_type, result_column, handler, check_sub_type, check_vendor in all_checks:
          if (check_vendor == 'ALL' ) or ( check_vendor == vendor ):
            result = ''

            if connection[handler_list.index(handler)] != '' :
                # if check_sub_type == "" or ( check_sub_type == target_sub_type) :
                if handler == 'OMS':  # Need to do this here because we need hostname and instance_name
                    check = f"{check.format(hostname, instance_name)}"  

                info_rc, result = targets.get_info(check, handler, connection[handler_list.index(handler)], target_logger)
                target_logger.debug("Inventory ID: %s Attribute: %s Value: %s RC: %s", inventory_id, result_column,
                                    result, info_rc)
                if info_rc == 1:
                    results.add(inventory_id, result, result_column, target_logger)

        for x in range(len(handlers))  :
            if connection[x] != '' :
                connection[x].close

    target_logger.info("Completed running check_targets.py with target_type=%s vendor=%s frequency=%s check_type=%s",
                       target_type, vendor, frequency, check_type)
    target_logger.info("====================================================================================")

# END main program

if __name__ == "__main__":
    target_logger = start_logging(GLOBAL_LOG_LEVEL, GLOBAL_LOG_FILE, GLOBAL_LOG_NAME, GLOBAL_LOG_TO_CONSOLE)    # Log to File
    main(sys.argv[1:])