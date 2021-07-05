#!/home/orac4i/Inventory/bin/python
#  -*- coding: utf-8
# ============================================================================
# Copyright (c) 2020 Bell Canada
#
# All rights reserved. No part of this script may be copied or translated
# in any form or by any means without prior written permission from BELL.
#
# DO NOT MODIFY THIS SCRIPT LOCALLY
# This script is part of the DBC DBTools.  Do not make
# modifications to local copies.
# ============================================================================
# Description
# ============================================================================
#
# Script name:          add_targets.py
#
# Version:              1.02
#
# Purpose:              This script adds new targets from DBList into the 
#                       DBC Inventory Database. If the targe exists and 
#                       something has changed, then it updates the entry.
#
# Input files:          /u01/app/oracle/DBTools/AddToDBList.txt
#
# Output:               Entries into the DBC_Targets tables
#                       Log files to ./logs directory
#
# Syntax:               python add_targets.py
#
# Called Routines:      cx_Oracle - for Oracle database calls
#                       psycopg2 - for PostgreSQL database calls
#                       date, grep, awk, cat, uname - misc UNIX commands
#
# Return Codes:
#
# Restrictions:         You must first run "source ~/venv/bin/activate
#                       to enter the necessary Python virtual environment
#
# Abend instructions:   Resolve and rerun
#
# ============================================================================
# History of Changes
# ============================================================================
# Date         Person            Version  Comments
# 2021/01/13   M.Pankratz        1.00     Created
# 2021/01/15   M.Pankratz        1.01     rename, add logging, restructure
# 2021/01/19   M.Pankratz        1.02     add containers
# 2021/03/03   M.Pankratz        1.03     add host type (VM or physical)
# 2021/06/10   M.Pankratz        1.04     move settings into separate file
# ============================================================================


# ============================================================================
# Import all the external Python modules that we need
# ============================================================================
import paramiko           # Allows us to ssh to the target hosts
import cx_Oracle          # https://oracle.github.io/python-cx_Oracle/
import psycopg2           # https://pypi.org/project/psycopg2/
import psycopg2.extras    # This gives access to the psycopg2 error messages
import sys                # for some reason this is not included by default
import logging            # https://docs.python.org/3/library/logging.html
import threading          # Allows us to time and kill hung db connections
# from numpy import asarray     # convert sql result tuples to python arrays
from datetime import date       # for some reason this is not included by default
from check_oms import CheckOMS  # Allows us to query the OEM DEv instance 
from decouple  import config    # Allows us to read .env
# ============================================================================

# ============================================================================
# Set DBTools Environment and Global Variables
# ============================================================================
DBC_USER = config('DBC_USER')
DBC_PWD  = config('DBC_PWD')
INV_USER = config('INV_USER')
INV_PWD  = config('INV_PWD')
ORACLE_BASE = "/u01/app/oracle"
ORACLE_HOME="/u01/app/oracle/product/12.2.0.1"
TNS_ADMIN="/u01/app/oracle/DBTools/"
target_file="/u01/app/oracle/DBTools/AddToDBList.txt"
Log_File="/home/orac4i/Inventory/src/logs/add_targets_"+str(date.today())+".log"
LogLevel="DEBUG"
GlobalLog_File = "/home/orac4i/Inventory/src/logs/check_targets_"+str(date.today())+".log"
GlobalLogLevel = logging.DEBUG
INVENTORYDB = "dbname=testdb user="+INV_USER+" password="+INV_PWD+" host=caddld-498.belldev.dev.bce.ca"


# ============================================================================

# ============================================================================
# Define Functions
# ============================================================================

def StartLogging(LogLevel, Log_File):
    logging.basicConfig(filename=Log_File, level=logging.DEBUG)
    logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
    TargetLogger=logging.getLogger('Add_Target')
    TargetLogger.setLevel(logging.DEBUG)

    # Create a console handler
    ch = logging.StreamHandler()
    #ch.setLevel(logging.LogLevel)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    TargetLogger.addHandler(ch)


    return TargetLogger
    # End StartLogging

# ============================================================================
# Logging examples
# ============================================================================
# logging.debug('This should go to the log file.')
# logging.info('So should this')
# logging.warning('And this, too')
# logging.error('And non-ASCII stuff, too, like Øresund and Malmö')
# ============================================================================

# ============================================================================
#  GetHostType
# ============================================================================

