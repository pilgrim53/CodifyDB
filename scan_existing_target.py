#!/home/orac4i/Inventory/bin/python

# ============================================================================
# Import all the external Python modules that we need
# ============================================================================
from datetime     import date          # not included by default
from decouple     import config        # Allows us to read .env
from Inv_Logging  import StartLogging  # Allows us to log to a file
import Targets                         # All target functions
import sys, getopt                     # Allows us to interact with the o/s
#                     psycopg2 - for PostgreSQL database calls
import psycopg2


# ============================================================================

# ============================================================================
# Set DBTools Environment and Global Variables
# ============================================================================
target_file="./discovery.txt"
LogFile="/home/orac4i/Inventory/src/logs/scan_targets_"+str(date.today())+".log"
LogLevel="DEBUG"
LogName="Scan_Targets"
DBC_USER = config('DBC_USER')
DBC_PWD  = config('DBC_PWD')
INV_USER = config('INV_USER')
INV_PWD  = config('INV_PWD')
ORACLE_BASE = "/u01/app/oracle"
ORACLE_HOME = "/u01/app/oracle/product/12.2.0.1"
TNS_ADMIN = "/u01/app/oracle/DBTools/"
INVENTORYDB = "dbname=testdb user="+INV_USER+" password="+INV_PWD+" host=caddld-498.belldev.dev.bce.ca"

# ============================================================================


# ============================================================================
# ============================================================================
# ---------------------------   MAIN PROGRAM   -------------------------------
# ============================================================================
# ============================================================================


TargetLogger=StartLogging(LogLevel, LogFile, LogName)  # Log to File 

global CHECKTYPE
CHECKTYPE = 'UPDATE'


try:
    opts, args = getopt.getopt(sys.argv[1:],"h:v:f:t")
    TargetLogger.debug('Parsing Options: %s  Arguments: %s', opts, args)

except getopt.GetoptError:
    print ('ScanTargets.py [ -t <type> ] -v <vendor> -f <frequency> ')
    sys.exit(2)

for opt, arg in opts:
    if opt == '-h':
        print ('ScanTargets.py [ -t <type> ] -v <vendor> -f <frequency> ')
        sys.exit()

    elif opt in ("-t"):
        CHECKTYPE = args[0]
        TargetLogger.debug('Parsing Type Parameter: %s', CHECKTYPE)

if CHECKTYPE == 'UPDATE' :

  # ============================================================================
  # Fetch all the valid database targets from the InventoryDB and
  # check each one database by database
  # Attempt to query that target and record the results
  # ============================================================================
  
  # Connect to the Inventory DB
  
  inventory_conn = psycopg2.connect(INVENTORYDB)
  target_cursor = inventory_conn.cursor()

  # Get ALL the active targets
  target_cursor.execute("""
          select inventoryid, instancename, owner, homedirectory, hostname
              from public.dbc_target
               where decommissioned is null
          order by inventoryid  """)
  all_targets = target_cursor.fetchall()

  inventory_conn.close()

  for InventoryID, InstanceName, Owner, HomeDir, HostName in all_targets:
      result=0
      TargetLogger.debug("InventoryID: %s InstanceName: %s Owner: %s HomeDir: %s HostName: %s ", \
                      InventoryID, InstanceName, Owner, HomeDir, HostName)
  
      result=Targets.Update(InventoryID, HostName, InstanceName, TargetLogger)
      TargetLogger.info('Host: %s Instance: %s InventoryID: %s results: %s ', HostName, InstanceName, InventoryID, result)




elif CHECKTYPE == 'ADD' :  
  # ============================================================================
  # Read through the AddToDBList.txt file database by database
  # Attempt to query that target and record the results
  # Record Format: 1) host_instance 2) owner FID 3) homedir 4) listener 5) ports
  # ============================================================================
  with open(target_file) as tf:
    for entry in tf:
      TargetLogger.info('Parsing new line: %s', entry)
      target="NONE"
      result="NONE"
      inventoryid=0
      scan_list=entry.split(",")
  
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
      # host, instance=target.split("_")     # Needed for oracle_discovery.ksh output
      instance, host=target.split("_")
  
      if host > '' and instance > '' :
        TargetLogger.info('Checking target: %s', str(target))
        #  Try connecting to the database and get info if possible
        for port in ports:
          if port != '':
            print('Target: %s Port: ''%s''', target, port)
            exists=Targets.Scan(target, port, TargetLogger)
            if exists ==0 :  # 0=host exists
              exists=Targets.CreateDBC(target, owner, TargetLogger)
            if exists >= 0 :  # -1 does not exist     0=host exists, 1=database and Cloud_DBC exist  2=Target exists
              inventoryid=Targets.Add(host, instance, 'TBD', '0', owner, homedir, exists, port, TargetLogger)
              if inventoryid > 0 :
                result=Targets.Update(inventoryid, host, instance, TargetLogger)
            else:
              result=Targets.Reject(host, 'ORACLE', instance, exists, owner, homedir, entry, TargetLogger)


      TargetLogger.info('Host: %s Instance: %s InventoryID: %s results: %s ', host, instance, inventoryid, result)
