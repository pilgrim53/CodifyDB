import os           # Allows us to run os commands from within the script
import subprocess
import smtplib      # Allows us to send an email with the status
import sys, getopt  # Allows us to interact with the o/s
from datetime import datetime
from datetime import date
from decouple import config  # Allows us to read .env
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
GLOBAL_LOG_NAME = "DB_Patching"
GLOBAL_LOG_FILE = LOG_DIR + GLOBAL_LOG_NAME + "_" + str(date.today()) + ".log"
GLOBAL_LOG_LEVEL = 'DEBUG'
GLOBAL_LOG_TO_CONSOLE = 'NO'

# ============================================================================
# ============================================================================
# ---------------------------     MAIN PROGRAM     -------------------------------
# ============================================================================
# ============================================================================
def main(argv):
    # Set some default values
    conflicts_only = "FALSE"
    handler = "ssh"
    curr_ver = '12.2.0.1.28'
    OPatch_Repo = "/BellDBC/Bell-ora-staging/OPatch/"
    New_OPatch = "OPatch_12.2.0.1.28_for_DB_21.0.0.0.0.zip"
    #Patch_Repo = "/BellDBC/Bell-ora-staging/Database/Oracle-DB-19.0.0/RU/"
    #New_Patch = "RU_JAN_2022_RDBMS_OJVM_p33567270_190000_Linux-x86-64.zip"


    Patch_Repo = "/BellDBC/Bell-ora-staging/Database/Oracle-DB-12102/PSU/"
    New_Patch = "PSU_JAN_2022_RDBMS_OJVM_p33559997_121020_Linux-x86-64.zip"


    kb_required = 5621087  # Need space for zip and unzipped
    hostname = ''
    instance_name = ''

    # Get the parameters
    try:
        opts, args = getopt.getopt(argv,":H:d:ch")

    except getopt.GetoptError:
        print ('USAGE: python db_patch.py -H Hostname -d Database -c ')
        sys.exit(2)

    target_logger.debug('Command Options: %s  Arguments: %s ', opts, args)

    for opt, arg in opts:
        if opt == '-h':
            print ('USAGE: python db_patch.py -H Hostname -d Database -c ')
            sys.exit()

        elif opt == "-c" :
            conflicts_only = "TRUE"

        elif opt == "-H":
            hostname = arg

        elif opt =="-d":
            instance_name = arg

    target_logger.info("Running db_patch.py with HOSTNAME=%s INSTANCE=%s CONFLICTS_ONLY=%s ", hostname, instance_name, conflicts_only)

    if ( hostname == '' or instance_name == '' ) : 
        print ('USAGE: python db_patch.py -H Hostname -d Database -c ')
        return -1

    target_logger.info("Running db_patch.py with HOSTNAME=%s INSTANCE=%s CONFLICTS_ONLY=%s ", hostname, instance_name, conflicts_only)

    target_query = 'select hostname, instance_name, version, os, owner, home_dir from public.target a where a.hostname = \''
    target_query += hostname + '\' and instance_name = \'' + instance_name + '\';'

    # Get ALL the checks to perform on these targets
    RC, patch_target=inventory.exec_sql(target_query, 'ONE', target_logger)

    if RC <= 0 :
        target_logger.error("Could not find HOSTNAME=%s with INSTANCE=%s in inventory.", hostname, instance_name)
        return -1
     
    else : 
        target_logger.debug("Found patch target: %s" , patch_target)
        print("Found patch target: %s" , patch_target)

    ################################################
    # * * * *   Main Program of Patching   * * * * #
    ################################################

    hostname, instance_name, version, os, owner, home_dir = [str(value).strip() for value in patch_target]

    if ( "Linux" not in os ) or ( "x86_64" not in os ) :
        print("Current script is for Linux x86_64 patches only.")
        target_logger.error("Current script is for Linux x86_64 patches only.")
        return -1

    # if ( "19" not in version ) and ( "12.1" not in version ) :
        # # print("Current supported versions are 19C and 12.1 only.")
        # target_logger.error("Current supported versions are 19C and 12.1 only.")
        # return -1


    # ssh to the host to:
    #    1)  confirm access and Oracle_Home location
    rc, connection = targets.connect(hostname, instance_name, owner, handler, target_logger)
    print( 'Connection RC: ', rc , 'Home_Dir', home_dir )
    if rc != 1 :
        target_logger.error("Can not connect to host %s as owner %s", hostname, owner)
        return -1

    # What is the current OPatch version?    
    check = home_dir + '/OPatch/opatch version | head -n 1 | awk -F":" \'{print $2}\' '
    rc, OPatch_Version = targets.get_info(check, handler, connection, target_logger)
    if rc != 1 :
        target_logger.error("Failed to obtain current OPatch version")
        return -1
    
    # if the connection is good and it's not the current OPatch then proceed 
    print("Current OPatch version is: " , OPatch_Version) 
    if OPatch_Version != curr_ver :

        # Check if there is sufficient space in Oracle_Home
        check = 'df -kP ' +  home_dir + ' | awk \'{print $4}\' | tail -n 1 ; exit '
        rc2, home_free = targets.get_info(check, handler, connection, target_logger)
        print('Free space in Oracle_Home: ', home_free )

        if ( rc2 == 1 ) and ( int(home_free) > kb_required ) : 
            # Move the current OPatch directory
            command = 'mv ' + home_dir + '/OPatch '  + home_dir + '/OPatch.' + OPatch_Version
            
            rc, output = targets.get_info(command, handler, connection, target_logger)
            print('Command: ', command, 'RC: ', rc2)

            command = 'scp ' + OPatch_Repo + New_OPatch + ' ' + owner+'@'+hostname + ':' + home_dir 
            process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
            process.wait()
            print( process.returncode)

            # Now unzip it and overwrite existing files
            command = 'cd ' + home_dir + '; unzip -qo ' + New_OPatch
            rc, output = targets.get_info(command, handler, connection, target_logger)
            print('Output: ', output, 'RC: ', rc2)
          
            # Clean up
            command = 'rm ' + home_dir + '/' + New_OPatch
            rc, output = targets.get_info(command, handler, connection, target_logger)

        else:
            print('No space for new OPatch.  Please make room and restart.')
            return -1
    else:
        print('Skipping OPatch update.  Already at current version.')

    # Check space in Oracle_Home
    check = 'df -kP ' +  home_dir + ' | awk \'{print $4}\' | tail -n 1 ; exit '
    rc2, home_free = targets.get_info(check, handler, connection, target_logger)
    print('Free space in Oracle_Home: ', home_free )

    # What is the current OPatch version now?    
    check = home_dir + '/OPatch/opatch version | head -n 1 | awk -F":" \'{print $2}\' '
    rc, OPatch_Version = targets.get_info(check, handler, connection, target_logger)

    sw_dir = '/' + home_dir.split('/')[1] + '/software'
    print("Transferring patch to: ", sw_dir)

    if int(home_free) >  kb_required  : 
        command = 'scp ' + Patch_Repo + New_Patch + ' ' + owner+'@'+hostname + ':' + sw_dir 
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
        process.wait()
        rc1 = process.returncode

        if rc1 == 1 :
            # Now unzip it
            command = 'cd ' + sw_dir + '; unzip -qo ' + New_Patch
            rc2, output = targets.get_info(command, handler, connection, target_logger)

    else:
        print('No space for Patches.  Please make room and restart.')
        return -1

    target_logger.info("Completed db_patch.py with HOSTNAME=%s INSTANCE=%s CONFLICTS_ONLY=%s ", hostname, instance_name, conflicts_only)
    target_logger.info("====================================================================================")

# ============================================================================
# END main program
# ============================================================================

if __name__ == "__main__":
    target_logger=start_logging(GLOBAL_LOG_LEVEL, GLOBAL_LOG_FILE, GLOBAL_LOG_NAME, GLOBAL_LOG_TO_CONSOLE)    # Log to File
    main(sys.argv[1:])