def GetHostType(host, owner):

  HostType="Unknown"
  command="dmesg | grep \"Hardware name:\" | head -n 1 | awk -F\":\" '{print $2}'"
  ssh1 = paramiko.SSHClient()
  ssh1.load_system_host_keys()
  ssh1.set_missing_host_key_policy(paramiko.AutoAddPolicy())

  TargetLogger.info("Connecting to %s as %s to run %s ", host, owner, command)

  timer1 = threading.Timer(10,ssh1.close)
  timer1.start()  # start counting right before connecting to the database

  try:
      ssh1.connect(host, 22, owner)
      stdin, stdout, stderr = ssh1.exec_command(command)
      HostTypeRow = stdout.readlines()
      TargetLogger.debug("Result: %s ", HostTypeRow)
      HostType=str(HostTypeRow[0]).strip()
      timer1.cancel()  # cancel the connection thread if it's still alive after 30 seconds

  except Exception as exc:
      TargetLogger.error("Error connecting to check host type: %s", host)

  finally:
      ssh1.close()

  return HostType

# ============================================================================
#  GetDBora
# ============================================================================

def GetDBora(host, owner):

  dbora="Unknown"
  command = "if [ ! -f /etc/init.d/dbora ];  then echo \"NONE\" ; else grep Version /etc/init.d/dbora | sed s/#//g ; fi"
  ssh1 = paramiko.SSHClient()
  ssh1.load_system_host_keys()
  ssh1.set_missing_host_key_policy(paramiko.AutoAddPolicy())

  TargetLogger.info("Connecting to %s as %s to run %s ", host, owner, command)

  timer1 = threading.Timer(10,ssh1.close)
  timer1.start()  # start counting right before connecting to the database

  try:
      ssh1.connect(host, 22, owner)
      stdin, stdout, stderr = ssh1.exec_command(command)
      DBoraRow = stdout.readlines()
      TargetLogger.debug("Result: %s ", DBoraRow)
      dbora=str(DBoraRow[0]).strip()
      timer1.cancel()  # cancel the connection thread if it's still alive after 30 seconds

  except Exception as exc:
      TargetLogger.error("Error connecting to check host type: %s", host)

  finally:
      ssh1.close()

  return dbora

# ============================================================================
# Function:    CheckOratab
# Description: Checks the oratab file of the target host
#              to find the Oracle_Home path
# Input:       Takes target in the format of host_instance
# Ouptut:      Returns a boolean if its new and the target info
#              [instance,host,DBCreateDate,DBID,version,logMode,status]
# ============================================================================
def CheckOratab(target, owner):
  NewHomeDir='UNKNOWN'
  instance, host=target.split('_')
  ssh1 = paramiko.SSHClient()
  ssh1.load_system_host_keys()
  ssh1.set_missing_host_key_policy(paramiko.AutoAddPolicy())

  command = "grep -i " + instance + ": /etc/oratab | awk -F':' '{print $2}' | head -n 1"
  TargetLogger.info("Connecting to %s as %s to run %s ", host, owner, command)

  timer1 = threading.Timer(30,ssh1.close)
  timer1.start()  # start counting right before connecting to the database

  try:
      ssh1.connect(host, 22, owner)
      stdin, stdout, stderr = ssh1.exec_command(command)
      HomeDirRow = stdout.readlines()
      TargetLogger.debug("Result: %s ", HomeDirRow)
      NewHomeDir=str(HomeDirRow[0]).strip()

  except Exception as exc:
     TargetLogger.error("Error connecting to check oratab: %s", host)

  timer1.cancel()  # cancel the connection thread if it's still alive after 30 seconds

  return NewHomeDir

