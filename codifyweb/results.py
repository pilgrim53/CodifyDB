import cx_Oracle
import psycopg2  # https://pypi.org/project/psycopg2/
import psycopg2.extras  # This gives access to the psycopg2 error messages
# from numpy import asarray # convert sql result tuples to python arrays
from datetime import date, datetime  # for some reason this is not included by default
from decouple import config  # Allows us to read .env

# Set DBTools Environment and Global Variables
INV_USER = config('INV_USER')
INV_PWD = config('INV_PWD')
CODIFYDB_HOST = config('CODIFYDB_HOST')
CODIFYDB = config('CODIFYDB')
CODIFY_PORT = config('CODIFY_PORT')
INVENTORYDB = cx_Oracle.makedsn(CODIFYDB_HOST, CODIFY_PORT, service_name=CODIFYDB)
conn_mode = cx_Oracle.DEFAULT_AUTH


def add(inventory_id, check_result, column_name, target_logger):
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

# END add

