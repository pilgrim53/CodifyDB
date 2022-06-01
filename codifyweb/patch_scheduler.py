import os           # Allows us to run os commands from within the script
import subprocess
import smtplib      # Allows us to send an email with the status
import sys, getopt  # Allows us to interact with the o/s
from time import sleep  
from datetime import datetime
from datetime import date
from unittest.mock import patch
from decouple import config  # Allows us to read .env
from threading import TIMEOUT_MAX
from threading import Timer
# from dataclasses import dataclass   # Allows us to create a data class structure
# ============================================================================
CODIFYWEB_DIR = config('CODIFYWEB_DIR')
sys.path.append(CODIFYWEB_DIR)
from inv_logging import start_logging
import inventory
import targets

# ============================================================================

# ============================================================================
# Set  Environment and Global Variables
# ============================================================================
LOG_DIR = config('LOG_DIR')
GLOBAL_LOG_NAME = "Patch_Scheduler"
GLOBAL_LOG_FILE = LOG_DIR + GLOBAL_LOG_NAME + "_" + str(f"{datetime.now():%Y-%m-%d_%H%M%S}") + ".log"
GLOBAL_LOG_LEVEL = 'DEBUG'
GLOBAL_LOG_TO_CONSOLE = 'ON'



# ============================================================================
# Set our data model
# ============================================================================
# @dataclass
class PatchTarget:
    id:                 int = None
    hostname:           str = None
    instance_name:      str = None
    PRE_OPATCH:	        str = None
    PRE_SW_RELEASE:	str = None
    PRE_HOME_FREE:	int = None
    sched_date_time:	date= None
    POST_OPATCH:	str = None
    POST_SW_RELEASE:    str = None
    POST_HOME_FREE:	int = None
    DB_STOPPED:	        date= None
    DB_STARTED:	        date= None
    CONFLICTS:	        str = None
    DB_PATCH_NUMBER:    str = None
    SHARED_HOME:	str = None

# ============================================================================
# ============================================================================
# ---------------------------     MAIN PROGRAM     -------------------------------
# ============================================================================
# ============================================================================
def main(argv):
    # Set some default values
    rc = 0
    target_logger.info("Starting Oracle DB Patch Scheduler")

    target_query = """ select id, hostname, instance_name, check_complete, sched_date_time
     from dbc_team.patching 
    where SCHED_DATE_TIME > ( sysdate -1 )
     -- and SCHED_DATE_TIME < ( sysdate + 1 )
      and check_complete is null
      and pre_req_issues is null
   order by SCHED_DATE_TIME  """


    # Get ALL the checks to perform on these targets
    RC, patch_targets=inventory.exec_sql(target_query, 'ALL', target_logger)

    if RC <= 0 :
        target_logger.error("Could not get patching schedule")
        return -1

    else :
        target_logger.info("Patching Schedule retrieved")

    ################################################
    # * * * *   Main Program of Patching   * * * * #
    ################################################
    # target_logger.info("Number of targets:", str(len(patch_targets[0])))

    # PRE_OPATCH, PRE_SW_RELEASE , PRE_HOME_FREE, SCHED_DATE_TIME, POST_OPATCH, POST_SW_RELEASE, POST_HOME_FREE , 
    # DB_STOPPED, DB_STARTED, CONFLICTS, DB_PATCH_NUMBER, SHARED_HOME 

    for inventory_id, hostname, instance_name, check_complete, sched_date_time in patch_targets:
        target_logger.info("Targets: %s  Scheduled date: %s ", str(inventory_id), str(sched_date_time.strftime("%m/%d/%Y %H:%M:%S")))

        if sched_date_time == '' :
            target_logger.error("Unknown Scheduled Date")
            return -1

        if ( check_complete  and check_complete < datetime.now() ) :
            target_logger.info("Pre-Checks Completed Successfully for %s at %s", \
                               instance_name, str(check_complete.strftime("%m/%d/%Y %H:%M:%S")))

        else: 
            target_logger.info("Performing Prep on Target : %s ", str(inventory_id))
            command = './db_patch.py -H ' + str(hostname) + ' -d ' + str(instance_name) + ' -s' 
            target_logger.info("Command: %s ", str(command) )
            process = subprocess.Popen(command, shell=True, stdout=None)
            waiter = process.wait()
            rc = process.returncode
            target_logger.info('Patching result: ' +  str(rc))

            if rc != 0 :
                target_logger.error("Patch Scheduling had errors.  Please investigate on %s", str(hostname))
                add_check_date = 'update dbc_team.patching set pre_req_issues=\'' + str(rc) + '\', check_complete=sysdate \
                                     where id = ' + str(inventory_id)

            else :
                target_logger.info("Patch Scheduling  completed successfully for %s : %s", str(hostname), str(instance_name))
                add_check_date = 'update dbc_team.patching set pre_req_issues=\'NONE\', check_complete=sysdate \
                                     where id = ' + str(inventory_id)

            RC, test=inventory.exec_sql(add_check_date, 'EXEC', target_logger)


    target_logger.info("Patch Scheduling Completed at %s ", str(datetime.now()))
    target_logger.info("====================================================================================")

    return rc

# ============================================================================
# END main program
# ============================================================================

if __name__ == "__main__":
    target_logger=start_logging(GLOBAL_LOG_LEVEL, GLOBAL_LOG_FILE, GLOBAL_LOG_NAME, GLOBAL_LOG_TO_CONSOLE)    # Log to File
    main(sys.argv[1:])
