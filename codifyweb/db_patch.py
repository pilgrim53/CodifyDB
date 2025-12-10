"""
# ============================================================================
# Name:         db_patch.py
# Description:  Apply latest Quarterly Release Update from Oracle
#
# Input Files:  PATCHING and PATCHES Table
#               .env
#
# Output:       Results saved to the PATCHING table
#               Log files to $LOG_DIR/DB_Patching_$date.log
#
# Syntax:       python db_patch.py -H <Hostname> -d <CDB> [-A (APPLY) -R id
                     -O id ] [-s (scp the patch)]
#
# Calls:        targets.connect, targets.get_attribute, targets.get_info
#               inventory.get_id, inventory.exec_sql
#               checks.get_checks, do_checks
#
# Restrictions: Enter the correct python environment prior to running.
#               ex)  "source ~/<venv>/bin/activate"
#                           to enter the necessary virtual environment
# ============================================================================
#     """
import subprocess   # Allows us to run os commands from within the script
import sys
import argparse  # Allows us to interact with the o/s
import re
import paramiko  # Allows us to ssh to caddla-978 to run ansible jobs
from time import sleep
from shutil import copyfile
from pathlib import Path
from datetime import datetime
from decouple import config  # Allows us to read .env
from threading import TIMEOUT_MAX
from password_manager import PasswordManager
# ============================================================================
from inv_logging import start_logging
from inventory import Inventory
from target import Target
# ============================================================================
handler = "ssh"

CREDENTIALS = PasswordManager()
PKEY = CREDENTIALS.get('PKEY')

def update_opatch(inventory, target, logger, version, opatch_ver, release_date):
    logger.debug(f"Arrived at update_opatch with {target} {version} {opatch_ver}")
    status = 1
    handler = 'ssh'
    # Check if OPatch/opatch version is already at the latest version
    opatch_query1 = (f" select location from dbc_team.patches where patch_num = '6880880' and release_date='{release_date}' ")
    opatch_query2 = (f" select patch_file from dbc_team.patches where patch_num = '6880880' and release_date='{release_date}' ")

    if version == '11.2.0.4' : 
        opatch_query2 += " and patch_version = '11.2.0.4.0'"
    else :
        opatch_query2 += " and patch_version != '11.2.0.4.0'"

    rc, opatch_repo = inventory.exec_sql(opatch_query1, 'ONE')
    rc, new_opatch = inventory.exec_sql(opatch_query2, 'ONE')

    if new_opatch is None:
        status = 0
        logger.info("OPatch not found.")
    else:
        if version == '11.2.0.4' : 
            opatch = re.search(r"11.2.0.3.\d\d",str(new_opatch))
            curr_ver = opatch.group() if opatch else '11.2.0.4'
        else : 
            opatch = re.search(r"12.2.0.1.\d\d",str(new_opatch))
            curr_ver = opatch.group() if opatch else '12.2.0.1'

        opatch_repo = opatch_repo[0]
        new_opatch = new_opatch[0]

        logger.info(f"Using OPatch version {curr_ver} from {opatch_repo}{new_opatch}")

        if opatch_ver == '' :
            opatch_ver = 'unknown'
        
        if str(opatch_ver) != curr_ver:
            if target.vendor =='ORACLE' :
                rc = target.connect(handler, inventory, 60)
                # Move the current OPatch directory
                logger.info('OPatch %s is not current. Updating it first.', str(opatch_ver))
                command = (f'mv {target.home_dir.strip()}/OPatch {target.home_dir}/OPatch.{opatch_ver}')
                rc2, output = target.get_info(command, handler, 120)
                logger.info('Command: %s RC: %s', command, rc2)

                # scp in the new zip
                command = (f'scp -i {PKEY} -o "StrictHostKeyChecking no" {opatch_repo}{new_opatch} {target.owner}@{target.hostname}:{target.home_dir}')
                logger.debug('scp command: %s ', str(command))
                process = subprocess.Popen(command, shell=True,stdout=subprocess.PIPE)
                rc = process.wait()
                logger.debug('scp result: %s ', str(rc))

                # Now unzip it and overwrite existing files
                command = 'cd ' + target.home_dir + '; unzip -qo ' + new_opatch
                rc2, output = target.get_info(command, handler, 300)
                logger.info('Output: %s RC: %s', output, rc2)

                # Clean up OPatch zip file
                command = 'rm ' + target.home_dir + '/' + new_opatch
                rc, output = target.get_info(command, handler)

                # What is the current OPatch version now?
                # This command does NOT work with formatted string due to awk use of { }
                check = (target.home_dir + '/OPatch/opatch version | head -n 1 | awk -F":" \'{print $2}\' ')
                rc, opatch_ver = target.get_info(check, handler)
                inventory.add_result(target.inventory_id, opatch_ver,'opatch')
                if str(opatch_ver) != curr_ver:
                    status=0
                target.disconnect()

            elif target.vendor == 'ASM':
                rc = target.connect(handler, inventory, 30)
                sw_dir = '/' + target.home_dir.split('/')[1] + '/software'
                command = 'mkdir -p ' + sw_dir
                rc, output = target.get_info(command, handler, 30)
                target.disconnect()
                logger.info(f'We can not write to ASM Grid Home. Please replace OPatch manually from /xxx01/software.')
                logger.info(f'Transferring patch to: {sw_dir}' )
                command = (f'scp -i {PKEY} -o "StrictHostKeyChecking no" {opatch_repo}{new_opatch} {target.owner}@{target.hostname}:{sw_dir}')
                process = subprocess.Popen(command, shell=True, stdout=None)
                rc1 = process.wait()
                logger.info('OPatch scp result: ' + str(rc1))
        else:
            logger.info(f'OPatch is already at current version: {str(opatch_ver)} ')
    
    return status

