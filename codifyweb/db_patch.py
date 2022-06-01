#!/home/orac4i/Inventory/bin/python

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
GLOBAL_LOG_FILE = LOG_DIR + GLOBAL_LOG_NAME + "_" + str(f"{datetime.now():%Y-%m-%d_%H:%M:%S}") + ".log"
GLOBAL_LOG_LEVEL = 'INFO'
GLOBAL_LOG_TO_CONSOLE = 'ON'

# ============================================================================
# ============================================================================
# ---------------------------     MAIN PROGRAM     -------------------------------
# ============================================================================
# ============================================================================
def main(argv):
    # Set some default values
    scp_copy = "FALSE"
    conflicts_only = "FALSE"
    handler = "ssh"
    curr_ver = '12.2.0.1.30'
    OPatch_Repo = "/BellDBC/Bell-ora-staging/OPatch/"
    New_OPatch = "OPatch_12.2.0.1.30_p6880880_122010_Linux-x86-64.zip"
    kb_required = 5221087  # Need space for zip and unzipped
    hostname = ''
    instance_name = ''
    APPLY = ""
    

    # ========================================================================
    # PSU Dictionary / Library
    patch_index={'':1, '12.2.0.1.0':3, '12.1.0.2.0':2, '19.0.0.0.0':4}
    patch_repos = [{}] * 5
    patch_repos[1]= {}
    patch_repos[2]= {}
    patch_repos[3]= {}
    patch_repos[4]= {}

    # Updated May 2022
    patch_repos[4] = {
        "pd" : "/BellDBC/Bell-ora-staging/Database/Oracle-DB-19.0.0/RU/", 
        "pf" : "RU_APR_2022_RDBMS_OJVM_p33859194_190000_Linux-x86-64.zip",
        "pn" : "33859194" }

    patch_repos[3] = {
        "pd" : "/BellDBC/Bell-ora-staging/Database/Oracle-DB-12201/RU/",
        "pf" : "RU_JAN_2022_RDBMS_OJVM_p33559893_122010_Linux-x86-64.zip",
        "pn" : "33559893" }

    patch_repos[2] = {
        "pd" : "/BellDBC/Bell-ora-staging/Database/Oracle-DB-12102/PSU/",
        "pf" : "PSU_APR_2022_RDBMS_OJVM_p33859494_121020_Linux-x86-64.zip", 
        "pn" : "33859494" }

    patch_repos[1] = {
        "pd" : "/BellDBC/Bell-ora-staging/Database/Oracle-DB-12102/PSU/",
        "pf" : "PSU_APR_2022_RDBMS_OJVM_p33859494_121020_Linux-x86-64.zip",
        "pn" : "33859494" }

    # Get the parameters from command line
    try:
        opts, args = getopt.getopt(argv,":H:d:Ash")

    except getopt.GetoptError:
        target_logger.error('USAGE: python db_patch.py -H Hostname -d Database -A (APPLY) -s (scp the patch)')
        sys.exit(2)

    target_logger.debug('Command Options: %s  Arguments: %s ', opts, args)

    for opt, arg in opts:
        if opt == '-h':
            target_logger.info('USAGE: python db_patch.py -H Hostname -d Database -A -s ')
            sys.exit()

        elif opt == "-A" :
            APPLY = "APPLY"

        elif opt == "-H":
            hostname = arg.upper()

        elif opt =="-d":
            instance_name = arg.upper()

        elif opt =="-s":
            scp_copy = "TRUE"

    target_logger.info("Running db_patch.py with HOSTNAME=%s INSTANCE=%s APPLY=%s ", hostname, instance_name, APPLY)

    if ( hostname == '' or instance_name == '' ) :
        target_logger.error('USAGE: python db_patch.py -H Hostname -d Database -c ')
        #return -1
        sys.exit(-1)

    target_query = 'select hostname, instance_name, version, os, owner, home_dir from targets a where a.hostname = \''
    target_query += hostname + '\' and instance_name = \'' + instance_name + '\''

    # Get ALL the checks to perform on these targets
    RC, patch_target=inventory.exec_sql(target_query, 'ONE', target_logger)

    if RC <= 0 :
        target_logger.error("Could not find HOSTNAME=%s with INSTANCE=%s in inventory.", hostname, instance_name)
        # return -1
        sys.exit(-1)

    else :
        target_logger.info("Found patch target: %s" , patch_target)

    ################################################
    # * * * *   Main Program of Patching   * * * * #
    ################################################

    hostname, instance_name, version, os, owner, home_dir = [str(value).strip() for value in patch_target]
    #patch_dir, patch_file, patch_num = {}.fromkeys(['pd', 'pf', 'pn'], patch_repos[patch_index[version]])

    if version == '' :
        if APPLY == 'APPLY' :
            target_logger.error("Unknown version. Update target info and re-run")
            return -1
        else : 
            target_logger.info("Unknown version. doing checks ")
            version = '12.2.0.1.0'

    patch_dir = patch_repos[patch_index[version]].get('pd','None')
    patch_file = patch_repos[patch_index[version]].get('pf','None')
    patch_num = patch_repos[patch_index[version]].get('pn','None')

    target_logger.debug("Version: %s  Index: %s Number: %s ", str(version), str(patch_index[version]), str(patch_repos[patch_index[version]]))

    if ( "Linux" not in os ) or ( "x86_64" not in os ) :
        target_logger.error("Current script is for Linux x86_64 patches only.")
        return -1

    if ( "19" not in version ) and ( "12" not in version ) :
        target_logger.error("Current supported versions are 19C and 12 only.")
        return -1

    # ssh to the host to:
    #    1)  confirm access and set timeout to MAX
    rc, connection = targets.connect(hostname, instance_name, owner, handler, target_logger, 60) 
    target_logger.debug( 'Connection RC: %s Home: %s', rc ,  home_dir )
    if rc != 1 :
        target_logger.error("Can not connect to host %s as owner %s", hostname, owner)
        return -1

    # What is the current OPatch version?
    check = home_dir + '/OPatch/opatch version | head -n 1 | awk -F":" \'{print $2}\' '
    rc, OPatch_Version = targets.get_info(check, handler, connection, target_logger, 60)
    if rc != 1 :
        target_logger.error("Failed to obtain current OPatch version")
        return -1
    connection.close()

    # if the connection is good and it's not the current OPatch then proceed
    target_logger.info("Current OPatch version is: %s" , str(OPatch_Version))

    if str(OPatch_Version) != curr_ver :
        #    2)  Connect confirm OPatch
        rc, connection = targets.connect(hostname, instance_name, owner, handler, target_logger, 60) 

        # Check if there is sufficient space in Oracle_Home
        check = 'df -kP ' +  home_dir + ' | awk \'{print $4}\' | tail -n 1 ; exit '
        rc2, home_free = targets.get_info(check, handler, connection, target_logger, 60)
        target_logger.info('Free space in Oracle_Home: %s', home_free )
        connection.close()

        if ( rc2 == 1 ) and ( int(home_free) > kb_required ) :
            # Move the current OPatch directory
            command = 'mv ' + home_dir + '/OPatch '  + home_dir + '/OPatch.' + OPatch_Version

            rc, connection = targets.connect(hostname, instance_name, owner, handler, target_logger, 60) 

            rc, output = targets.get_info(command, handler, connection, target_logger, 60)
            target_logger.info('Command: %s RC: %s', command, rc2)

            command = 'scp ' + OPatch_Repo + New_OPatch + ' ' + owner+'@'+hostname + ':' + home_dir
            process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
            rc = process.wait()
            target_logger.debug('scp result: %s ', str(rc))

            connection.close()

            # Now unzip it and overwrite existing files
            rc, connection = targets.connect(hostname, instance_name, owner, handler, target_logger, 150) 
            command = 'cd ' + home_dir + '; unzip -qo ' + New_OPatch
            rc, output = targets.get_info(command, handler, connection, target_logger, 150)
            target_logger.info('Output: %s RC: %s', output, rc2)

            # Clean up OPatch zip file
            command = 'rm ' + home_dir + '/' + New_OPatch
            rc, output = targets.get_info(command, handler, connection, target_logger)
            connection.close()

        else:
            target_logger.error('No space for new OPatch.  Please make room and restart.')
            sys.exit(-1)
    else:
        target_logger.info('Skipping OPatch update.  Already at current version.')

    rc, connection = targets.connect(hostname, instance_name, owner, handler, target_logger, 120) 

    # Check space in Oracle_Home
    check = 'df -kP ' +  home_dir + ' | awk \'{print $4}\' | tail -n 1 ; exit '
    rc2, home_free = targets.get_info(check, handler, connection, target_logger)
    target_logger.info('Free space in Oracle_Home: %s', home_free )
    connection.close()

    # What is the current OPatch version now?
    rc, connection = targets.connect(hostname, instance_name, owner, handler, target_logger, 120) 
    check = home_dir + '/OPatch/opatch version | head -n 1 | awk -F":" \'{print $2}\' '
    rc, OPatch_Version = targets.get_info(check, handler, connection, target_logger)
    sw_dir = '/' + home_dir.split('/')[1] + '/software'
    connection.close()

    if scp_copy == "TRUE" :
        if int(home_free) >  kb_required  :
            rc, connection = targets.connect(hostname, instance_name, owner, handler, target_logger, 120) 

            # Mke sure the /XXX01/software directory exists
            command = 'mkdir -p ' + sw_dir
            rc, output = targets.get_info(command, handler, connection, target_logger)
            target_logger.info("Transferring patch to: %s", sw_dir)
            command = 'scp ' + patch_dir + patch_file + ' ' + owner+'@'+hostname + ':' + sw_dir
            process = subprocess.Popen(command, shell=True, stdout=None)
            rc1 = process.wait()
            target_logger.info('scp2 result: ' +  str(rc1))
            connection.close()

            # unzip the patch and remove the zip file
            rc, connection = targets.connect(hostname, instance_name, owner, handler, target_logger, 120) 
            command = 'cd ' + sw_dir + '; nohup unzip -o ' + patch_file 
            rc2, output = targets.get_info(command, handler, connection, target_logger, 120)
            if rc2 != 1 :
                    target_logger.error("Failed to unzip patch on %s : %s ", hostname, sw_dir )
            command = 'cd ' + sw_dir  + ' ; rm -f ' + patch_file 
            rc3, output = targets.get_info(command, handler, connection, target_logger, 120)
            if rc3 != 1 :
                    target_logger.error("Failed to remove patch zip file on %s : %s ", hostname, sw_dir )
            connection.close()

        else:
            target_logger.error("Only %s kb available. Make room for patches and restart.", home_free)
            sys.exit(-1)

    # Tansfer latest OraDBPatch.ksh to server
    target_logger.info("Transferring OraDBPatch.ksh to: %s ", home_dir + '/../../DBTools' )
    command = 'scp /BellDBC/Bell-ora-staging/DBTools/OraDBPatch.ksh ' + owner+'@'+hostname + ':' + home_dir + '/../../DBTools/'
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
    rc1 = process.wait()
    target_logger.info("scp OraDBPatch.ksh return code: %s", rc1)

    # Tansfer latest OraDBPatch.ksh to server
    rc, connection = targets.connect(hostname, instance_name, owner, handler, target_logger, 1800) 
    check = home_dir + '/../../DBTools/OraDBPatch.ksh ' +instance_name+ ' ' +sw_dir+'/' +patch_num+ ' ' +APPLY
    rc, patch_apply = targets.get_info(check, handler, connection, target_logger, 1800)
    connection.close()

    if rc != 1 :
        target_logger.error("OraDBPatch.ksh had errors.  Please investigate on %s", hostname)
        sys.exit(rc)
    else :
        target_logger.info("OraDBPatch.ksh completed successfully for %s : %s", hostname, instance_name)

    target_logger.info("Completed db_patch.py with HOSTNAME=%s INSTANCE=%s APPLY=%s ", hostname, instance_name, APPLY)
    target_logger.info("====================================================================================")

    return rc

# ============================================================================
# END main program
# ============================================================================

if __name__ == "__main__":
    target_logger=start_logging(GLOBAL_LOG_LEVEL, GLOBAL_LOG_FILE, GLOBAL_LOG_NAME, GLOBAL_LOG_TO_CONSOLE)    # Log to File
    main(sys.argv[1:])
