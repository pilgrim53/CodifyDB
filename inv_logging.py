import logging  # https://docs.python.org/3/library/logging.html


def start_logging(log_level, log_file, log_name, log_to_console):

    # Change console_log_level to desired level if different from file log level
    console_log_level = log_level

    target_logger = logging.getLogger(log_name)
    target_logger.setLevel(log_level)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    target_logger.addHandler(file_handler)

    # Create a console handler
    if log_to_console == "ON":
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        ch.setLevel(console_log_level)
        target_logger.addHandler(ch)



    # logging.basicConfig(filename=log_file, level=log_level)
    # logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
    # target_logger = logging.getLogger(log_name)
    # target_logger.setLevel(log_level)
    #
    # # Create a console handler
    # ch = logging.StreamHandler()
    # formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # ch.setFormatter(formatter)
    # target_logger.addHandler(ch)

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
