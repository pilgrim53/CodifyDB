# ============================================================================
# Import all the external Python modules that we need
# ============================================================================
import logging            # https://docs.python.org/3/library/logging.html

# ============================================================================
# Define Functions
# ============================================================================

def StartLogging(Log_Level, Log_File, Log_Name):
    logging.basicConfig(filename=Log_File, level=Log_Level)
    logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
    TargetLogger=logging.getLogger(Log_Name)
    TargetLogger.setLevel(Log_Level)

    # Create a console handler
    ch = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    TargetLogger.addHandler(ch)

    return TargetLogger
    # End StartLogging

# ============================================================================
# Logging examples
# ============================================================================
# logging.debug('This should go to the log file.')
# logging.info('So should this')
# logging.warning('And this, too')
# logging.error('And non-ASCII stuff, too, like Øresund and Malmö')
# ============================================================================