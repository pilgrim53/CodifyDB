from .inv_logging import start_logging
import smtplib
import psycopg2
import sys, getopt  # Allows us to interact with the o/s
import paramiko  # Allows us to ssh to the Database Servers
import threading  # Allows us to time and kill hung db connections
from datetime import datetime
from datetime import date
from decouple import config  # Allows us to read .env
# ============================================================================

# ============================================================================

# ============================================================================
# Set DBTools Environment and Global Variables
# ============================================================================
DBC_USER      = config('DBC_USER')
DBC_PWD       = config('DBC_PWD')
INV_USER      = config('INV_USER')
INV_PWD       = config('INV_PWD')
ORACLE_BASE   = config('ORACLE_BASE')
ORACLE_HOME   = config('ORACLE_HOME')
TNS_ADMIN     = config('TNS_ADMIN')
LOG_DIR       = config('LOG_DIR')
CODIFYDB_HOST = config('CODIFYDB_HOST')
CODIFYDB      = config('CODIFYDB')
INVENTORYDB = "dbname=" + CODIFYDB + " user=" + INV_USER + " password=" + INV_PWD + " host=" + CODIFYDB_HOST

GLOBAL_LOG_NAME = "Mighty_List"
GLOBAL_LOG_FILE = LOG_DIR + GLOBAL_LOG_NAME + "_" + str(date.today()) + ".log"
GLOBAL_LOG_LEVEL = 'DEBUG'

# ============================================================================
# ============================================================================
# ---------------------------     MAIN PROGRAM     -------------------------------
# ============================================================================
# ============================================================================
def main(argv):
    # Set some defaults
    frequency = 'HOURLY' 
    interval = '24'
    support_tier = 'ALL'
    target_type = 'Database'  # Default to Database right now for development

    check_query = 'select threshold, result_column from mightys where 1=1 '
    target_prefix = '''select hostname, instance_name, cast(check_date as text), check_result "ALERT" 
                       from target a, check_results b 
                      where a.inventory_id = b.inventory_id and check_column = '''
    target_suffix = ''


    query_stmt = """
              select a.inventory_id, hostname, a.instance_name, owner, version, home_dir, clustered as "RAC",
                 case when (select container from target b where a.inventory_id = b.inventory_id ) = 'CDB$ROOT' then 'CDB'
                      when (select container from target c where a.inventory_id = c.inventory_id ) = 'STANDALONE' then 'STANDALONE'
                      when (select container from target c where a.inventory_id = c.inventory_id ) = a.instance_name then 'STANDALONE'
                         else 'PDB'
                  end as "CDB/PDB"
                from target a
               where target_type='Database' and decommissioned is null
            order by hostname, instance_name; """

    try:
        opts, args = getopt.getopt(argv,":t:i:f:s:h")

    except getopt.GetoptError:
        print ('python mightys.py [ -t Database|Server -i <interval in HOURS>  -f [HOURLY|DAILY|WEEKLY] -s [GOLD|SILVER|BRONZE] ]')
        sys.exit(2)

    target_logger.debug('Command Options: %s  Arguments: %s ', opts, args)

    for opt, arg in opts:
        print("Option: {} Argument: {}".format(opt,arg))
        if opt == '-h':
            print ('python mightys.py -t [Database|Server] -i <interval in HOURS> -f [HOURLY|DAILY|WEEKLY] -s [GOLD|SILVER|BRONZE]')
            sys.exit()

        elif opt == "-t" :
            target_type = arg
            target_suffix += ' and target_type = \'' + target_type + '\''

    target_logger.info("Running mighty.py with TARGETTYPE=%s", target_type)
    target_logger.debug("Query: %s", query_stmt)

    # ============================================================================
    # Connect to the inventory DB to get the mighty checks
    # ============================================================================

    # Connect to the Inventory DB
    inventory_conn = psycopg2.connect(INVENTORYDB)
    mighty_cursor = inventory_conn.cursor()

    # Get ALL the checks to perform on these targets
    mighty_cursor.execute(query_stmt)
    targets = mighty_cursor.fetchall()

    ######################################################
    # * * * *   Main Loop of all Targets   * * * * #
    ######################################################
    TEXT = ''
    for inventory_id, hostname, instance_name, owner, version, home_dir, rac, container  in targets:
        target_logger.info("%s,%s,%s,%s,%s,%s,%s,%s",str(inventory_id), hostname, instance_name, owner, \
                                                     version, home_dir.strip(), rac, container)

    inventory_conn.close()


    target_logger.info("Completed mighty.py with TARGETTYPE=%s ", target_type)
    target_logger.info("====================================================================================")

# ============================================================================
# END main program
# ============================================================================
#
if __name__ == "__main__":
    target_logger=start_logging(GLOBAL_LOG_LEVEL, GLOBAL_LOG_FILE, GLOBAL_LOG_NAME)    # Log to File
    main(sys.argv[1:])

