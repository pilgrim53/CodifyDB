"""
# ============================================================================
# Name:         notifications.py
# Description:  Monitors IT targets currently stored in TARGETS
#               Check results are stored and viewable in CHECK_RESULTS
#
# Input Files:  TARGETS Table
#               CHECKLIST table
#               NOTIFICATIONS Table
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

import smtplib
import os, sys, argparse  # Allows us to interact with the o/s
from datetime import datetime
from datetime import date
from decouple import config  # Allows us to read .env
# ============================================================================
from inv_logging import start_logging
from inventory import Inventory
import target

# ============================================================================


# ============================================================================
# ============================================================================
# ---------------------------     MAIN PROGRAM     -------------------------------
# ============================================================================
# ============================================================================
def main(argv):
    # Set some defaults
    log_dir = config('LOG_DIR')
    log_name = "Notifications"
    log_file = log_dir + log_name + "_" + str(date.today()) + ".log"
    log_level = 'INFO'
    log_to_console = 'OFF'

    # Log to File
    target_logger = start_logging(log_level, log_file, log_name, log_to_console)

    parser = argparse.ArgumentParser(description='DBC Notifications.')
    parser.add_argument('-t', '--target_type', default='Database')
    parser.add_argument('-i', '--interval', default='24')
    parser.add_argument('-f', '--frequency', default='HOURLY')
    parser.add_argument('-s', '--support_tier', default='Standard')
    parser.add_argument('-v', '--vendor', default='ALL')
    parser.add_argument('-x', '--low_id', default='1')
    parser.add_argument('-y', '--high_id', default='999999')
    args = parser.parse_args()

    inventory = Inventory(target_logger)
    rc = inventory.connect()
    if rc == 0:
        target_logger.error("Unable to connect to the Inventory Database. "
                            "Exiting.")
        sys.exit()

    check_query = 'select threshold, result_column from notifications where 1=1 '
    target_prefix = '''select upper(hostname), instance_name, to_char(check_date,\'YYYY-MM-DD HH24:MI:SS\'), check_result "ALERT"
                       from targets a, check_results b
                      where a.inventory_id = b.inventory_id and check_column = '''
    target_suffix = ''

    if args.target_type == 'Database' or args.target_type == 'Server' :
            target_suffix += ' and upper(target_type) = \'' + args.target_type.upper() + '\''

    if int(args.interval) > 0 :
        target_suffix += ' and check_date > ( sysdate - ' + args.interval +  ' / 24 )'

    check_query += ' and upper(frequency) = \'' + args.frequency.upper() + '\' '
    target_suffix += ' and upper(support_tier) = \'' + args.support_tier.upper() + '\'  order by check_date desc'

    target_logger.info("Running notifications.py with TARGETTYPE=%s INTERVAL=%s FREQUENCY=%s SUPPORT_TIER=%s", args.target_type,
                        args.interval, args.frequency, args.support_tier)
    target_logger.info("Check Query: %s", check_query)

    # Get ALL the checks to perform on these targets
    RC, all_checks=inventory.exec_sql(check_query, 'ALL')
    print(str(all_checks))

    target_logger.debug("# of Checks: %s" , len(str(all_checks)))
    target_logger.debug("All Checks: %s" , str(all_checks))

    ######################################################
    # * * * *   Main Loop of all Notifications   * * * * #
    ######################################################
    TEXT = ''
    for threshold, result_column in all_checks:
        target_query = target_prefix + '\'' + result_column + '\' and REGEXP_LIKE (check_result, \'^[0123456789\.]*$\') \
                        and to_number(check_result) ' + threshold + target_suffix;

        target_logger.debug("Check: %s" , target_query)
        RC, targets=inventory.exec_sql(target_query, 'ALL')

        for hostname, instance_name, date_time, result in targets :
            target_logger.info("%s ALERT: %s value: %s", result_column.upper(), instance_name, result )
            TEXT += result_column.upper() + ' = ' + result + ' on ' + instance_name + '_' + hostname + ' at ' + str(date_time)
            TEXT += '\n'
            TEXT += '\n'

    target_logger.debug("Alert Text: %s ", TEXT )

    ######################################################
    # * * * *  Now Check all the Database Disk   * * * * #
    ######################################################

    target_list = inventory.get_targets(args.target_type, args.vendor, args.low_id, args.high_id)
    for target in target_list:

        disk_query =(f"Select check_result from dbc_team.check_results A"
                     f" where inventory_id = { target.inventory_id }"
                       f" and check_column='database_disks' "
                       f" and check_date = (select max(check_date) from dbc_team.check_results "
                                          f" where check_column='database_disks' "
                                            f" and inventory_id = A.inventory_id)" )

        rc , disk_result = inventory.exec_sql(disk_query, 'ALL') # returns list of tuples of the groups e.g [(group1 group2 group3,), (group8 group9,), ...])
        target_logger.debug("Database Disk: %s ", disk_result )

        for host_disk_tup in disk_result:
            target_logger.debug(f"Host_Disk_Tup: {host_disk_tup} ")
            disks =  host_disk_tup
            target_logger.debug(f"Inside_Info: {target.hostname} Disks: {disks}")
            new_disks = [disk.strip('\(\)\'') for disk in str(disks).split(',')]
            for disk in new_disks:
                target_logger.debug(f"Disk for {target.hostname}: {disk}")
                if '|' in disk :
                    mt_pt,space = disk.split('|')
                    mt_pt = str(mt_pt)
                    target_logger.debug(f"Mount point {target.inventory_id}: {mt_pt}")

                    # ssh -q -i  ~/.ssh/orac4i_2024_rsa oraais@caddlt-4001.belldev.dev.bce.ca -C "df -h  /u02 | grep \"/u02\" " | awk '{print $5}'
                    if '+' in mt_pt and space:
                        if float(space) > 95:
                            target_logger.info(f"Hostname: {target.hostname}  Mount Point: {mt_pt} Percent Full: {space}")
                            TEXT += (f"Hostname: {target.hostname}  Mount Point: {mt_pt} Percent Full: {space}")
                            TEXT += '\n'

                    else:
                        check_command=(f"df -h {mt_pt} | while read first second third fourth fifth sixth seventh; do echo $first $second $third $fifth $sixth $seventh;  done | grep \"{mt_pt}\" ")

                        try:
                            rc=target.connect('ssh', inventory)
                            rc, result=target.get_info(check_command, 'ssh')
                            target_logger.debug(f"Check result: {result}")

                            disk_pct = result.split()[3]
                            target_logger.debug(f"Percent Full: {disk_pct}")
                            if disk_pct > "95%" :
                                target_logger.info(f"Hostname: {target.hostname}  Mount Point: {mt_pt} Percent Full: {disk_pct}")
                                TEXT += (f"Hostname: {target.hostname}  Mount Point: {mt_pt} Percent Full: {disk_pct}")
                                TEXT += '\n'
                            rc=target.disconnect()
                        except:
                            target_logger.error(f"Unable to connect to: {target.hostname}")

    # All Done, let's send the email
    # email options
    SERVER = "app-mail.bell.corp.bce.ca"
    FROM = "orac4i@caddld-590.belldev.dev.bce.ca"
    TO = "BellITCloudDBC@bell.ca"
    SUBJECT = args.frequency + " DBC Alerts from the last " + args.interval + " hours"

    message = """From: %s
To: %s
Subject: %s

%s
""" % (FROM, ", ".join([TO]), SUBJECT, TEXT)

    try:
        server = smtplib.SMTP(SERVER)
        server.set_debuglevel(3)
        server.sendmail(FROM, TO, message)
        server.quit()
    except smtplib.SMTPException:
        target_logger.error( "Error: unable to send email")

    # ssh to db server with orac4i ssh key
    # command = 'echo  \"' + str(TEXT) + '\" | mail -s "' + str(SUBJECT) + '" -r ' + str(FROM) + ' ' + TO
    # target_logger.debug("Alert email: %s ", command )
    # process = os.system(command)
    rc=inventory.disconnect()
    target_logger.info("Completed notifications.py with TARGETTYPE=%s INTERVAL=%s FREQUENCY=%s SUPPORT_TIER=%s",
                       args.target_type, args.interval, args.frequency, args.support_tier)
    target_logger.info("====================================================================================")

# ============================================================================
# END main program
# ============================================================================

if __name__ == "__main__":

    main(sys.argv[1:])
