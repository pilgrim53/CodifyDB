#!/home/orac4i/Inventory/bin/python

# ============================================================================
# Import all the external Python modules that we need
# ============================================================================
from datetime     import date,datetime # not included by default
from decouple     import config        # Allows us to read .env
from Inv_Logging  import StartLogging  # Allows us to log to a file
import Targets                         # All target functions
import sys, getopt                     # Allows us to interact with the o/s
import psycopg2                        # for PostgreSQL database calls

# ============================================================================
# Set DBTools Environment and Global Variables
# ============================================================================
target_file="./discovery.txt"
LOG_DIR  = config('LOG_DIR')
LogName  = "Scan_Targets"
LogFile  = LOG_DIR+LogName+"_"+str(date.today())+".log"
LogLevel = "WARNING"
DBC_USER = config('DBC_USER')
DBC_PWD  = config('DBC_PWD')
INV_USER = config('INV_USER')
INV_PWD  = config('INV_PWD')
ORACLE_BASE = config('ORACLE_BASE')
ORACLE_HOME = config('ORACLE_HOME')
TNS_ADMIN   = "/u01/app/oracle/DBTools/"
CODIFYDB_HOST = config('CODIFYDB_HOST')
CODIFYDB      = config('CODIFYDB')
INVENTORYDB   = "dbname="+CODIFYDB+" user="+INV_USER+" password="+INV_PWD+" host="+CODIFYDB_HOST
# ============================================================================

