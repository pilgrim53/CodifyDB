"""
# ============================================================================
# Name:         check_targets.py
# Description:  Monitors IT targets currently stored in TARGETS
#               Check results are stored and viewable in CHECK_RESULTS
#
# Input Files:  TARGETS Table
#               CHECKLIST table
#               .env
#
# Output:       Monitoring Entries saved to the Check_Results table
#               Log files to $LOG_DIR/check_results_$date.log
#
# Syntax:       check_targets.py -t target_type -v vendor -f frequency
#               -c check_type -s start_id -e end_id
#
# Calls:        targets.connect,  targets.get_info
#               inventory.exec_sql
#               checks.get_check
#
# Restrictions: Enter the correct python environment prior to running.
#               ex)  "source ~/<venv>/bin/activate"
#                           to enter the necessary virtual environment
# ============================================================================
#     """

import concurrent.futures # allows us to do multiple checks at once
import sys
import argparse # Allows us to interact with the o/s
from datetime import date
from time import sleep
from decouple import config  # Allows us to read .env
from inv_logging import start_logging
# ============================================================================
from inventory import Inventory
import os

def main():
    parallel_procs=50
    parser = argparse.ArgumentParser(description='Check targets.')
    parser.add_argument('-t', '--target_type', default='Database')
    parser.add_argument('-v', '--vendor', default='ALL')
    parser.add_argument('-f', '--frequency', default='HOURLY')
    parser.add_argument('-x', '--low_id', default='1')
    parser.add_argument('-y', '--high_id', default='999999')
    args = parser.parse_args()
    # Set Environment and Variables
    log_dir = config('LOG_DIR')
    log_name = "Check_Targets"
    log_file = log_dir + log_name + "_" + str(date.today()) + ".log"
    log_level = 'INFO'
    log_to_console = 'OFF'

    # Log to File
    target_logger = start_logging(log_level, log_file, log_name, log_to_console)

    target_logger.info(f"Running check_targets.py with "
                       f"TARGETTYPE={args.target_type} "
                       f"VENDOR={args.vendor} FREQUENCY={args.frequency}")

    inventory = Inventory(target_logger)
    rc = inventory.connect()
    if rc == 0:
        target_logger.error("Unable to connect to the Inventory Database. "
                            "Exiting.")
        sys.exit()

    # Get ALL the matching active targets from the inventory
    target_list = inventory.get_targets(args.target_type, args.vendor, args.low_id, args.high_id)
    target_logger.debug("# of Targets: %s", len(target_list))

    # Get ALL the checks to perform on these targets
    # Construct filter dictionary
    filter = {
        'AND': {
            'frequency': args.frequency,
            'check_type': args.target_type
        }
    }
    if args.vendor != 'ALL':
        filter['AND'].update({'vendor': args.vendor})

    checks_list = inventory.get_checks(filter)
    target_logger.info("# of Checks: %s", len(checks_list))
    target_logger.debug("All Checks: %s", [ str(check) for check in checks_list] )

    # Take all the targets and all the checks and submit them to "Do_Checks"
    with concurrent.futures.ThreadPoolExecutor(max_workers=parallel_procs) as executor:
        futures = [executor.submit(targ.do_checks, checks_list) for targ in target_list]

        # Before leaving see how they did and log the return codes.
        for future in concurrent.futures.as_completed(futures):
                try:
                    target_logger.info("Completed Checks: %s", future.result())
                except:
                    target_logger.error("Failed on %s", str(future))

    target_logger.info(f"Completed running check_targets.py with "
                       f"target_type={args.target_type} vendor={args.vendor} "
                       f"frequency={args.frequency} "
                       f"low_id={str(args.low_id)} high_id={str(args.high_id)}")
    target_logger.info("=========================================="
                       "==========================================")
    inventory.disconnect()
# END main program


if __name__ == "__main__":
    main()
