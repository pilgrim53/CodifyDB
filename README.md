# CodifyDB

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
- Django for Application Web Interface  https://www.djangoproject.com/start/overview/ 
- You will need either a common account and password or passwordless (ssh key) access to linux / un*x servers
- You will need a common account and password for each database vendor group.


### Database Schema
------------------------

<img alt="Pretty Picture goes here" src="tbdg" width="75%">

# Installation

## Installing from Github
- [ ] install pre-requisite python modules listed above
- [ ] download this repository and unzip **OR** clone directly from github

```
cd <your application directory>
cd to working area   

#=================================
# Use of a virtual environment is helpful for development but not required.
python3 -m venv .     #  This is only for the FIRST time
source  bin/activate
# End of virtual environment steps
#=================================
# More FIRST TIME  ONLY commands
python -m pip install --upgrade pip 
python -m pip instal cx_Oracle
python -m pip install psycopg2
python -m pip install django
( alternatively get the whl and python setup.py build; python setup.py install
# End of first time only commands
NOTE:  If you are trying to RE-CREATE a first time deployment you may need to FORCEFULLY 
       remove the database docker volumes that were previously used
docker volume ls     #  ( or use Docker Desktop GUI Volumes tab )
#=================================
git clone  https://github.com/pilgrim53/CodifyDB.git 
cd CodifyDB   #  ie  <CodifyBase>
cd CodifyWeb 
use your text editor to edit  ".env"  to set the values for your environment
# make sure docker is running
docker-compose up -d --build
# this will create the CodifyDB Postgres database using a Postgres Docker image and initializing it with 0_init_PostgresDB.sh
Now, check the database with adminer, PGAdmin or SQL Developer - Should have an empty CodifyDB 
cd ..
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser  # one time only
python manage.py runserver

# ===========================
# Add Indices and data
# ===========================
cd CodifyWeb 
docker-compose exec db /bin/bash
cd /code/postgresdb
./1_Init_CodifyDB.sh
exit # postgres user
exit # root user
cd ..
# =============================
```	

# Populate some targets
python scan_targets.py -t Database -a 
# Alternatively go to http://localhost:8000/   and hit the "Add"  button

## Install as a Docker Container
- [ ] install Docker for your monitoring server ex)  https://www.digitalocean.com/community/tutorials/how-to-install-and-use-docker-on-ubuntu-20-04 
- [ ] complete all post install steps  ex)    https://docs.docker.com/engine/install/linux-postinstall/
- [ ] install from GitHub (above) 


## Configure your instance
 - set postgres password
 - update .env
 - etc...
 
 # Using the Inventory Application
 
 ## Add Targets
  - do these things
  
 ## Update Targets
  - do these other things
 
 ## Check Targets
  - do still more things

 # Getting additional help or support
