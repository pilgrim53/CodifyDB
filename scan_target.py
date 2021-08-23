#!/home/orac4i/Inventory/bin/python

# ============================================================================
# Import all the external Python modules that we need
# ============================================================================
from datetime     import date          # not included by default
from decouple     import config        # Allows us to read .env
from Inv_Logging  import StartLogging  # Allows us to log to a file
import Targets                         # All target functions
# ============================================================================

# ============================================================================
# Set DBTools Environment and Global Variables
# ============================================================================
target_file="./discovery.txt"
LogFile="/home/orac4i/Inventory/src/logs/scan_targets_"+str(date.today())+".log"
LogLevel="DEBUG"
LogName="Scan_Targets"
# ============================================================================


# ============================================================================
# ============================================================================
# ---------------------------   MAIN PROGRAM   -------------------------------
# ============================================================================
# ============================================================================

TargetLogger=StartLogging(LogLevel, LogFile, LogName)  # Log to File 

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
    owner=owner.lower().strip()
    # host, instance=target.split("_")     # Needed for oracle_discovery.ksh output
    instance, host=target.split("_")

    if host > '' and instance > '' :
      TargetLogger.info('Checking target: %s', str(target))
      #  Try connecting to the database and get info if possible
      for port in ports:
        if port != '':
          print('Target: %s Port: ''%s''', target, port)
          exists=Targets.Scan(target, owner, port, TargetLogger)
          if exists == 0 : 
            exists=Targets.CreateDBC(target, owner, TargetLogger)
            break
          if exists >= 0 :  # -1 does not exist     0=host exists, 1=database and Cloud_DBC exist  2=Target exists
            inventoryid=Targets.Add(host, instance, 'TBD', '0', owner, homedir, exists, port, TargetLogger)
            if inventoryid > 0 :
              result=Targets.Update(inventoryid, host, instance, TargetLogger)
            break
          else:
            result=Targets.Reject(host, 'ORACLE', instance, exists, owner, homedir, entry, TargetLogger)


    TargetLogger.info('Host: %s Instance: %s InventoryID: %s results: %s ', host, instance, inventoryid, result)