def customize_oradbpatch(inventory, target, logger, oneoffs, rollbacks, OraDBPatch, sw_dir):
    rc_patch = 1
    try:
        sourcefile = Path(OraDBPatch).resolve()
    except Exception as exc:
        logger.error(f"Error accessing file: {exc}")

    custom_file = '/tmp/OraDBPatch_' + target.instance_name + '.ksh'
    # The line to insert rollbacks after.
    insert_rollback_line = "# CUSTOM CONFLICT "
    # The line to insert oneoffs after.
    insert_oneoff_line = "# CUSTOM MERGE "

    LINE = ''
    with sourcefile.open(mode="r") as source:
        with open(custom_file, 'w') as destination:
            while insert_rollback_line not in LINE:
                LINE = source.readline()
                destination.write(LINE)

            if rollbacks > '':
                # 1) Insert the Rollback Line(s)
                insert_data = ("        $ORACLE_HOME/OPatch/opatch rollback -id ")
                patch_ids = rollbacks.split(",")
                for patch_id in patch_ids:
                    destination.write('        log_info -t \"Rollback -id ' + patch_id + '\"\n')
                    destination.write(str(insert_data) + str(patch_id) + ' -silent \n')

            destination.write(LINE)  # the line read above

            # Now find the Merge / Oneoffs location
            while insert_oneoff_line not in LINE:
                LINE = source.readline()
                destination.write(LINE)

            if oneoffs > '':
                # 2) Insert the OneOff Apply Line(s)
                insert_data = ("        $ORACLE_HOME/OPatch/opatch apply -silent ")
                patch_ids = oneoffs.split(",")
                for patch_id in patch_ids:
                    destination.write('        log_info -t \"apply oneoff ' + patch_id + '\"\n')
                    destination.write(str(insert_data)+str(sw_dir) + '/' + str(patch_id)+'\n')

            destination.write(LINE)  # the line read above

            # Write the rest in chunks.
            while True:
                data = source.read(1024)
                if not data:
                    break
                destination.write(data)
        # Finish writing data.
        # destination.flush()
    OraDBPatch = custom_file

    if oneoffs > '':
        sw_dir = '/' + target.home_dir.split('/')[1] + '/software' 
        for patch_id in patch_ids:
            patch_query = (
                f"select patch_id, patch_version, location, "
                f"patch_file, patch_num, is_current\n"
                f"from dbc_team.patches where is_current='Y'\n"
                f"and patch_version = '{target.version}'"
                f" and patch_num = '{patch_id}'")

            # Get the current patch for the target database
            RC, patches = inventory.exec_sql(patch_query, 'ONE')

            try:
                id, version, patch_dir, patch_file, oneoff_patch_num,\
                    current = [str(value).strip() for value in patches]
            except NameError:
                logger.error("NameError: Could not find OneOff Patch:")
                rc_patch += 1
            except TypeError:
                logger.error("TypeError: Could not find OneOff Patch:")
                rc_patch += 1
            else:
                logger.info("Transferring oneoff patches to: %s", sw_dir)
                command = (f'scp -i {PKEY} {patch_dir}{patch_file} {target.owner}@{target.hostname}:{sw_dir}')
                process = subprocess.Popen(command, shell=True, stdout=None)
                rc = process.wait()
                logger.info(f'scp result: {str(rc)}')

                # unzip the patch and remove the zip file
                rc = target.connect(handler, inventory, 300)
                command = 'cd ' + sw_dir + '; unzip -o ' + patch_file
                rc2, output = target.get_info(command, handler, 300)
                rc_patch += rc2
                if rc2 != 1:
                    logger.error(f'Failed to unzip patch in {target.hostname} : {sw_dir} ')
                command = 'cd ' + sw_dir + ' ; rm -f ' + patch_file
                rc, output = target.get_info(command, handler, 300)
                if rc != 1:
                    logger.error(f'Failed to remove patch zip in {target.hostname} : {sw_dir} ')

                target.disconnect()

    return rc_patch, OraDBPatch

