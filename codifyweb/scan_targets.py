from datetime import date, datetime  # not included by default
from decouple import config  # Allows us to read .env
import sys, getopt  # Allows us to interact with the o/s
import cx_Oracle
import traceback    # Allows us to get detailed exception info

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
LOG_LEVEL = "DEBUG"
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
    vendor = 'ORACLE'  # Default to Oracle database targets
    target_query = 'select inventory_id, instance_name, owner, home_dir, hostname, target_type, vendor \
                      from targets where decommissioned is null '

    try:
        opts, args = getopt.getopt(argv, ":t:v:adh")

    except getopt.GetoptError:
        print('scan_targets.py [ -a (ADD) -t Database|Server -v Vendor  ] | -h (help) ')
        sys.exit(2)

    target_logger.info('Command Options: %s  Arguments: %s ', opts, args)

    for opt, arg in opts:
        target_logger.debug("Option: {} Argument: {}".format(opt, arg))
        if opt == '-h':
            print('scan_targets.py [ -t Database|Server -v Vendor -a (ADD) ] | -h (help) ')
            sys.exit()

        elif opt == "-a":
            check_type = 'ADD'

        elif opt == "-d":
            check_type = 'DISCOVER'
                
        elif opt == "-v":
            vendor = arg
                
        elif opt == "-t":
            target_type = arg

    target_query += ' and upper(target_type) = \'' + target_type.upper() + '\' order by inventory_id desc'

    check_query = 'select check_command, check_type, result_column, handler, sub_type, vendor from checklist \
                   where upper(vendor) = \'' +vendor.upper()+'\' and upper(frequency)=\''+target_type.upper()+'\' order by handler, priority'



    target_logger.info("Running scan_target.py with target_type=%s check_type=%s", target_type, check_type)
    target_logger.info("Check Query: %s", check_query)
    target_logger.info("Target Query: %s", target_query)

    # Collect alll the applicable monitoring "checks"
    rc, all_checks=inventory.exec_sql(check_query, 'ALL', target_logger)

    if check_type == 'ADD':
        # Read through the target_file record by record
        # Record Format: hostname, instance_name, owner, home_dir, target_type, vendor
        try: 
            with open(TARGET_FILE) as tf:
                for entry in tf :
                    list_entry=list(entry.split(','))
                    print('Entry: %s' , str(entry) )
                    if entry.find('#') == 0 :
                        target_logger.info('Comment Only %s ', entry)
                    elif len(list_entry) != 5 :
                        target_logger.error('Entry incomplete: %s Only %s ', entry, str(len(list_entry)))
                    elif len(list_entry) == 5:
                        """ 
                        These are the standard extract rules for Oracle Discovery Output
                        # hostname, instance_name, owner, home_dir, target_type, vendor = entry.split(',')
                        hostname = strip(list_entry[0])
                        instance_name = strip(list_entry[1])
                        owner = strip(list_entry[2])
                        home_dir = strip(list_entry[3])
                        target_type = strip(list_entry[4])
                        vendor = strip(list_entry[5])
                        """
                        """ 
                        These are the SQL Server Discovery format
                        # hostname, instance_name, owner, home_dir, target_type, vendor = entry.split(',')
                        # ex) CADDWD-115, 2014 (SP3) (KB4022619), Standard Edition (64-bit) , Windows NT 6.3 <X64> , 1433
                        """
                        hostname = list_entry[0][:list_entry[0].find('\\')]
                        hostname = hostname.strip()
                        instance_name = list_entry[0]
                        instance_name = instance_name.strip()
                        owner = 'BELL\\fidBellDBC'
                        home_dir = ''
                        target_type = 'Database'
                        vendor = 'MSSQL'
                        port = list_entry[4]
                        port = port.strip()
                        target_logger.debug('Adding: %s %s %s %s %s %s ', hostname, instance_name, owner, home_dir, target_type, vendor)
                        inventory_id = targets.add(hostname, instance_name, instance_name, '0', owner, home_dir, 'ADD', port , target_type, target_logger, vendor)
                                 #def add(host, instance, container, DBID, owner, home_dir, status, port, target_type, target_logger, vendor='ORACLE'):
                    
                        if inventory_id > 0:
                            target_logger.info('Added new:  hostname: %s instance_name: %s inventory_id: %s ',
                                    hostname, instance_name, inventory_id)
                        else:
                            result = targets.reject(hostname, vendor, instance_name, 'REJECT', owner, home_dir, 'Failed to Add',target_type, target_logger)
                            target_logger.info('Rejecting:  hostname: %s instance_name: %s inventory_id: %s results: %s ', hostname, instance_name, inventory_id, result)



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
            print("Exception message : %s" %ex_value)
            print("Stack trace : %s" %stack_trace)

            return
        sys.exit()
  
    # Get newly discovered databases and add them
    elif check_type == 'DISCOVER':
        # Read through the monitoring results for new host and instance combinations
        # Get the delta from what is already known in the inventory
        # DB Record Format: 1) host_instance 2) instance_1 instance_2 ..... instance_n
        discover_query=""" select distinct substr(a.hostname,1,50), cast(upper(b.check_result)as varchar2(255))
from server_team.targets a, server_team.check_results b
where a.inventory_id = b.inventory_id
and (( check_column = 'pmon') or ( check_column = 'pdbs'))
--and to_timestamp(check_date,'YYYY-MM-DD HH24:MI:SS.FF') > ( sysdate -7 )
-- and check_result not like '%near line 1%'
and check_result is not null
minus
select substr(hostname,1,50), substr(instance_name,1,50) from codify.targets; """

        rc, all_targets=inventory.exec_sql(discover_query, 'ALL', target_logger)

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
                else:
                    result = targets.reject(hostname, vendor, instance_name, 'REJECT', owner, home_dir, 'Failed to Add',target_type, target_logger)
                    target_logger.info('Rejecting:  hostname: %s instance_name: %s inventory_id: %s results: %s ',
                                hostname, instance_name, inventory_id, result)


    # Get ALL the active targets from the inventory now that Add and Discover are completed.
    rc, all_targets=inventory.exec_sql(target_query, 'ALL', target_logger)
    # print(all_targets)
    # Main Loop of all in-scope Targets - check each one database by database
    for inventory_id, instance_name, owner, home_dir, hostname, TargetType, target_vendor in all_targets:
        target_logger.debug("inventory_id: %s instance: %s owner: %s home_dir: %s hostname: %s TargetType: %s",
                            inventory_id, instance_name, owner, home_dir, hostname, TargetType)

        # Build the set of handlers required for this target
        handlers=set()
        for check, check_type, result_column, handler, check_sub_type, check_vendor in all_checks:
            if ( check_vendor == target_vendor ) or ( check_vendor == 'ALL' ) :
                handlers.add(handler)

        handler_list=list(handlers)

        connection = [''] * len(handler_list)  # dictionary of connections
        x = 0
        for handler in handler_list :
            rc, connection[x] = targets.connect(hostname, instance_name, owner, handler, target_logger)
            inventory.add_results(inventory_id, handler + ':' + str(rc), 'access', target_logger)
            x += 1

        # Sub Loop to perform all Checks for the Target
        for check, check_type, result_column, handler, check_sub_type, check_vendor in all_checks:
          if (check_vendor.upper() == 'ALL' ) or ( check_vendor.upper() == target_vendor.upper() ):
            result = ''
            # print(check)
            if connection[handler_list.index(handler)] != '' :
                # if check_sub_type == "" or ( check_sub_type == target_sub_type) :
                if handler == 'OMS':  # Need to do this here because we need hostname and instance_name
                    # remove_digits = str.maketrans('', '', digits)
                    # instance_name = instance_name.translate(remove_digits)   # Strip the numeral off the end if exists
                    check = f"{check.format(hostname, instance_name)}"

                info_rc, result = targets.get_info(check, handler, connection[handler_list.index(handler)], target_logger)
                target_logger.debug("Inventory ID: %s Attribute: %s Value: %s RC: %s", inventory_id, result_column,
                                    result, info_rc)
                if info_rc == 1:
                    targets.update_column(inventory_id, result_column, result, target_logger)

        for x in range(len(handler_list))  :
            if connection[x] != '' :
                connection[x].close

    target_logger.info("Completed running scan_target.py with target_type=%s check_type=%s",
                       target_type, check_type)
    target_logger.info("====================================================================================")
                               
# END main program

if __name__ == "__main__":
    target_logger = start_logging(LOG_LEVEL, LOG_FILE, LOG_NAME, LOG_TO_CONSOLE)  # Log to File
    main(sys.argv[1:])
