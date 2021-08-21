# Inventory

This repository contains scripts that are used to inventory and monitor IT resources such as servers and databases. Additional information and support can be found at https://pankratzmanagement.com

## Overview

This application has 3 operation modes:

1. ADD resources called "Targets". These are things you want to inventory and monitor such as servers and databases.
2. UPDATE targets.  Over time targets come and go, get upgraded, moved, etc..   Update will scan the targets for any changes in status.   
3. CHECK targets.   Perform various health and status checks on the targets in your inventory.   There are 3 custom filter options you can apply on any give "Check".   
  - TYPE:   	ie   OS, DB, Other
  - FREQUENCY:  ie  MONTHLY, DAILY, HOURLY, ADHOC, etc...
  - VENDOR:   	ie  Oracle, AIX, Solaris, DB2, SQL, Postgres, etc...

All information including the monitored targets and monitoring results are stored in a Postgres database.   The TARGETS table contains the relatively static information about the targets such as Name, Version, IP Address, Vendor, CreateDate, etc...
The checks you want to perform on the Targets are stored in the "CHECKLIST" table.
Finally, results of all the "Check" runs are stored in the CHECK_RESULTS table.

Grafana is recommended to be used for creating the dashboards and user interfaces for your monitoring results.  However, you can use the Postgres database directly with your own queries and reports.

### Application Dependencies
- Python 3 https://www.python.org/download/releases/3.0/
- psycopg2 https://www.psycopg.org/
- paramiko for OS monitoring http://www.paramiko.org/
- cx_Oracle for Oracle DB monitoring https://oracle.github.io/python-cx_Oracle/
- You will need either a common account and password or passwordless (ssh key) access to linux / un*x servers
- You will need a common account and password for each database vendor group.


### Description of files
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

### Database Schema
------------------------

<img alt="Pretty Picture goes here" src="tbdg" width="75%">

# Installation

## Installing from Github
- [ ] install pre-requisite python modules listed above
- [ ] download this repository and unzip **OR** clone directly from github


	cd "<your application directory>"
	git clone https://github.com/pilgrim53/DBInventory.git  
	

## Install as a Docker Container
- [ ] install Docker for your monitoring server ex)  https://www.digitalocean.com/community/tutorials/how-to-install-and-use-docker-on-ubuntu-20-04 
- [ ] complete all post install steps  ex)    https://docs.docker.com/engine/install/linux-postinstall/
- [ ] cd "<your application directory>"
	
	
        git clone https://github.com/pilgrim53/DBInventory.git  
        Docker-compose up -d --build![image](https://user-images.githubusercontent.com/28211619/130332929-659d07bb-1119-464c-9d80-b7f07f9b295b.png)

