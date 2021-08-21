Inventory 
=========

This repository contains scripts to inventory, and monitor IT resources
such as servers and databases. Additional information and support can 
be found at https://pankratzmanagement.com

Overview
--------

This application has 3 main operation modes:

1. ADD resources called "Targets". These are things you want to inventory and monitor such as servers and databases.
2. UPDATE targets.  Over time targets come and go, get upgraded, moved, etc..   Update will scan the targets for any changes in status.   
3. CHECK targets.   Perform various health and status checks on the targets in your inventory.   There are 3 filters you can apply on any give "Check".   
  - TYPE:   	ie   OS, DB, Other
  - FREQUENCY:  ie  MONTHLY, DAILY, HOURLY, ADHOC, etc...
  - VENDOR:   	ie  Oracle, AIX, Solaris, DB2, SQL, Postgres, etc...

Targets are stored in a Postgres database.   The TARGETS table contains the relatively static information
about the targets such as Name, Version, IP Address, Vendor, CreateDate, etc...

The checks you want to perform on the Targets are stored in the "CHECKLIST" table.

Finally, results of all the "Check" runs are stored in the CHECK_RESULTS table.

Grafana is used and recommended for creating the dashboards and user interfaces for your monitoring results.


Application Dependencies
------------------------
- Python 3
- psycopg2 https://www.psycopg.org/
- paramiko for OS monitoring http://www.paramiko.org/
- cx_Oracle for Oracle DB monitoring https://oracle.github.io/python-cx_Oracle/
- You will need either a common account and password or passwordless (ssh key) access to linux / un*x servers
- You will need a common account and password for each database vendor group.


Description of files
--------------------

Non-Python files:

filename                  |  description
--------------------------|------------------------------------------------------------------------------------
README.md                 |  Text file (markdown format) description of the project.
dockerfile                |  Rapid deployment via Docker container


Python scripts files:

filename                  |  description
--------------------------|------------------------------------------------------------------------------------
scan_targets.py           |  This is the program for building, adding, updating targets in your Inventory
check_targets.py          |  This is the program used to perform monitoring checks on your Inventory


Python modules:

filename                  |  description
--------------------------|------------------------------------------------------------------------------------
Inv_Logging.py            |  Handle all the application logging output to files.
Targets.py                |  Module containing all Target methods (add, update, get, etc...)

How it all fits together
------------------------

<img alt="Pretty Picture goes here" src="docs/oeis-tools.png" width="75%">

