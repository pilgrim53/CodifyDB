# ============================================================================
# Import all the external Python modules that we need
# ============================================================================
import logging  # https://docs.python.org/3/library/logging.html


# ============================================================================
# Define Functions
# ============================================================================

def start_logging(log_level, log_file, log_name):
    logging.basicConfig(filename=log_file, level=log_level)
    logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
    target_logger = logging.getLogger(log_name)
    target_logger.setLevel(log_level)

    # Create a console handler
    ch = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    target_logger.addHandler(ch)

    return target_logger
    # End StartLogging

# ============================================================================
# Logging examples
# ============================================================================
# logging.debug('This should go to the log file.')
# logging.info('So should this')
# logging.warning('And this, too')
# logging.error('And non-ASCII stuff, too, like Øresund and Malmö')
# ============================================================================
