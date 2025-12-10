# Step 1) Setting up the Python Environment

In order for some of the python modules to work. The NonProdInventory code must be run on Python 3.10 or higher. 
To create a virtual python 3.11 environment on caddld-590 follow these steps.

0. Log in fresh.  Do not try to do these steps from an existing log in.
1. cd [DEVEL_BASE]   (ex  /app/automation for caddla-978   or  ~/gitlab for personal )
2. (s)cp -r caddld-590:/BellDBC/Bell-ora-staging/python/modules/Python-3.11-Environment/* .
4. cd Python-3.11.4
5. ./configure --with-openssl=/usr/include/openssl   
6. make
7. vi Makefile  \# Change prefix from /opt/local to  !pwd !!!!
8. make install;  cd .. 
9. Create virtual environment:
    * Using vscode
        * Setup using vscode: https://code.visualstudio.com/docs/python/environments#
    * or use venv
        * Python-3.11.4/python -m venv [virtual_env]
10.  . [virtual_env]/bin/activate
11. \# mkdir [DEVEL_BASE]/modules; cd [DEVEL_BASE]/modules
13. \# (s)cp caddld-590:/BellDBC/Bell-ora-staging/python/modules/Python-3.11-Environment/* . 
14. pip install -r requirements.txt -f ./ --no-index

# Step 2) Set up your development git repository
1) Create your personal ssh key and upload it to your gitlab profile
   https://docs.gitlab.com/ee/user/ssh.html

2) cd to [DEVEL_BASE]   (ex /app/automation or  ~/gitlab )

3) git clone git@gitlab.bell.corp.bce.ca:it-infrastructure/ainonprodsupport/NonProdInventory.git



# Step 3) Perform UAT of your development work
1) Merge your developemnt branch into UAT 

2) ssh orac4i@caddld-590

3) cd automation/NonProdInventory

4) git checkout origin/UAT

5) git pull origin/UAT

6) vi .env    \#   Verify correct DB,  log directory, etc...

7)  \# gpg --gen-key   \# NOTE:  you can not do this from su and only do this ONCE! 

8)  vi uat_info   \# Add the passphrase you used to generate the key and update as necessary

9) gpg --output uat_info.inf --encrypt --recipient orac4i@caddld-590.belldev.dev.bce.ca uat_info
    NOTE:   To view the file after encrypting:  "gpg --decrypt uat_info.inf"
    
10)  . /home/orac4i/automation/Python-3.11-Environment/UAT_Env/bin/activate
