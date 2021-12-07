from inv_logging import start_logging
import smtplib
import psycopg2
import sys, getopt  # Allows us to interact with the o/s
import paramiko  # Allows us to ssh to the Database Servers
import threading  # Allows us to time and kill hung db connections
from datetime import datetime
from datetime import date
from decouple import config  # Allows us to read .env
# ============================================================================
import results

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
CODIFYDB = config('CODIFYDB')
INVENTORYDB = "dbname=" + CODIFYDB + " user=" + INV_USER + " password=" + INV_PWD + " host=" + CODIFYDB_HOST

GLOBAL_LOG_NAME = "Notifications"
GLOBAL_LOG_FILE = LOG_DIR + GLOBAL_LOG_NAME + "_" + str(date.today()) + ".log"
GLOBAL_LOG_LEVEL = 'INFO'

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

    check_query = 'select threshold, result_column from notifications where 1=1 '
    target_prefix = '''select hostname, instance_name, cast(check_date as text), check_result "ALERT"
                       from target a, check_results b
                      where a.inventory_id = b.inventory_id and check_column = '''
    target_suffix = ''

    try:
        opts, args = getopt.getopt(argv,":t:i:f:s:h")

    except getopt.GetoptError:
        print ('python notifications.py [ -t Database|Server -i <interval in HOURS>  -f [HOURLY|DAILY|WEEKLY] -s [GOLD|SILVER|BRONZE] ]')
        sys.exit(2)

    target_logger.debug('Command Options: %s  Arguments: %s ', opts, args)

    for opt, arg in opts:
        print("Option: {} Argument: {}".format(opt,arg))
        if opt == '-h':
            print ('python notifications.py -t [Database|Server] -i <interval in HOURS> -f [HOURLY|DAILY|WEEKLY] -s [GOLD|SILVER|BRONZE]')
            sys.exit()

        elif opt == "-t" :
            target_type = arg
            target_suffix += ' and target_type = \'' + target_type + '\''

        elif opt == "-i":
            interval = arg
            target_suffix += ' and check_date > ( NOW() - INTERVAL \'' + interval + ' HOURS \' ) '

        elif opt =="-f":
            frequency = arg
            check_query += ' and frequency = \'' + frequency + '\'  order by id'

        elif opt =="-s":
            support_tier = arg
            check_query += ' and support_tier = \'' + support_tier + '\'  order by id'
            target_suffix += ' and support_tier = \'' + support_tier + '\'  order by check_date desc'

    target_logger.info("Running notifications.py with TARGETTYPE=%s INTERVAL=%s FREQUENCY=%s SUPPORT_TIER=%s", target_type,
                        interval, frequency, support_tier)
    target_logger.debug("Check Query: %s", check_query)

    # ============================================================================
    # Connect to the inventory DB to get the notification checks
    # ============================================================================

    # Connect to the Inventory DB
    inventory_conn = psycopg2.connect(INVENTORYDB)
    notification_cursor = inventory_conn.cursor()

    # Get ALL the checks to perform on these targets
    notification_cursor.execute(check_query)
    all_checks = notification_cursor.fetchall()
    target_logger.debug("# of Checks: %s" , len(all_checks))
    target_logger.debug("All Checks: %s" , all_checks)

    ######################################################
    # * * * *   Main Loop of all Notifications   * * * * #
    ######################################################
    TEXT = ''
    for threshold, result_column in all_checks:
        target_query = target_prefix + '\'' + result_column + '\' and check_result::bigint ' + threshold + target_suffix;
        target_logger.debug("Target Query: %s", target_query)
        notification_cursor.execute(target_query)
        targets = notification_cursor.fetchall()
        for hostname, instance_name, date_time, result in targets :
            target_logger.info("%s ALERT: %s value: %s", result_column.upper(), instance_name, result )
            TEXT += result_column.upper() + ' = ' + result + ' on ' + instance_name + '_' + hostname + ' at ' + date_time
            TEXT += '\n'
            TEXT += '\n'

    inventory_conn.close()


    # All Done, let's send the email
    # email options
    SERVER = "app-mail.bell.corp.bce.ca"
    FROM = "orac4i@caddld-590.belldev.dev.bce.ca"
    TO = ["BellITCloudDBC@bell.ca"]
    SUBJECT = frequency + " DBC Alerts from the last " + interval + " hours"

    message = """From: %s
To: %s
Subject: %s

%s
""" % (FROM, ", ".join(TO), SUBJECT, TEXT)

    try:
        server = smtplib.SMTP(SERVER)
        server.set_debuglevel(3)
        server.sendmail(FROM, TO, message)
        server.quit()
    except SMTPException:
        target_logger.error( "Error: unable to send email")

    target_logger.info("Completed notifications.py with TARGETTYPE=%s INTERVAL=%s FREQUENCY=%s SUPPORT_TIER=%s", target_type,
                        interval, frequency, support_tier)
    target_logger.info("====================================================================================")

# ============================================================================
# END main program
# ============================================================================

if __name__ == "__main__":
    target_logger=start_logging(GLOBAL_LOG_LEVEL, GLOBAL_LOG_FILE, GLOBAL_LOG_NAME)    # Log to File
    main(sys.argv[1:])
