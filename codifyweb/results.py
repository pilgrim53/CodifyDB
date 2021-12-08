import psycopg2  # https://pypi.org/project/psycopg2/
import psycopg2.extras  # This gives access to the psycopg2 error messages
# from numpy import asarray # convert sql result tuples to python arrays
from datetime import date, datetime  # for some reason this is not included by default
from decouple import config  # Allows us to read .env

# Set  Environment and Global Variables
INV_USER = config('INV_USER')
INV_PWD = config('INV_PWD')
CODIFYDB_HOST = config('CODIFYDB_HOST')
CODIFYDB = config('CODIFYDB')
INVENTORYDB = "dbname=" + CODIFYDB + " user=" + INV_USER + " password=" + INV_PWD + " host=" + CODIFYDB_HOST


def add(inventory_id, check_result, column_name, target_logger):
    """
    Insert the check results into the inventory database. Outputs single entry into CheckResults table
    :param inventory_id:
    :param check_result:
    :param column_name: Column name for Check results to be stored
    :param target_logger:
    """
    target_logger.debug("Insert check result: %s into %s for ID: %s", check_result, column_name, inventory_id)
    postgres_insert_connection = psycopg2.connect(INVENTORYDB)
    insert_cursor = postgres_insert_connection.cursor()
    insert_statement = "INSERT INTO check_results (inventory_id, check_date, check_result, check_column) \
                          VALUES ( %s, %s, %s, %s ); "
    check_date = datetime.now()

    # Pass data to fill a query placeholders and let Psycopg perform
    # the correct conversion (no more SQL injections!)
    try:
        insert_cursor.execute(insert_statement, (inventory_id, check_date, check_result, column_name))

    except psycopg2.Error as exc:
        error, = exc.args
        target_logger.error("Data Exception: %s ", error)

    else:
        target_logger.info("Result added: %s  %s  %s  %s", inventory_id, column_name, check_result, check_date)

        # Make the changes to the database persistent
        postgres_insert_connection.commit()

    finally:
        postgres_insert_connection.close()

    return 0

# END add

