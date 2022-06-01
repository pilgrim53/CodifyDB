import paramiko  # Allows us to ssh to the target hosts
import cx_Oracle  # https://oracle.github.io/python-cx_Oracle/
import psycopg2  # https://pypi.org/project/psycopg2/
import psycopg2.extras  # This gives access to the psycopg2 error messages
import sys  # for some reason this is not included by default
from datetime import date, datetime  # for some reason this is not included by default
from decouple import config  # Allows us to read .env
from inv_logging import start_logging
# ===============================================================================
CODIFYWEB_DIR = config('CODIFYWEB_DIR')
sys.path.append(CODIFYWEB_DIR)
import inventory

# Set Environment and Global Variables
INV_USER = config('INV_USER')
INV_PWD = config('INV_PWD')
CODIFYDB_HOST = config('CODIFYDB_HOST')
CODIFYDB = config('CODIFYDB')
INVENTORYDB = "dbname=" + CODIFYDB + " user=" + INV_USER + " password=" + INV_PWD + " host=" + CODIFYDB_HOST
ORACLE_BASE = config('ORACLE_BASE')
ORACLE_HOME = config('ORACLE_HOME')
TNS_ADMIN = "/u01/app/oracle/DBTools/"
TARGET_FILE = "./discovery.txt"
conn_mode = cx_Oracle.DEFAULT_AUTH


def get_id(host, instance_name, target_logger):
    """
    Look up the Inventory_ID of a target based on the hostname and instance_name
    :param host:   the host or server name
    :param instance_name:   the instance_name of the target 
    :param target_logger:  
    :return: inventory_id: Returns the inventory_id of the target or 0 if not found
    """
    target_logger.debug("get_id with host = %s, instance_name = %s", host, instance_name)
    inventory_id = 0

    select_stmt = 'select nvl(inventory_id,0) from targets where hostname=\'' \
                  + host + '\' and instance_name=\'' + instance_name + '\' order by inventory_id '

    RC, result = inventory.exec_sql(select_stmt, 'ONE', target_logger)
    target_logger.info('Check %s %s returned: ''%s''', host, instance_name, result)
    if result is None:
        inventory_id = 0
    else:
        inventory_id = result[0]

    target_logger.debug("get_id returning inventory_id = %s", inventory_id)
    return inventory_id

# END get_id


def get_attribute(inventory_id, target, column, target_logger):
    """
    Returns the value of an inventory_id's attribute
    :param inventory_id:  The Inventory_ID of the object
    :param target:   The "target" associated with the ID
    :param column:   The column or "attribute" you want to retrieve
    :param target_logger:
    :return: value: the current value of the attribute "column" for the target
    """

    target_logger.debug("get_attribute with inventory_id=%s, target=%s, column=%s", inventory_id, target, column)
    query = 'select ' + column + ' from targets where inventory_id=' + str(inventory_id) + ''
    RC, value = inventory.exec_sql(query, 'ONE', target_logger)

    target_logger.debug("get_attribute returning value = %s", value)
    return value

# END get_attribute


def exec_sql(inventory_query, scale, target_logger):
    """
    Returns all the inventory_id's that match a query provided
    :param inventory_id:  The Inventory_ID of the object
    :param target:   The "target" associated with the ID
    :param column :  The column or "attribute" you want to retrieve
    :param target_logger:
    :return: value: 1 list or an array of lists.   RC=1
    :RC:            1 = Success, 0 = Fail
    """
    RC=1 
    target_logger.debug("Scale: %s, Inventory Query: %s", scale, inventory_query)

    # Connect to the Inventory DB
    try :
        inventory_conn = cx_Oracle.connect(INV_USER, INV_PWD, INVENTORYDB, mode=conn_mode)
        # inventory_conn = psycopg2.connect(INVENTORYDB)
        inventory_cursor = inventory_conn.cursor()

        # Get ALL the active targets
        inventory_cursor.execute(inventory_query)
        if scale == 'ALL' :
            query_result = inventory_cursor.fetchall()
        elif scale == 'ONE' : 
            query_result = inventory_cursor.fetchone()
        elif scale == 'EXEC' : 
            inventory_conn.commit()
            query_result = 1

        inventory_conn.close()

    except cx_Oracle.DatabaseError as exc:
        error, = exc.args
        target_logger.error("DatabaseError-Code: %s %s ", error.code, error.message)
        RC=0

    if not query_result : 
        RC=0

    target_logger.debug("Query result: %s", query_result)

    return RC, query_result


def add_results(inventory_id, check_result, column_name, target_logger):
    """
    Insert the check results into the inventory database. Outputs single entry into CheckResults table
    :param inventory_id:
    :param check_result:
    :param column_name: Column name for Check results to be stored
    :param target_logger:
    """
    target_logger.debug("Insert check result: %s into %s for ID: %s", check_result, column_name, inventory_id)
    inventory_conn = cx_Oracle.connect(INV_USER, INV_PWD, INVENTORYDB, mode=conn_mode)
    # postgres_insert_connection = psycopg2.connect(INVENTORYDB)
    insert_cursor = inventory_conn.cursor()
    check_date = datetime.now()
    insert_stmt = 'INSERT INTO check_results (inventory_id, check_date, check_result, check_column) \
                    VALUES ( ' + str(inventory_id) + ', to_timestamp(\'' + str(check_date) + '\',\'YYYY-MM-DD HH24:MI:SS.FF\')' ', \'' \
                             +  check_result + '\', \'' + column_name + '\')' 

    # insert_stmt = f"{insert_stmt.format(inventory_id, check_date, check_result, column_name)}"
    target_logger.debug("Insert Statement: %s ", insert_stmt)


    # Pass data to fill a query placeholders and let Psycopg perform
    # the correct conversion (no more SQL injections!)
    try:
        insert_cursor.execute(insert_stmt)

    except psycopg2.Error as exc:
        error, = exc.args
        target_logger.error("Data Exception: %s ", error)

    except cx_Oracle.DatabaseError as exc:
        error, = exc.args
        target_logger.error("Data Exception: %s ", error)

    else:
        target_logger.info("Result added: %s  %s  %s  %s", inventory_id, column_name, check_result, check_date)

        # Make the changes to the database persistent
        inventory_conn.commit()

    finally:
        inventory_conn.close()

    return 0

# END add_results