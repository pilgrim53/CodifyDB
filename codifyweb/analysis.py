import concurrent.futures # allows us to do multiple checks at once
import sys
import argparse # Allows us to interact with the o/s
from datetime import date
from time import sleep
from decouple import config  # Allows us to read .env
import sklearn

# =====================================================
from inv_logging import start_logging
import pandas as pd
from inventory import Inventory

log_dir = config('LOG_DIR')
log_name = "Analysis"
log_file = log_dir + log_name + "_" + str(date.today()) + ".log"
log_level = 'INFO'
log_to_console = 'OFF'

# Log to File
target_logger = start_logging(log_level, log_file, log_name, log_to_console)

target_logger.info("Running analysis.py")

inventory = Inventory(target_logger)
rc = inventory.connect()

all_targets=inventory.get_targets('Server','ALL',1,999999)
server_df = pd.DataFrame([x.as_dict() for x in all_targets])

all_targets=inventory.get_targets('Database','ALL',1,999999)
database_df = pd.DataFrame([x.as_dict() for x in all_targets])
# print(dataframe)
# print(str(dataframe))

# =======================================================
# PLOTTING (requires matplotlib)
#  dataframe.pivot(columns='hostname',values='version')
#  plot function requires matplotlib
#  we can do this directly in APEX if needed
#  dataframe.plot(kind = 'scatter', x='hostname',y = 'version')
# =======================================================

print('')
print('Server Data')
server_df.describe()
server_df.info()
print(server_df)

print('')
print('Database Data')
database_df.describe()
database_df.info()
print(database_df)

print('')
print('Database Data Description')
print(database_df.describe())

num_cols=['inventory_id','version']

corr_df = database_df[num_cols]
pd.to_numeric(corr_df['version'], errors='coerce')
corr_df = corr_df.fillna(0)
corr_df.info()


print('')
print('Database Versions')
print(corr_df)

print('')
print('Database Version Correlation')
print(corr_df.corr( numeric_only = True ))
print(corr_df.describe())

"""
Data columns (total 13 columns):
 #   Column         Non-Null Count  Dtype
---  ------         --------------  -----
 0   inventory_id   15 non-null     int64
 1   hostname       15 non-null     object
 2   instance_name  15 non-null     object
 3   vendor         15 non-null     object
 4   version        13 non-null     object
 5   sub_type       15 non-null     object
 6   owner          15 non-null     object
 7   home_dir       14 non-null     object
 8   target_type    15 non-null     object
 9   container      15 non-null     object
 10  serial_number  15 non-null     object
 11  status         15 non-null     object
 12  port           15 non-null     int64   """


X = database_df
y = database_df.version

from sklearn.tree import DecisionTreeRegressor
# from sklearn.tree import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

#specify the model.
#For model reproducibility, set a numeric value for random_state when specifying the model
db_model = DecisionTreeRegressor(random_state=1)




from sklearn.ensemble import RandomForestClassifier
features = [ "vendor", "sub_type", "owner", "target_type"]
for col in features:
  database_df[col] = database_df[col].astype('str')

print(database_df[features])

X = pd.get_dummies(database_df[features])
# X_test = pd.get_dummies(test_data[features])

#model = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=1)
model = RandomForestClassifier()
model.fit(X, y)
predictions = model.predict(X)

print('')
print('Prediction of the database version from training data')
output = pd.DataFrame({'inventory_id': database_df.inventory_id, 'version': predictions})
print(output)

print('')
print('Actual database version')
print(corr_df)


import subprocess
import re

def extract_fourth_field(input_string):
    """
    Extracts the fourth field from lines containing "/arch" in a string.  Returns the first match or None.

    Args:
        input_string: The input string to process.

    Returns:
        The fourth field (string) if found, otherwise None.
    """
    lines = input_string.splitlines()
    for line in lines:
        if "/arch/" in line:
            fields = line.split()
            if len(fields) >= 4:
                return fields[3]
    return None









try:
    # Get input from a file (replace 'input.txt' with your file)
    with open('input.txt', 'r') as f:
        input_data = f.read()
    result = extract_fourth_field(input_data)

    #Get input from a command
    #result = extract_fourth_field(subprocess.check_output(['some', 'command']).decode())

    if result:
        print(result)
    else:
        print("No match found.")

except FileNotFoundError:
    print("Input file not found.")
except subprocess.CalledProcessError as e:
    print(f"Error executing command: {e}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")