# ============================================================================
# Function:    PingTarget
# Description: Checks the Inventory database and retuns the result
# Input:       Takes target in the format of instance_host
# Ouptut:      Returns a boolean if its new and the target info
#              [instance,host,DBCreateDate,DBID,version,logMode,status]
# ============================================================================
def PingTarget(target):
  # Set some initial values each time we do a check
  NewTarget=False  # Set to False until we determine if it's True
  TargetRow=[]     # create an empty array to start
  instance, host=target.split('_')

  if "+ASM" in target:
     TargetLogger.info('ASM Instance found: %s', str(TargetRow))
     # Build connection to
     # return NewTarget, TargetRow
  else:

    try:
        connection = cx_Oracle.connect(DBC_USER, DBC_PWD, target.strip(), encoding="UTF-8")
        timer = threading.Timer(30,connection.cancel)
        db_info_cursor = connection.cursor()
        timer.start()  # start counting right before connecting to the database
        db_info_cursor.execute("""
            select upper(instance_name), upper(host_name), to_char(db.created, 'YYYY-MM-DD'), to_char(db.dbid), 
                   version, db.log_mode, status, database_role,
                   CASE when substr(version,0,instr(version,'.')-1) > 11
			then case
			         when SYS_CONTEXT('USERENV','CON_NAME') = instance_name
			         then 'STANDALONE'
			         else SYS_CONTEXT('USERENV','CON_NAME')
			     end
			else 'STANDALONE'
                    end as container,
                    CASE when substr(version,0,instr(version,'.')-1) > 11
			 then SYS_CONTEXT('USERENV','ORACLE_HOME')
			 else 'UNKNOWN'
	 	    end as oracle_home
            from v$instance, v$database db
            where instance_name like db.name ||'%' """)

        TargetRow = db_info_cursor.fetchone()
        timer.cancel()  # cancel the connection thread if it's still alive after 30 seconds

        if TargetRow != None:
            # This target is reachable as Cloud_DBC!!
            TargetLogger.debug('Connected to: %s', str(TargetRow))
            NewTarget = True
            TargetRowList=list(TargetRow)

            db_info_cursor.execute("""
               select value from v$parameter where name ='db_block_size' """)
            DBBlockSize = db_info_cursor.fetchone() 

            db_info_cursor.execute("""
               select distinct(username) from v$process where background=1 """)
            OwnerRow = db_info_cursor.fetchone()
            Owner=str(OwnerRow[0]).strip()

            #in_oms=CheckOMS(target)
            in_oms="N"
            hosttype=GetHostType(host, Owner)
            dbora=GetDBora(host, Owner)
    
            homedir=TargetRowList.pop() 

            if homedir == 'UNKNOWN':
              # make sure we use the actual Oracle "Instance" returned above to get the container
              instance=str(target[0]).upper()
              TargetRowList.append(CheckOratab(target, Owner))
            else:
              TargetRowList.append(homedir)
          
            TargetRowList.append(Owner)
            TargetRowList.append('ORACLE')
            TargetRowList.append(int(DBBlockSize[0]))
            TargetRowList.append(in_oms)
            TargetRowList.append(hosttype)
            TargetRowList.append(dbora)

            TargetRow=tuple(TargetRowList)
 
            # All done with the Target Oracle connection
            connection.close()
        else:
            # This target is not reachable as Cloud_DBC!!
            TargetLogger.debug('Unable to connect to: %s', str(TargetRow))
            NewTarget = False
   
    
    # Handle all the things that could go wrong with this connection attempt
    except cx_Oracle.DatabaseError as exc:
    # If there was a database error we need the ORA-##### error
    # This might mean the database exists
        error, = exc.args
        oraerr=str(error.code)
        NotExist=['12545','12541','12543','12514','12505']
        if oraerr in NotExist :
            TargetLogger.error('Target: %s   Status: ORA- %s  Message: %s', str(target), oraerr, str(error))
            TargetLogger.error('TNS Error: Target DB not added to inventory. Correct the issue or remove from DBList')
            NewTarget = False
        else:
            TargetLogger.warning('Target: %s   Status: ORA- %s  Message: %s', str(target), oraerr, str(error))
            # We can add a placeholder for this target into inventory even though we can't log in
            NewTarget=True  
            TargetLogger.info('Target %s exists, but couldn''t log in. Setting blank initial values.', str(target))
            TargetRow = (str(instance).upper(),str(host).upper(),"1900-01-01",'','Unknown','',oraerr,'','STANDALONE','','','ORACLE',0,'','','')
            NewTarget = True


    except Exception as exc:
    # ============================================================================
    # There was a problem that was not database related
    # ============================================================================
        error, = exc.args
        TargetLogger.error('Target: %s   Error: %s', str(target), error)
        TargetLogger.error('Target DB not added to inventory. Correct the issue or remove from DBList')
        NewTarget = False
 
    

  return NewTarget, TargetRow
# ============================================================================
# END PingTarget
# ============================================================================

