import psycopg2  # https://pypi.org/project/psycopg2/
import psycopg2.extras  # This gives access to the psycopg2 error messages
# from numpy import asarray # convert sql result tuples to python arrays
from datetime import date, datetime  # for some reason this is not included by default
from decouple import config  # Allows us to read .env
import inventory

def add(inventory_id, check_result, column_name, target_logger):
    """
    Insert the check results into the inventory database. Outputs single entry into CheckResults table
    :param inventory_id:
    :param check_result:
    :param column_name: Column name for Check results to be stored
    :param target_logger:
    """
 
    insert_statement = "INSERT INTO check_results (inventory_id, check_date, check_result, check_column) \
                          VALUES ( {}, \'{}\', \'{}\', \'{}\' ); "

    check_date = datetime.now()
    insert_statement = f"{insert_statement.format(inventory_id, check_date, check_result, column_name)}"

    result=inventory.exec_sql(insert_statement, 'EXEC', target_logger)

    return result

# END add