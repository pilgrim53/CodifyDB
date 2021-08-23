# ============================================================================
# Import all the external Python modules that we need
# ============================================================================
import psycopg2           # https://pypi.org/project/psycopg2/
import psycopg2.extras    # This gives access to the psycopg2 error messages
# from numpy import asarray # convert sql result tuples to python arrays
from datetime import date, datetime # for some reason this is not included by default
from decouple  import config     # Allows us to read .env

INV_USER = config('INV_USER')
INV_PWD  = config('INV_PWD')
INVENTORYDB = "dbname=testdb user="+INV_USER+" password="+INV_PWD+" host=caddld-498.belldev.dev.bce.ca"

# ============================================================================
# Function:     add_result
# Description:  Insert the check results into the inventory database
# Input:        Check results and column_name for the results to be stored
# Ouptut:       Single entry into CheckResults table
# ============================================================================

def add_result(ID, check_result, column_name, TargetLogger):
    TargetLogger.debug("Insert check result: %s into %s for ID: %s", check_result, column_name, ID)
    postgres_insert_connection = psycopg2.connect(INVENTORYDB)
    insert_cursor = postgres_insert_connection.cursor()
    insert_statement  =  "INSERT INTO checkresults (inventoryid, checkdate, check_result, check_column) \
                          VALUES ( %s, %s, %s, %s ); "
    # insert_statement  =  "INSERT INTO checkresults (inventoryid, checkdate," \
    #                      + column_name + " ) VALUES ( %s, %s, %s); "
    check_date = datetime.now()

    # Pass data to fill a query placeholders and let Psycopg perform
    # the correct conversion (no more SQL injections!)
    try:
        insert_cursor.execute(insert_statement, ( ID, check_date, check_result, column_name ))

    except psycopg2.Error as exc:
        error, = exc.args
        TargetLogger.error("Data Exception: %s ", error) 

    else:
        TargetLogger.info("Result added: %s  %s  %s  %s", ID, column_name, check_result, check_date) 

        # Make the changes to the database persistent
        postgres_insert_connection.commit()

    finally:
        postgres_insert_connection.close()

    return 0

# ============================================================================
# END add_result
# ============================================================================
