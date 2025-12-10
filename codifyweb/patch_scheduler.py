"""
# ============================================================================
# Name:         patch_scheduler.py
# Description:  Monitors the PATCHING table and launches db_patch.py
#               for each entry scheduled in the next 15 days that does
#               not already have a successfuly pre-requisite check
#
# Input Files:  PATCHING Table
#               PATCHES table
#               .env
#
# Output:       Log files to $LOG_DIR/Patch_Scheduler_$date.log
#
# Syntax:       python patch_scheduler.py [-n or --no-pause]
#
# Calls:        inventory.connect, inventory.exec_sql, inventory.disconnect
#
# Restrictions: Enter the correct python environment prior to running.
#               ex)  "source ~/<venv>/bin/activate"
#                           to enter the necessary virtual environment
# ============================================================================
#     """
import argparse          # read parameter input
import datetime          # date, datetime, timedelta
import concurrent.futures # allows us to do multiple checks at once
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
# ============================================================================
# -------------------------     MAIN PROGRAM     -----------------------------
# ============================================================================
if __name__ == "__main__":
    # Set some default values
    log_dir = config('LOG_DIR')
    log_name = "Patch_Scheduler"
    log_file = log_dir + log_name + "_" + str(datetime.datetime.now().strftime('%Y-%m-%d')) + ".log"
    log_level = 'DEBUG'
    log_to_console = 'ON'

    # Log to File
    target_logger = start_logging(log_level, log_file, log_name, log_to_console)
    
    inventory = Inventory(target_logger)
    rc = inventory.connect()
    start = time.time
    rc = 0

    target_logger.info("Starting Cloud Non Prod Database Patch Scheduler")

    parser = argparse.ArgumentParser(description='Scan Targets.')
    parser.add_argument('-n', '--no-pause',  action='store_true')
    args = parser.parse_args()

    patch_list = inventory.get_patches()
    rc = inventory.disconnect()
    new_patch_list=[]

    # Give some user feedback and pause here before proceeding
    print('+=====================================================================================================================+')
    print('| ACTION     HOSTNAME                        DATABASE       VENDOR SW_RELEASE    APPLY TIME           TICKET          |')
    print('+=====================================================================================================================+')
    for p in patch_list:
        if p.ticket is None:
            p.ticket = ""
        if p.apply == 'SKIP':
            print("| No Action  " + p.host.ljust(32) + p.instance.ljust(15) + p.vendor.ljust(7) + \
                  str(p.sw_release).ljust(14) + str(p.sched).ljust(21) + p.ticket.ljust(16) + "|")
        elif p.apply == '':
            print("| Pre-check  " + p.host.ljust(32) + p.instance.ljust(15) + p.vendor.ljust(7) + \
                  str(p.sw_release).ljust(14) + str(p.sched).ljust(21) + p.ticket.ljust(16)+ "|")
            new_patch_list.append(p)
        elif p.apply == 'APPLY':
            print("| APPLY!     " + p.host.ljust(32) + p.instance.ljust(15) + p.vendor.ljust(7) + \
                  str(p.sw_release).ljust(14) + str(p.sched).ljust(21) + p.ticket.ljust(16)+ "|")
            new_patch_list.append(p)
    print('+=====================================================================================================================+')

    if not args.no_pause:
        input('Press CTRL-C to abort')

    # Turn the schedule into an actionable list.  ie remove any that are "SKIP"
    procs = []

    # Take the final list of patches and run them in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(patch, p.host, p.instance, p.rollbacks,
                        p.oneoffs, p.apply, p.sw_release, p.scp_copy, 
                        p.ticket) for p in new_patch_list ]

        # Before leaving see how they did and log the return codes.      
        for future in concurrent.futures.as_completed(futures):
            try: 
                target_logger.info("Completed Patching: %s", future.result())
            except:
                target_logger.error("Failed Patching on %s", str(future))

    target_logger.info("Patch Scheduling Completed at %s ", str(datetime.datetime.now()))
    target_logger.info("====================================================")

    # =======================================================================
    # END main program
    # =======================================================================

