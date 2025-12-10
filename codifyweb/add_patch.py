# ============================================================================
# Name:         add_patch.py
# Description:  Insert an Oracle DB Patch request into the PATCHING Schedule
#
# Input Files:  PATCHING Table
#               .env
#
# Output:       Log files to $LOG_DIR/Add_Patch_$date.log
#
# Syntax:       python add_patch.py hostname dbname sched service_now#
#
# Calls:        inventory.connect, inventory.exec_sql, inventory.disconnect
#
# Restrictions: Enter the correct python environment prior to running.
#               ex)  "source ~/<venv>/bin/activate"
#                           to enter the necessary virtual environment
# ============================================================================
import sys               # Allows us to interact with the o/s
import datetime          # date, datetime, timedelta
import os
import time
from time import sleep
from tracemalloc import start
from decouple import config  # Allows us to read .env
from threading import TIMEOUT_MAX
from patch import Patch
# ============================================================================
# Now import local modules
# ============================================================================
from inv_logging import start_logging
from inventory import Inventory
from db_patch import patch
# ============================================================================

# ============================================================================
# Function:     main
# Description:  Top-level function
# ============================================================================
def main():
    # Set some default values
    log_dir = config('LOG_DIR')
    log_name = "Add_Patch"
    log_file = log_dir + log_name + "_" + str(datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')) + ".log"
    log_level = 'DEBUG'
    log_to_console = 'ON'

    # Log to File
    target_logger = start_logging(log_level, log_file, log_name, log_to_console)
    inventory = Inventory(target_logger)

    target_logger.info("Adding Oracle DB Patch to the Schedule")

    hostname = os.environ.get('HOST').lower()
    db = os.environ.get('DB')
    sched_dt_tm = os.environ.get('SCHED_DT_TM')  # format ex) "2024-06-20 14:01:00"
    ritm = os.environ.get('RITM')

    rc = inventory.connect()
    start = time.time
    RC = 1 # zero return code is good o/s exit code

    if hostname  and  db  and  sched_dt_tm  and  ritm :
        inventory_id = int(inventory.get_id(hostname, db, 'Database'))
        if inventory_id > 0 :
            # we need to get vendor, version and latest PSU for that version
            target_info=inventory.get_targets('Database','ALL',inventory_id,inventory_id+1)
            target_logger.debug(f"This is: {target_info}")

            insert_stmt = f"INSERT INTO DBC_TEAM.PATCHING (HOSTNAME, INSTANCE_NAME, VENDOR, SCHED_DATE_TIME, TICKET)"
            insert_stmt += f" VALUES (\'{hostname}\', \'{db}\', \'{target_info[0].vendor}\', to_date(\'{sched_dt_tm}\',\'YYYY-MM-DD HH24:MI:SS\'),\'{ritm}\')"
            target_logger.debug("Running  %s ", insert_stmt)
            rc, exec_out = inventory.exec_sql(insert_stmt, 'EXEC')
            if rc != 1 :  #  1 is good python exit
                target_logger.error("FAILED: Oracle DB Patch NOT added to the Schedule")
                RC = 99
            else:
                RC = 0 # All is well
        else:
            target_logger.error("FAILED: Oracle DB Not found in NonProd Inventory")
    else :
        target_logger.error("FAILED: add_patch.py requires 4 environment variables set: HOST, DB, SCHED_DT_TM, RITM. ")
    
    rc2 = inventory.disconnect()

    target_logger.info("Add Patch ended at %s ", str(datetime.datetime.now()))
    target_logger.info("====================================================")

    sys.exit(RC)

    # =======================================================================
    # END main program
    # =======================================================================

if __name__ == "__main__":
    main()
    