# ============================================================================
# ============================================================================
# ---------------------------   MAIN PROGRAM   -------------------------------
# ============================================================================
# ============================================================================
# Function:     scan_target
# Description:  Evaluate target info and look for changes to targets.
# Input:        -a (ADD) -t Database|Server -v Vendor
# Ouptut:       Insert new or update existing records in Targets table
# Returns:      None
# ============================================================================
def main(argv):

  global CHECKTYPE
  global TARGETTYPE
  CHECKTYPE  = 'UPDATE'     # Default to scan / update existing known Targets
  TARGETTYPE = 'Database'   # Default to database targets

  TargetLogger=StartLogging(LogLevel, LogFile, LogName)  # Log to File
  TARGETQUERY='select inventoryid, instancename, owner, homedirectory, hostname, targettype \
                from public.dbc_target where decommissioned is null '


  try:
    opts, args = getopt.getopt(argv,":t:v:ah")

  except getopt.GetoptError:
          print ('scan_targets.py [ -a (ADD) -t Database|Server -v Vendor  ] | -h (help) ')
          sys.exit(2)

  TargetLogger.debug("All Options passed: {}".format(opts))
  TargetLogger.debug("All arguments passed: {}".format(args))

  for opt, arg in opts:
    TargetLogger.debug("Option: {} Argument: {}".format(opt,arg))
    if opt == '-h':
      print ('scan_targets.py [ -t Database|Server -v Vendor -a (ADD) ] | -h (help) ')
      sys.exit()

    elif opt == "-a" :
      CHECKTYPE = 'ADD'

    elif opt == "-t" :
      TARGETTYPE = arg
      TARGETQUERY += ' and targettype = \'' + TARGETTYPE + '\''
    elif opt == "-v" :
      VENDOR = arg
      TARGETQUERY += ' and vendor = \'' + VENDOR + '\''

  TARGETQUERY += ' order by inventoryid'

  CHECKQUERY="select check_command, check_type, result_column, handler from public.checklist \
               where frequency='"+TARGETTYPE+"' order by handler, priority"

  # Connect to the Inventory DB
  inventory_conn = psycopg2.connect(INVENTORYDB)
  target_cursor = inventory_conn.cursor()

  # Get ALL the checks to perform on these targets
  target_cursor.execute(CHECKQUERY)
  all_checks = target_cursor.fetchall()
  TargetLogger.debug("All Checks: %s" , all_checks)

  if CHECKTYPE == 'UPDATE' :
    # ============================================================================
    # Update existing targets that match the target criteria
    # ============================================================================
    # ============================================================================
    # Fetch all the valid database targets from the InventoryDB and
    # check each one database by database
    # Attempt to query that target and record the results
    # ============================================================================

    # Get ALL the active targets
    target_cursor.execute(TARGETQUERY)
    all_targets = target_cursor.fetchall()
    # TargetLogger.debug("All Targets: %s" , all_targets)

    inventory_conn.close()

    ######################################################
    # * * * *  Main Loop of all in-scope Targets * * * * #
    ######################################################
    for inventoryid, instance, owner, homedir, host, TargetType in all_targets:
        result=0
        TargetLogger.debug("inventoryid: %s instance: %s owner: %s homedir: %s HostName: %s TargetType: %s", \
                        inventoryid, instance, owner, homedir, host, TargetType)

        oldHandler = ''
        ###############################################################################
        # Sub Loop of All Checks for the Target
        # Reuse the connection to the target for all similar checks with same handler
        ###############################################################################
        for check, check_type, result_column, handler in all_checks:
            result=''
            if handler != oldHandler :
                if oldHandler != '' and curr_connection != '':
                    # Targets.Disconnect(curr_connection)
                    curr_connection.close()
                oldHandler = handler
                rc, curr_connection=Targets.Connect(host, instance, owner, handler, TargetLogger)


            if curr_connection:  # connection still works
                rc, result=Targets.GetInfo(check, handler, curr_connection, TargetLogger)
                print ('Result: %s', result)
                if result :
                  Targets.UpdateColumn(inventoryid, result_column, result, TargetLogger)

            else:   # connection no longer works
                Targets.UpdateColumn(inventoryid, 'status', 'No '+handler+' Connection', TargetLogger)

            TargetLogger.info("Inventory ID: %s Attribute: %s Value: %s" , inventoryid, result_column, result)

        # Targets.Disconnect(curr_connection)
        curr_connection.close()

  # ============================================================================
  # Look for and add NEW Targets to the inventory
  # ============================================================================

  elif CHECKTYPE == 'ADD' :
    # ============================================================================
    # Read through the target_file record by record
    # Attempt to query that target and record the results
    # DB Record Format: 1) host_instance 2) owner FID 3) homedir 4) listener 5) ports
    # Server Record Format: 1) hostname 2) IP Address
    # ============================================================================
    with open(target_file) as tf:
      for entry in tf:
        TargetLogger.info('Parsing new line: %s', entry)
        target="NONE"
        result="NONE"
        inventoryid=0
        entry=entry.strip()
        scan_list=entry.split(",")

        if TARGETTYPE == "Server":
          if len(scan_list) == 2 :
            host, owner = entry.split(",")
          else :
            owner="fidBIN"

          host=entry.upper().strip()
          owner=owner.strip()
          target=host+"_"+host
          instance=host
          ports='22'
          homedir,exists='',''
        else:

          if len(scan_list) > 4 :
            target, owner, homedir, listener, *ports = entry.split(",")
          elif len(scan_list) == 4 :
            target, owner, homedir, listener = entry.split(",")
            ports=1521, 2349
          elif len(scan_list) == 3 :
            target, owner, homedir = entry.split(",")
            exists=''
            ports=1521, 2349
          elif len(scan_list) == 2 :
            target, owner = entry.split(",")
            homedir,exists='',''
            ports=1521, 2349
          elif len(scan_list) == 1:
            target = entry
            owner,homedir,exists='','',''
            ports=1521, 2349

          target=target.upper().strip()
          owner=owner.strip()
          # host, instance=target.split("_")     # Needed for oracle_discovery.ksh output
          instance, host=target.split("_")

        if host > '' and instance > '' :
          TargetLogger.info('Checking target: %s', str(target))
          # Try connecting to the database and get info if possible
          # exists=Targets.CreateDBC(target, owner, TargetLogger)
          # if exists >= 0 :  # -1 does not exist     0=host exists, 1=database and Cloud_DBC exist  2=Target exists
          #  Why add if already there?
          inventoryid=Targets.Add(host, instance, 'TBD', '0', owner, homedir, exists, 0, TARGETTYPE, TargetLogger)
          if inventoryid > 0 :
            result=0
            TargetLogger.debug("inventoryid: %s instance: %s owner: %s homedir: %s HostName: %s TargetType: %s", \
                            inventoryid, instance, owner, homedir, host, TARGETTYPE)

            oldHandler = ''
            ###############################################################################
            # Sub Loop of All Checks for the Target
            # Reuse the connection to the target for all similar checks with same handler
            ###############################################################################
            for check, check_type, result_column, handler in all_checks:
                result=''
                if handler != oldHandler :
                    if oldHandler != '' and curr_connection != '':
                        # Targets.Disconnect(curr_connection)
                        curr_connection.close()
                    oldHandler = handler
                    rc, curr_connection=Targets.Connect(host, instance, owner, handler, TargetLogger)

                if curr_connection:  # connection still works
                    Targets.UpdateColumn(inventoryid, 'status', handler+' Connected', TargetLogger)
                    rc, result=Targets.GetInfo(check, handler, curr_connection, TargetLogger)
                    print ('Result: %s', result)
                    if result :
                      Targets.UpdateColumn(inventoryid, result_column, result, TargetLogger)

                else:   # connection no longer works
                    Targets.UpdateColumn(inventoryid, 'status', 'No '+handler+' Connection', TargetLogger)

                TargetLogger.info("Inventory ID: %s Attribute: %s Value: %s" , inventoryid, result_column, result)

            # Targets.Disconnect(curr_connection)
            Targets.UpdateColumn(inventoryid, "lastcheckdate", str(datetime.now()), TargetLogger)
            if curr_connection != '':
              curr_connection.close()

          else:
            result=Targets.Reject(host, '', instance, exists, owner, homedir, entry, TARGETTYPE, TargetLogger)

        TargetLogger.info('Host: %s Instance: %s inventoryid: %s results: %s ', host, instance, inventoryid, result)

# ============================================================================
# END main program
# ============================================================================

if __name__ == "__main__":
    TargetLogger=StartLogging(LogLevel, LogFile, LogName)    # Log to File
    main(sys.argv[1:])
    