# ============================================================================
# Function:    UpdateTarget
# Description: Checks the Inventory database and retuns the result
# Input:       Takes target in the format of host_instance 
# Ouptut:      Returns a boolean if its new and the target info 
#              [instance,host,DBCreateDate,DBID,version,logMode,status]
# ============================================================================
def UpdateTarget(target):
        NewTarget   =False
        row         =None
        instance    =str(target[0]).upper()
        host        =str(target[1]).upper()
        DBCreateDate=str(target[2])
        DBID        =str(target[3])
        version     =str(target[4])
        logMode     =str(target[5])
        status      =str(target[6])
        Role        =str(target[7])
        Container   =str(target[8]).upper()
        HomeDir     =str(target[9])
        Owner       =str(target[10])
        Vendor      =str(target[11])
        DBBlockSize =str(target[12])
        In_OMS      =str(target[13])
        hosttype    =str(target[14])
        dbora       =str(target[15])

        # ============================================================================
        # Open a connection to the Inventory Database 
        # Insert or update the results if:
        #   1) The target is not already there
        #   2) If anything has changed about the target (i.e. version or logmode)
        # ============================================================================
         
        postgres_conn = psycopg2.connect(INVENTORYDB)
   
        # ============================================================================
        # 1) See if the target is in the inventory database
        # ============================================================================

        if Container==instance :
           Container='STANDALONE'
        if Container=='None':
           Container=''

        select_cursor = postgres_conn.cursor()
        TargetLogger.info('Checking if Host: %s Instance: %s Container: %s exists in inventory.', host, instance, Container)
   
        try: 
           
            # Get just the info about the target for comparison
            select_cursor.execute("""
                select InstanceName, HostName, to_char(DBCreatedDate,'YYYY-MM-DD'), DBID,  Version, ArchiveLogMode, Status, Role, 
                       Container, HomeDirectory, Owner, Vendor, BlockSize, in_oms, hosttype, dbora
                    from public.DBC_Target
                    where InstanceName = %s
                    and Coalesce(Container,'') = %s
                    and HostName = %s; 
                    """, (instance, Container, host ))
            row = select_cursor.fetchone()

            # Get just the InventoryID for reference
            select_cursor.execute("""
                select InventoryID
                    from public.DBC_Target
                    where InstanceName = %s
                    and Coalesce(Container,'') = %s
                    and HostName = %s; 
                    """, (instance, Container, host ))
            oldInventoryID = select_cursor.fetchone()

        except (psycopg2.DataError) as exc:
            errormsg = psycopg2.errors.lookup(exc.pgcode)
            TargetLogger.error('Target: %s  DataError: %s', str(target), str(errormsg))
            if ((errormsg == '02000' ) or ( errormsg == NoData )): 
                # Try to detect and flag "No Data Found" as it means we don't have this target
                TargetLogger.info('Is this a New Target Found!?!?')
                TargetLogger.info('Host: %s  Instance: %s  Message: %s', str(host), str(instance), str(errormsg))
                TargetLogger.error('Target DB not added to inventory. Correct the issue or remove from DBList')
                # Now lets insert or update if we got data above
                NewTarget=True
                pass

            else:
                # Move on.  Data error checking the Inventory
                NewTarget=False
                TargetLogger.info('Skipping Target: %s  DataError: %s', str(target), str(errormsg))
                
        except (psycopg2.DatabaseError, psycopg2.IntegrityError, psycopg2.InternalError)   as exc:
            error, = exc.args
            TargetLogger.error('Target: %s  Message: %s', str(target),  str(error))

   
        except Exception as exc:
            error, = exc.args
            TargetLogger.error('Postgres Exception on target: %s  Message: %s', str(target),  str(error))
   

        if row == None:
            TargetLogger.info('New Target Found. Host: %s Instance: %s ', str(host), str(instance))

            insert_cursor = postgres_conn.cursor()
   
            try:
                insert_cursor.execute("""
                     INSERT INTO public.dbc_target (InventoryCreate, DBCreatedDate, DBID, InstanceName, 
                                                    HostName, Version, ArchiveLogMode, Status, Role, Container,
                                                    HomeDirectory, Owner, Vendor, BlockSize, in_oms, hosttype, dbora ) 
                     VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s );
                 """, ( date.today(), DBCreateDate, DBID, instance, host, version, logMode, status, Role, Container, \
                        HomeDir, Owner, Vendor, DBBlockSize, In_OMS, hosttype, dbora ))

                # Make the changes to the database persistent
                postgres_conn.commit()

            except (psycopg2.DatabaseError, psycopg2.IntegrityError, psycopg2.DataError, psycopg2.InternalError)   as exc:
                error, = exc.args
                TargetLogger.error('Error inserting new target: %s %s Container: %s %s ', str(host),str(instance), str(Container), str(error))
                result='INSERT FAILED'
         
            except Exception as exc:
                error, = exc.args
                TargetLogger.error('Exception occurred inserting target: %s %s Container: %s %s', \
                                    str(host), str(instance), str(Container), str(error))
                result='INSERT FAILED'

            else:
                result='TARGET ADDED'
   
        else:  # host, instance, container already  exists in inventory
                # see if something changed about the database info and UPDATE it.
                # select InventoryID, InstanceName, HostName, DBCreatedDate, DBID,  Version, ArchiveLogMode 
                oldinstance    =str(row[0])
                oldhost        =str(row[1])
                oldDBCreateDate=str(row[2])
                oldDBID        =str(row[3])
                oldversion     =str(row[4])
                oldlogMode     =str(row[5])
                oldStatus      =str(row[6])
                oldRole        =str(row[7])
                oldContainer   =str(row[8])
                oldHomeDir     =str(row[9])
                oldOwner       =str(row[10])
                oldVendor      =str(row[11])
                oldDBBlockSize =str(row[12])
                oldIn_OMS      =str(row[13])
                oldhostype     =str(row[14])
                olddbora       =str(row[15])

                if instance == Container:
                   TargetLogger.info('Instance %s Container is %s and should be STANDALONE ', instance, Container)

                if target != row:
                    TargetLogger.info('Target known. Status has changed. Host: %s  Instance: %s ', str(host), str(instance))
                    TargetLogger.info('New data: '+ str(target))
                    TargetLogger.info('Old data: '+ str(row))

                    TargetLogger.info('Old container: %s New container: %s ', oldContainer, Container)

                    # Pass data to fill a query placeholder and let Psycopg perform
                    # the correct conversion (no more SQL injections!)
                    update_cursor = postgres_conn.cursor()

                    try:
                        update_cursor.execute("""
                        UPDATE public.dbc_target 
                           set DBCreatedDate=%s, DBID=%s, Version=%s, ArchiveLogMode=%s, Status=%s, Role=%s, Container=%s,
                               HomeDirectory=%s, Vendor=%s, BlockSize=%s, in_oms=%s, hosttype=%s, dbora=%s
                         WHERE InventoryID=%s
                           and decommissioned is null; 
                        """, ( DBCreateDate, DBID, version, logMode, status, Role, Container, HomeDir, Vendor, DBBlockSize, \
                               In_OMS, hosttype, dbora, oldInventoryID ))
                        # Don't update owner until we can find a way to obtain it on all versions
          
                        # Make the changes to the database persistent
                        postgres_conn.commit()
   
                    except (psycopg2.DatabaseError, psycopg2.IntegrityError, psycopg2.DataError, psycopg2.InternalError)   as exc:
                        error, = exc.args
                        TargetLogger.error('Postgres DB Error: %s %s %s', str(host), str(instance), str(error))
                        result='UPDATE FAILED'
            
                    except Exception as exc:
                        error, = exc.args
                        TargetLogger.error('Postgres Exception: %s %s %s', str(host), str(instance), str(error))
                        result='UPDATE FAILED'

                    else:
                        result='UPDATED'


                else:
                   TargetLogger.info('Target known and no change in status: Host: %s  Instance: %s ', str(host), str(instance)) 
                   result='KNOWN'


        postgres_conn.close()

        return result
# ============================================================================
# END UpdateTarget
# ============================================================================


# ============================================================================
# ============================================================================
# ---------------------------   MAIN PROGRAM   -------------------------------
# ============================================================================
# ============================================================================


TargetLogger=StartLogging(LogLevel, Log_File)  # Log to File 

# ============================================================================
# Read through the DBList.txt file database by database
# Attempt to query that target and record the results
# ============================================================================
with open(target_file) as tf:
  for target in tf:
    target=target.strip()
    TargetLogger.info('Connecting to target: %s', str(target))
   
    # Try connecting to the database and get info if possible
    IsTarget, TargetInfo=PingTarget(target)

    if IsTarget: 
        TargetLogger.info('Target %s exists. Checking Inventory DB', str(target))
        result=UpdateTarget(TargetInfo)  # Update if it exists and there is new info 

    else:
        # This was not a valid reachable target
        TargetLogger.info('Target %s info should be corrected or removed from DBList.txt', str(target))
        TargetLogger.error('Target %s is not valid or not reachable:' , str(target)  )


