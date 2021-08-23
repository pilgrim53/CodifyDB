
# ============================================================================
# Import all the external Python modules that we need
# ============================================================================
import paramiko                  # Allows us to ssh to the Database Servers
import threading                 # Allows us to time and kill hung db connections
import add_result
from Inv_Logging import StartLogging
from datetime  import datetime
from datetime  import date
from check_oms import CheckOMS   # Allows us to query the OEM Dev instance
from decouple  import config     # Allows us to read .env
# ============================================================================

# ============================================================================
# Set DBTools Environment and Global Variables
# ============================================================================
# N/A

# ============================================================================
#    check_os_target    
# ============================================================================
def check_os_target(ID, owner, host, homedir, check, result_column, TargetLogger):
    result=''
    ssh_connection = paramiko.SSHClient()
    ssh_connection.load_system_host_keys()
    ssh_connection.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    timer = threading.Timer(90,ssh_connection.close)
    timer.start()    # start counting right before connecting to the database

    try:
        TargetLogger.info("Connecting to %s as %s ", host, owner)
        ssh_connection.connect(host, 22, owner) 

    except paramiko.ssh_exception.AuthenticationException:
        TargetLogger.error("Authentication failed, Host: %s    Owner: %s", host, owner)
        result='ssh_exception.AuthenticationException'
        
    except paramiko.ssh_exception.BadHostKeyException as badHostKeyException:
        TargetLogger.error("Unable to verify server's host key: %s", badHostKeyException)
        result='ssh_exception.BadHostKeyException'

    except    paramiko.ssh_exception.SSHException as sshException:
        TargetLogger.error("Unable to establish SSH connection: %s",    sshException)
        result='ssh_exception.SSHException'

    except Exception as sshException:
        TargetLogger.error("General Exception: %s ",    sshException)
        result='General exception running os command'

    else:
        try: 
            if result_column == 'swrelease':
               check = homedir + '/OPatch/' + check

            TargetLogger.info("Running %s as %s on %s ", check, owner, host)
            stdin, stdout, stderr = ssh_connection.exec_command(check, get_pty=True)

            result_row = stdout.readlines()
            result_err = stderr.readlines()
            TargetLogger.info("OS Check stdout: %s ", str(result_row) )
            TargetLogger.info("OS Check Errors: %s ", str(result_err) )

            if result_row :
                result=str(result_row[0].strip())
                TargetLogger.info("InventoryID: %s result: %s result_column: %s ", \
                            ID, result, result_column)   
            else :
                TargetLogger.info("OS Check Errors: %s ", result_err )

            timer.cancel()    # cancel the connection thread if it's still alive after 30 seconds

        except  Exception as sshException:
            TargetLogger.error("Unable to run: %s on host: %s as %s Result: %s",   \
                               check, host, owner, sshException)
            
    finally:
        ssh_connection.close() 

    return result

# ============================================================================
#    End check_os_target    
# ============================================================================
