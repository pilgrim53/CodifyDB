# ============================================================================
# Name:         check_patch.py
# Description:  Query status of Oracle DB Patch request from the PATCHING Schedule
#
# Input Files:  PATCHING Table
#               .env
#
# Output:       Log files to $LOG_DIR/Check_Patch_$date.log
#
# Syntax:       python check_patch.py hostname dbname sched service_now#
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
   rc = 0
   log_dir = config('LOG_DIR')
   log_name = "Check_Patch"
   log_file = log_dir + log_name + "_" + str(datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')) + ".log"
   log_level = 'INFO'
   log_to_console = 'OFF'

   # Log to File
   target_logger = start_logging(log_level, log_file, log_name, log_to_console)

   inventory = Inventory(target_logger)

   target_logger.info("Executing the check_patch.py")

   hostname =    os.environ.get('HOST').lower()
   db =          os.environ.get('DB')
   sched_dt_tm = os.environ.get('SCHED_DT_TM')
   ritm =        os.environ.get('RITM')

   if ritm is not None :
       try:
           rc = inventory.connect()
       except ConnectionError as e:
           target_logger.error(f"Failed to connect to the inventory: {str(e)}")
           sys.exit(1)

       start = time.time
       chk_issues = f"SELECT NVL(PATCH_ISSUES,'999') FROM DBC_TEAM.PATCHING where ticket =\'{ritm}\'"
       rc1, patch_results = inventory.exec_sql(chk_issues, 'ONE')
       if patch_results :
          # if patch_results[0] is not None:
           rc = int(str(patch_results[0]))
       else :
           rc = 999

       sql_stmt = (f"SELECT 'Hostname: ' || hostname || '  Database: ' || instance_name "
                   f"|| '  Patch Date: ' || to_char(PATCH_DATE,'YYYY-DD-MM HH24:MM') "
                   f"|| '  Patch Level: ' || POST_SW_RELEASE || '  Patch Issues: ' || NVL(PATCH_ISSUES,999) "
                   f"FROM DBC_TEAM.PATCHING where ticket ='{ritm}'")

       target_logger.debug("Running  %s ", sql_stmt)
       rc2, patch_results = inventory.exec_sql(sql_stmt, 'ONE')
       if  patch_results :
           target_logger.info(f"Ticket: {ritm} Hostname: {hostname} Instance: {db} scheduled for: {sched_dt_tm}")
           target_logger.info(f"Full Patch result: {str(patch_results[0])}")

           print(f"RC:{rc}")
           print(f"Full Patch result: {str(patch_results[0])}")

       else:
           rc == 999
           print(f"RC:{rc}")
           print(f"Full Patch result: No Data Found")

       target_logger.info(f"Check Patch Completed at {str(datetime.datetime.now())} Return Code: {rc}")
       target_logger.info("====================================================")

   else:
       target_logger.error(f"Missing RITM: {ritm} ")

   # =======================================================================
   # END main program
   # =======================================================================

if __name__ == "__main__":
   main()
   