def update_patching_tbl(inventory, target, logger, ticket, step, issues, patch_date = str(f"{datetime.now():%Y-%m-%d_%H-%M-%S}")):

    logger.debug(f"Update Patching Table")
    logger.debug(f"Update Patch Date: { patch_date }")

    if step == 'PRE-CHECK':
        update_sql = (f'update dbc_team.patching set CHECK_DATE=sysdate, PRE_REQ_ISSUES = {str(issues)} ')
        logger.debug(f"SQL: {update_sql}")
    elif step == 'APPLY':
        update_sql = (f"update dbc_team.patching set PATCH_DATE=to_date('{patch_date}','YYYY-MM-DD_HH24-MI-SS'), PATCH_ISSUES={issues} ")
        logger.debug(f"SQL: {update_sql}")

    update_sql += (f"where id = {str(target.inventory_id)} and ticket = '{str(ticket)}'")

    logger.debug(f"SQL: {update_sql}")

    rc, rc1 = inventory.exec_sql(update_sql, 'EXEC')
    return rc

# ============================================================================
# ---------------------------     MAIN PROGRAM     ---------------------------
# ============================================================================
# ============================================================================

def patch(hostname, instance_name, rollbacks, oneoffs, APPLY, release_date, scp_copy=False, ticket=''):
    
    # Set Environment variables and constants
    log_dir = config('LOG_DIR')
    log_name = (f"db_patch_{hostname}_{instance_name}_{datetime.now():%Y-%m-%d_%H-%M-%S}")
    log_level = 'DEBUG'
    log_to_console = 'ON'
    log_file = (f"{log_dir}{log_name}.log")
    # Set some default values
    patch_rc=1
    OraDBPatch = '/BellDBC/Bell-ora-staging/DBTools/OraDBPatch.ksh'
    # ========================================================================

    # Log to File
    logger = start_logging(log_level, log_file, log_name, log_to_console)
    inventory = Inventory(logger)

    if (hostname == '' or instance_name == ''):
            logger.error('USAGE: python db_patch.py -H <Hostname> '
                         '-d <CDB> [-A (APPLY) -R id -O id ] '
                         '[-s (scp the patch)]')
            RC = inventory.disconnect()
            return -1
    
    rc = inventory.connect()
    if inventory.patch_running(hostname, instance_name) :
        logger.warning("This patch is already running!!!")
        return 200

    logger.info(f"Running db_patch.py with HOSTNAME={hostname} "
                f"INSTANCE={instance_name} APPLY={APPLY} "
                f"Rollback={rollbacks} OneOffs={oneoffs}")

    inventory_id = inventory.get_id(hostname, instance_name)
    if inventory_id == 0:
        logger.error(f"Could not find HOST: {hostname} with INSTANCE: {instance_name} in inventory.")
        RC = inventory.disconnect()
        return -1
    
    logger.debug(f"Found patch target ID: {inventory_id}" )
    RC1 = inventory.patch_progress_update(hostname, instance_name, 'Y')

    ################################################
    # * * * *   Main Program of Patching   * * * * #
    ################################################
    # Get the details on the patching target
    targets=inventory.get_targets('Database','ALL',inventory_id, inventory_id+1)
    for target in targets :
        logger.debug("Found target: %s ", str(target) )

    if '2019' in target.version:
        target.version='2019'
    elif '2017' in target.version:
        target.version='2017'
    elif '2016' in target.version:
        target.version='2016'

    # Get the latest patch level in the case one was not provided.
    if release_date is None:
        release_date_query = (f"select max(release_date) from dbc_team.patches where combo='Y' and patch_version='{target.version}' ")
        rc, release_date = inventory.exec_sql(release_date_query, 'ONE')
        if release_date:
            release_date = release_date[0]
            
    if target.vendor == 'ORACLE' or target.vendor =='ASM':
        kb_required = 8496010  # Need space for zip AND unzipped
        # Find directory like /xxx01/software for uploading patches
        sw_dir = '/' + target.home_dir.split('/')[1] + '/software'
        command = 'mkdir -p ' + sw_dir
        rc = target.connect(handler, inventory, 30)
        rc, output = target.get_info(command, handler, 30)
        target.disconnect()

        # PSU Dictionary / Library
        patch_query = ("select patch_id, patch_version, location, patch_file, "
                        "patch_num, release_date, is_current, combo, os "
                        f"from dbc_team.patches where combo='Y' and "
                        f"release_date='{release_date}' "
                        f" and patch_version = '{target.version}' ")

        # Get the current patch for the target database
        RC, combo_patch = inventory.exec_sql(patch_query, 'ONE')
        if RC == 0 :
            logger.error("Unable to find Security Update patch for this database.")
            RC1 = inventory.patch_progress_update(target.hostname, target.instance_name, 'N')
            RC = inventory.disconnect()
            return -1

        try:
            id, version, patch_dir, patch_file, patch_num, release_date, \
                current, combo, os = [str(value).strip() for value in combo_patch]
        except NameError:
            logger.error("Unable to find Security Update patch for this database.")
            RC1 = inventory.patch_progress_update(target.hostname, target.instance_name, 'N')
            RC = inventory.disconnect()
            return -1

    if APPLY == '':
        if target.vendor == 'MSSQL' :
            kb_required = 2048000 # SQL CU 

        # Get ALL the pre-checks to perform on these targets
        check_filter = { 'OR': { 'result_column': ['opatch', 'sw_release', 'home_free', 'started'] } }

        logger.debug(f"Get Pre-checks: {check_filter}")
        all_checks = inventory.get_checks(check_filter)
        logger.info("Pre-Checks: %s", str(all_checks))

        # Doing checks saves the results in the CHECK_RESULTS table.
        target.do_checks(all_checks)
        logger.debug("Number of checks performed: %s", len(all_checks))

        # Get the results of the checks from CHECK_RESULTS.
        opatch_ver = inventory.get_result(inventory_id, 'opatch')
        sw_release = inventory.get_result(inventory_id, 'sw_release')
        home_free = inventory.get_result(inventory_id, 'home_free')
        started = inventory.get_result(inventory_id, 'started')

        logger.info(f"checking if current patch level {sw_release} has {release_date}")
        
        if sw_release and (release_date in sw_release):
            last_patch_sql = (f"select to_char(min(check_date),'YYYY-MM-DD_HH24-MI-SS') from check_results where inventory_id={inventory_id} and check_column='sw_release' and check_result like '%{sw_release}%'")
            logger.debug(f"sql: {last_patch_sql}")
            rc, last_patch_date = inventory.exec_sql(last_patch_sql,'ONE')
            last_patch_date = last_patch_date[0]
            logger.info(f"It looks like this database already has this patch set! Last Patch date was { last_patch_date }. Closing as Successful.")

            logger.debug(f" {inventory}, {target}, {ticket}, 'APPLY' 0, {last_patch_date} ")

            rc = update_patching_tbl(inventory, target, logger, ticket, 'APPLY', 0, last_patch_date )
        else:
            if sw_release == '':
                logger.info('Current SW Release is unknown.  Proceeding anyways.')
            else:
                logger.info('SW Release on target is not current.  Proceeding.')
                            
            if home_free == '' : 
                home_free = 0
                logger.error('Unable to detect free space in Oracle_Base.')

            if int(home_free) < kb_required:
                logger.error(f'Insufficient space in Home_Dir {home_free}.')
                logger.error(f'Please free {kb_required} KB and restart.' )
                RC1 = inventory.patch_progress_update(target.hostname, target.instance_name,'N')
                patch_rc=500

            elif target.vendor == 'ORACLE' or target.vendor == 'ASM':
                # Does OPatch need updating first?
                rc=update_opatch(inventory, target, logger, version, opatch_ver, release_date)

                logger.info("Transferring patch to: %s", sw_dir)
                command = (f'scp  -i {PKEY} -o "StrictHostKeyChecking no" {patch_dir}{patch_file} {target.owner}@{target.hostname}:{sw_dir}')
                process = subprocess.Popen(command, shell=True, stdout=None)
                rc1 = process.wait()
                logger.info('scp2 result: ' + str(rc1))

                # unzip the patch and remove the zip file
                rc = target.connect(handler, inventory, 300)
                command = 'cd ' + sw_dir + '; unzip -o ' + patch_file + ' ; rm -f ' + patch_file
                rc2, output = target.get_info(command, handler, 300)
                if rc2 != 1:
                    logger.error(f'Errors deploying patch zip to {target.hostname}:{sw_dir} ')
                target.disconnect()

                # Put latest DBTools and custom OraDBPatch.ksh on Target Server
                if target.vendor == 'ASM' :
                    command = (f'scp -q -i {PKEY} -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null /BellDBC/Bell-ora-staging/DBTools/*.ksh {target.owner}@{target.hostname}:{target.home_dir}/../../../DBTools/')
                else:
                    command = (f'scp -q -i {PKEY} -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null /BellDBC/Bell-ora-staging/DBTools/*.ksh {target.owner}@{target.hostname}:{target.home_dir}/../../DBTools/')
                process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
                rc = process.wait()
                logger.info(f"scp DBTools return code: {rc}")

                if rc :  # If UNIX process returned non-zero Return Code
                    logger.error(f"Shell script transfer failed. ")
                    patch_rc = 100
                else:
                    # Run OraDBPatch.ksh on Target Server for conflict check only
                    rc = target.connect(handler, inventory, 1800)
                    check = (f"ksh {target.home_dir}/../../DBTools/OraDBPatch.ksh {target.instance_name} {sw_dir}/{patch_num}")
                    patch_rc, patch_apply = target.get_info(check, handler, 1800)
                    target.disconnect()
                    logger.debug("OraDBPatch.ksh returned: %s",  patch_rc)

        logger.debug("Saving pre-check result data.")
        rc = update_patching_tbl(inventory, target, logger, ticket, 'PRE-CHECK', patch_rc-1)

    elif APPLY == 'SKIP':
        logger.debug('Pre-Checks completed but it is not time to apply')
        patch_rc=1

    elif APPLY == 'APPLY':
        logger.debug('Pre-Checks completed and it is time to do Patching')
        if target.vendor == 'ORACLE':
            if (rollbacks > '') or (oneoffs > ''):
                # Customize and then transfer latest OraDBPatch.ksh to server
                rc, OraDBPatch = customize_oradbpatch(inventory, target, logger, oneoffs, rollbacks, OraDBPatch, sw_dir)

            # Run OraDBPatch.ksh on Target Server
            command = (f'scp  -i {PKEY} {OraDBPatch} {target.owner}@{target.hostname}:{target.home_dir}/../../DBTools/OraDBPatch.ksh')
            process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
            rc = process.wait()
            logger.info(f"scp OraDBPatch.ksh return code: {rc}")

            rc = target.connect(handler, inventory, 6600)
            check = (f"ksh {target.home_dir}/../../DBTools/OraDBPatch.ksh {target.instance_name} {sw_dir}/{patch_num} {APPLY}")
            patch_rc, patch_apply = target.get_info(check, handler, 6600)
            target.disconnect()
            logger.debug("OraDBPatch.ksh returned: %s",  patch_rc)

        elif target.vendor == 'ASM':
            logger.info(f"OraDBPatch.ksh is not able to apply grid patch on ASM Instances.")

        elif target.vendor == 'MSSQL':
            patch_rc=1
            rc = target.connect('rsh_978', inventory, 1800)
            if int(rc) > 0 :
                check = f'/bin/sudo /bin/sshpass -f /etc/ansible/windows_playbooks/sqlpatching/passtemp.txt /bin/ansible-playbook ' \
                        f' -u "BELL\\fidbelldbc" -k /etc/ansible/windows_playbooks/sqlpatching/sql_patching{target.version}.yaml ' \
                        f' -i /etc/ansible/windows_playbooks/sqlpatching/all_sql_hosts.txt --limit {target.hostname.lower()} --extra-vars "ansible_connection=ssh ansible_shell_type=powershell ansible_become=false" '

                patch_rc, pb_output = target.get_info(check, 'rsh_978', 1800)
                logger.debug(f'RC from ansible playbook is {patch_rc}')
                if pb_output:
                    logger.debug('Output from ansible playbook is: %s', str(pb_output))
            target.disconnect()

        # Get ALL the checks to perform on these targets
        # Doing checks saves the results in the CHECK_RESULTS table.
        check_filter = { 'OR': { 'result_column': ['opatch', 'sw_release', 'home_free', 'started']  }  }
        logger.debug(f"Perform these checks: {check_filter}")
        all_checks = inventory.get_checks(check_filter)
        target.do_checks(all_checks)
        logger.debug("Number of checks performed: %s", len(all_checks))

        # Get the results of the checks from CHECK_RESULTS table into variables we can use here.
        opatch_ver = inventory.get_result(inventory_id, 'opatch')
        sw_release = inventory.get_result(inventory_id, 'sw_release')
        home_free = inventory.get_result(inventory_id, 'home_free')
        started = inventory.get_result(inventory_id, 'started')

        if sw_release and (release_date in sw_release):
            logger.info(f"Patch presence confirmed: {sw_release} ")
        else :
            logger.error(f"ERROR: {release_date} patch presence not detected! Please investigate!")
            patch_rc -= 1

        rc = update_patching_tbl(inventory, target, logger, ticket, 'APPLY', patch_rc-1 )

        update_sql = ('update dbc_team.patching set patch_date=sysdate ')
        if opatch_ver:
            update_sql += ', post_opatch  = \'' + opatch_ver + '\' '
        if sw_release:
            update_sql += ', post_sw_release  = \'' + sw_release + '\' '
        if home_free:
            update_sql += f", post_home_free  = '{home_free}'"
        if started:
            update_sql += (f", db_started  = to_timestamp('{started}', "
                        f"'YYYY-MM-DD HH24:MI:SS')")
            
        update_sql += (f" where id = {str(inventory_id)} and ticket = '{ticket}' ")

        logger.debug("Saving additional patching result data: %s",  str(update_sql))
        RC1, RC2 = inventory.exec_sql(update_sql, 'EXEC')

        if patch_rc != 1:
            logger.error(f"Database Patching had errors. Please investigate on {target.hostname}")
        else:
            logger.info(f"Database Patching completed successfully for {target.instance_name} on {target.hostname}" )

    RC1 = inventory.patch_progress_update(target.hostname, target.instance_name, 'N')

    logger.info(f"Completed running db_patch.py with HOSTNAME={target.hostname} "
                f"INSTANCE={target.instance_name} APPLY={APPLY}")
    logger.info("====================================================")

    process = None
    RC = inventory.disconnect()
    return patch_rc

# ============================================================================
# END main program
# ============================================================================

if __name__ == "__main__":
    hostname, instance_name, rollbacks, oneoffs, release_date, APPLY = '', '', '', '', '', ''
    scp_copy = False

    # Get the parameters from command line
    parser = argparse.ArgumentParser(description='Check targets.')
    parser.add_argument('-H', '--hostname', required=True)
    parser.add_argument('-d', '--instance_name', required=True)
    parser.add_argument('-R', '--rollbacks')
    parser.add_argument('-r', '--release_date')
    parser.add_argument('-O', '--oneoffs')
    parser.add_argument('-A', '--APPLY', default='')
    parser.add_argument('-s', '--scp_copy', default='False')
    args = parser.parse_args()

    patch(args.hostname, args.instance_name, args.rollbacks, args.oneoffs, args.APPLY, \
          args.release_date, args.scp_copy, ticket='')

    sys.exit()
