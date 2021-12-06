import paramiko  # Allows us to ssh to the target hosts
import cx_Oracle  # https://oracle.github.io/python-cx_Oracle/
import psycopg2  # https://pypi.org/project/psycopg2/
import psycopg2.extras  # This gives access to the psycopg2 error messages
import sys  # for some reason this is not included by default
import logging  # https://docs.python.org/3/library/logging.html
import threading  # Allows us to time and kill hung db connections
# from numpy import asarray # convert sql result tuples to python arrays
from datetime import date, datetime  # for some reason this is not included by default
from decouple import config  # Allows us to read .env
import socket
import os
from .inv_logging import start_logging
from . import results

# Set DBTools Environment and Global Variables
DBC_USER = config('DBC_USER')
DBC_PWD = config('DBC_PWD')
INV_USER = config('INV_USER')
INV_PWD = config('INV_PWD')
CODIFYDB_HOST = config('CODIFYDB_HOST')
CODIFYDB = config('CODIFYDB')
INVENTORYDB = "dbname=" + CODIFYDB + " user=" + INV_USER + " password=" + INV_PWD + " host=" + CODIFYDB_HOST
ORACLE_BASE = config('ORACLE_BASE')
ORACLE_HOME = config('ORACLE_HOME')
TNS_ADMIN = "/u01/app/oracle/DBTools/"
TARGET_FILE = "./discovery.txt"


def get_id(host, instance_name, target_logger):
    """
    Creates the initial Target entry in the Target table
    :param host:
    :param instance_name:
    :param target_logger:
    :return: inventory_id: Returns the inventory_id of the target or 0 if not found
    """

    inventory_id = 0

    postgres_conn = psycopg2.connect(INVENTORYDB)

    select_cursor = postgres_conn.cursor()
    select_stmt = 'select coalesce(inventory_id,0) from public.target where hostname=\'' \
                  + host + '\' and instance_name=\'' + instance_name + '\' order by inventory_id '

    try:
        select_cursor.execute(select_stmt)
        result = select_cursor.fetchone()
        target_logger.info('Check %s %s returned: ''%s''', host, instance_name, result)
        if result is None:
            inventory_id = 0
        else:
            inventory_id = result[0]

        target_logger.debug('Check for existing target returned: %s', inventory_id)

    except (psycopg2.DatabaseError, psycopg2.IntegrityError, psycopg2.DataError, psycopg2.InternalError) as exc:
        error, = exc.args
        target_logger.error('Error checking existence of target: %s %s %s ', str(host), str(instance_name), str(error))

    postgres_conn.close()

    return inventory_id

# END get_id


def get_attribute(inventory_id, target, column, target_logger):
    """
    Takes a target and an OS check and first obtains the FID and home_dir for the call to the check_os_target routine
    :param inventory_id:
    :param target:
    :param column:
    :param target_logger:
    :return: value: the current value of the attribute "column" for the target
    """

    value = ''
    query = 'select ' + column + ' from target where inventory_id=' + str(inventory_id) + ''

    try:
        postgres_conn = psycopg2.connect(INVENTORYDB)
        select_cursor = postgres_conn.cursor()
        # Get just the info about the target for comparison
        select_cursor.execute(query)
        value = select_cursor.fetchone()
        value = value[0].strip()

    except cx_Oracle.DatabaseError as exc:
        # If there was a database error we need the ORA-##### error
        error, = exc.args
        oracle_error = str(error.code)
        target_logger.error('Target: %s   Status: ORA- %s  Message: %s', str(target), oracle_error, str(error))

    return value

# END get_attribute
