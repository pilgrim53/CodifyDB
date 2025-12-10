from datetime import datetime
import os
from decouple import config  # Allows us to read .env
import sys, argparse  # Allows us to interact with the o/s
import traceback    # Allows us to get detailed exception info
from time import sleep
from inventory import Inventory
from target import Target
from inv_logging import start_logging  # Allows us to log to a file

def main():

    log_dir = config('LOG_DIR')
    log_name = "Add_groups"
    log_file = log_dir + log_name + "_" + str(datetime.now().strftime('%Y-%m-%d_%H-%M-%S')) + ".log"
    log_level = 'INFO'
    log_to_console = 'ON'
    
    # Log to File   
    groups_logger = start_logging(log_level, log_file, log_name, log_to_console)

    inventory = Inventory(groups_logger)
    rc = inventory.connect()
    linux_group_query ="""Select distinct check_result from Server_team.Check_results 
                    where check_column='sssd_allow_groups' And check_date > ( sysdate - 5)"""
    rc , unix_group_result = inventory.exec_sql(linux_group_query, 'ALL') # returns list of tuples of the groups e.g [(group1 group2 group3,), (group8 group9,), ...])
    
    # tuple handling - move the tuples to a list
    unix_groups = [tup_group[0].split() for tup_group in unix_group_result if tup_group[0] is not None] # returns a list of lists [[group1, group2, group3], [group8], ...]
    unix_posted_groups = get_groups(inventory, groups_logger, 'UNIX')
    
    for group_list in unix_groups:
        for group in group_list:
            group = group.lower()
            add_group(inventory,groups_logger,group,'UNIX',unix_posted_groups)
            unix_posted_groups = get_groups(inventory, groups_logger,'UNIX')
    # get the members of each group
    # get_members_command = f"getent group cloud20_admins | sed 's/.*[a-zA-Z0-9]://'"
    for grp in get_groups(inventory, groups_logger,'UNIX'):
        get_members_command = f"getent group {grp}"
        execute_command = (os.popen(get_members_command).read()).split(":")
        members = execute_command[3] if len(execute_command) == 4 and (execute_command[3] != '\n') else None
        groups_logger.debug(f"GROUP MEMBERS IN {grp}: {members}")  
        if members is not None: add_members(inventory, groups_logger, grp, members) 
        
    
    windows_group_query = """Select distinct check_result from Server_team.Check_results 
                    where check_column='remote_desktop_users' And check_date > ( sysdate - 5)"""
    rc, windows_group_result = inventory.exec_sql(windows_group_query, 'ALL')
    
    windows_groups = [win_tup_group[0].split('\r\n\r\n')[-1].split('\r\n') for win_tup_group in windows_group_result if win_tup_group[0] is not None]  
    windows_posted_group = get_groups(inventory, groups_logger, 'WINDOWS')
    
    for windows_group_list in windows_groups:
        windows_group_list.pop()
        if windows_group_list:
            windows_group_list.pop(0)
            for win_group in windows_group_list:
                add_group(inventory,groups_logger,win_group,'WINDOWS',windows_posted_group)
                windows_posted_group = get_groups(inventory, groups_logger, 'WINDOWS')
    
    for win_grp in get_groups(inventory, groups_logger,'WINDOWS'):
        no_domain_name = win_grp.split('\\')[-1]
        get_members_command = f"getent group {no_domain_name.lower()}"
        execute_command = (os.popen(get_members_command).read()).split(":")
        members = execute_command[3] if len(execute_command) == 4 and (execute_command[3] != '\n') else no_domain_name
        groups_logger.debug(f"GROUP MEMBERS IN {win_grp}: {members}")  
        if members is not None: add_members(inventory, groups_logger, win_grp, members) 
    inventory.disconnect()
    
def get_groups(inventory: Inventory, logger, vendor):
        logger.debug("Getting all groups already in table")
        posted_query =  f"Select name from Server_team.groups where VENDOR = \'{vendor}\'"
        rc , posted_result = inventory.exec_sql(posted_query, 'ALL') # returns list of tuples of groups already in apex
        posted_groups = [tup[0] for tup in posted_result]
        return posted_groups
    
def add_group(inventory: Inventory, logger, group, vendor, posted_group):
    if group in posted_group:
        logger.debug(f"GROUP: {group} - Already exists in table")
    else:
        insert_statement = f"insert into server_team.groups (name,vendor) values (\'{group}\', \'{vendor}\')"
        rc, sql_insert = inventory.exec_sql(insert_statement, 'EXEC')
        logger.info(f"Added {vendor} group {group} to the table")

def add_members(inventory: Inventory, logger, group, members):
    update_sql=(f"update server_team.groups set members = \',{members.strip()},\' where name = \'{group}\'") #commas between the members helps getting the correct user when querying in Jira IQL
    status=inventory.exec_sql(update_sql,'EXEC')
    logger.info(f"Members added to {group}")
    
if __name__ == "__main__":
    main()   