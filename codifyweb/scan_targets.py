"""
# ============================================================================
# Name:         scan_targets.py
# Description:  Look for and add new targets into inventory, either from
#               an external file Or from recent check_results on monitored servers. 
#
# Input Files:  TARGETS Table
#               CHECKLIST table
#               .env
#
# Output:       Updates TARGETS Table
#               Log files to $LOG_DIR/Scan_Targets_$date.log
#
# Syntax:       scan_targets.py -a (Add from file) -t Database|Server -v Vendor
#
# Calls:        targets.connect,  targets.get_info
#               inventory.exec_sql, 
#               checks.get_checks, check_targets.do_checks
#
# Restrictions: Enter the correct python environment prior to running.
#               ex)  "source ~/<venv>/bin/activate"
#                           to enter the necessary virtual environment
# ============================================================================
#     """

from datetime import datetime
from pickle import NONE  # not included by default
from decouple import config  # Allows us to read .env
import sys, argparse  # Allows us to interact with the o/s
import traceback    # Allows us to get detailed exception info
from time import sleep
from inventory import Inventory
from target import Target
from inv_logging import start_logging  # Allows us to log to a file

# ---------------------------   MAIN PROGRAM   -------------------------------
def main(argv):
    # Set some default values
    TARGET_FILE = "./discovery.txt"
    ORACLE_BASE = config('ORACLE_BASE')
    ORACLE_HOME = config('ORACLE_HOME')
    TNS_ADMIN = "/u01/app/oracle/DBTools/"
    parallel_procs = 50

    log_dir = config('LOG_DIR')
    log_name = "Scan_Targets"
    log_file = log_dir + log_name + "_" + str(datetime.now().strftime('%Y-%m-%d_%H-%M-%S')) + ".log"
    log_level = 'INFO'
    log_to_console = 'OFF'

    # Log to File
    target_logger = start_logging(log_level, log_file, log_name, log_to_console)

    check_type = 'UPDATE'  # Default to scan / update existing known Targets
    target_type = 'Database'  # Default to database targets
    vendor = 'ORACLE'  # Default to Oracle database targets
    inventory = Inventory(target_logger)
    rc = inventory.connect()

    parser = argparse.ArgumentParser(description='Scan Targets.')
    parser.add_argument('-t', '--target_type', default='Database')
    parser.add_argument('-v', '--vendor', default='ALL')
    parser.add_argument('-d', '--check_type', default='DISCOVER')
    args = parser.parse_args()

    # Get ALL the checks to perform on these targets
    check_filter = {
        'AND': {
            'frequency': args.target_type
        },
        'OR': {
            'vendor': [args.vendor, 'ALL']
        }
    }

    checks_list = inventory.get_checks(check_filter)
    target_logger.info("# of checks found: %s", len(checks_list))
    # target_logger.info("All Checks: %s", checks_list)

    if args.check_type == 'ADD':
        # Read through the target_file record by record
        # Record Format: hostname, instance_name, owner, home_dir,
        # target_type, vendor
        try:
            with open(TARGET_FILE) as tf:
                for entry in tf :
                    list_entry = list(entry.split(','))
                    print('Entry: %s', str(entry))
                    if entry.find('#') == 0:
                        target_logger.info('Comment Only %s ', entry)
                    elif len(list_entry) < 4:
                        target_logger.error('Entry incomplete: %s Only %s ',
                                            entry, str(len(list_entry)))
                    else:
                        # These are the standard extract rules for Oracle
                        # Discovery Output
                        # hostname, instance_name, owner, home_dir,
                        # target_type, vendor = entry.split(',')
                        target = Target(
                            -1,  # initially set inventory_id to -1
                            list_entry[0].upper().strip(),
                            list_entry[1].strip(),
                            list_entry[2].strip(),
                            list_entry[3].strip(),
                            'Database', 'ORACLE','STANDALONE','Discovered',
                            target_logger,
                            port=0
                        )
                        # hostname = list_entry[0].upper().strip()
                        # instance_name = list_entry[1].strip()
                        # owner = list_entry[2].strip()
                        # home_dir = list_entry[3].strip()
                        # # target_type = list_entry[4].strip()
                        # # vendor = list_entry[5].strip()
                        # port=0
                        # version=''
                        # sw_release=''
                        # vendor='ORACLE'
                        # target_type='Database'

                        # These are the SQL Server Discovery format
                        # hostname, instance_name, owner, home_dir,
                        # target_type, vendor = entry.split(',')
                        # ex) CADDWD-115, 2014 (SP3) (KB4022619),
                        # Standard Edition (64-bit) ,
                        # Windows NT 6.3 <X64> , 1433
                        """
                        # hostname = list_entry[0][:list_entry[0].find('\\')]
                        hostname = list_entry[0].strip().upper()
                        instance_name = list_entry[1].strip()
                        instance_name = instance_name.strip()
                        owner = 'BELL\\fidBellDBC'
                        home_dir = ''
                        target_type = 'Database'
                        vendor = 'MSSQL'
                        sw_release = list_entry[2]
                        version = list_entry[3]
                        port = list_entry[5]
                        port = port.strip()
                        """

                        target_logger.debug('Adding: %s %s %s %s %s %s ',
                                            target.hostname,
                                            target.instance_name, target.owner,
                                            target.home_dir,
                                            target.target_type, target.vendor)
                        inventory.add(target)

                        if target.inventory_id > 0:
                            target_logger.info(
                                f'Added new: '
                                f'hostname: {target.hostname} '
                                f'instance_name: {target.instance_name} '
                                f'inventory_id: {target.inventory_id} ')
                            # rc = inventory.set_target_attribute(
                            #     target.inventory_id, 'version',
                            #     version + ' ' + sw_release)
                        else:
                            result = inventory.reject(target)
                            target_logger.info(
                                f'Rejecting: '
                                f'hostname: {target.hostname} '
                                f'instance_name: {target.instance_name} '
                                f'inventory_id: {target.inventory_id} '
                                f'results: {result} ')

        except BaseException as ex:
            # Get current system exception
            ex_type, ex_value, ex_traceback = sys.exc_info()

            # Extract unformatter stack traces as tuples
            trace_back = traceback.extract_tb(ex_traceback)

            # Format stacktrace
            stack_trace = list()

            for trace in trace_back:
                stack_trace.append("File : %s , Line : %d, Func.Name : %s, Message : %s" % (trace[0], trace[1], trace[2], trace[3]))

            print("Exception type : %s " % ex_type.__name__)
            print("Exception message : %s" % ex_value)
            print("Stack trace : %s" % stack_trace)

            return
        sys.exit()

    # Get newly discovered databases and add them
    elif args.check_type == 'DISCOVER':
        # Read through the monitoring results for new host and
        # instance combinations
        # Get the delta from what is already known in the inventory
        # DB Record Format: 1) host_instance
        # 2) instance_1 instance_2 ..... instance_n
        discover_query = """ select distinct lower(b.hostname), b.check_result
                              from server_team.targets a, server_team.check_results b
                             where lower(a.instance_name) = lower(b.hostname)
                               and check_column in ( 'pmon', 'pdbs' )
                               and check_date > ( sysdate - 7 )
                               and check_result is not null
                               and upper(check_result) != 'NONE'
                             union
                            select distinct lower(a.hostname), b.check_result
                              from dbc_team.targets a, dbc_team.check_results b
                             where a.inventory_id = b.inventory_id
                               and check_column in ( 'pmon', 'pdbs' )
                               and check_date > ( sysdate - 7 )
                               and check_result is not null
                               and upper(check_result) != 'NONE'
                             minus
                            select lower(hostname),instance_name from
                             dbc_team.targets
                           """

        rc, all_targets = inventory.exec_sql(discover_query, 'ALL')
        

        for hostname, instance_list in all_targets:
            if ',' in instance_list:
                instance_list = instance_list.split(",")
            else:
                instance_list = instance_list.split()
            for instance_name in instance_list:
                owner, instance_name = instance_name.split(":")
                target_logger.info(f'Checking target '
                                   f'Hostname: {str(hostname)} '
                                   f'Instance_name: {str(instance_name)} '
                                   f'Owner: {str(owner)} ')
                # Try connecting to the database and get info if possible
                # exists=targets.CreateDBC(target, owner, target_logger)
                # if exists >= 0 :  # -1 does not exist 0=host exists,
                # 1=database and Cloud_DBC
                # exist  2=Target exists Why add if already there?
                instance_name = instance_name.strip()
                hostname = hostname.strip()

                inventory_id = inventory.get_id(hostname, instance_name)
                if inventory_id == 0:
                    new_target = Target(
                        inventory_id=0,
                        hostname=hostname,
                        instance_name=instance_name,
                        owner=owner,
                        home_dir='',
                        vendor='ORACLE',
                        sub_type='STANDALONE',
                        target_type='Database',
                        version='',
                        support_tier='Discovered',
                        logger=target_logger
                    )
                    inventory.add(new_target)  # Rejects target if not added
                    # if new_target.inventory_id > 0:
                    #     result = 0
                    #     target_logger.debug(
                    #         "inventory_id: %s instance_name: %s hostname: %s target_type: %s",
                    #         inventory_id, instance_name, hostname, target_type)
                    # else:
                    #     result = targets.reject(INVENTORY_CONN, hostname, vendor, instance_name, 'REJECT', '', '', 'Failed to Add',target_type, target_logger)
                else:
                    target_logger.debug(f'Already in Inventory '
                                        f'Hostname: {str(hostname)} '
                                        f'Instance_name: {str(instance_name)}')
                    




















    rc = inventory.disconnect()
    target_logger.info("Completed running scan_target.py "
                       "with target_type=%s check_type=%s",
                       args.target_type, args.check_type)
    target_logger.info("======================================================"
                       "==============================")

# END main program


if __name__ == "__main__":


    main(sys.argv[1:])
