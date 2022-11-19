#!/bin/bash
sec_secret_storage_loc="/my_secret_files"

echo "Script for testing and running naked.py"
echo "------------------------------------------------"

echo "Checking if config.ini exists in the current working dir -->"
if test -f "config.ini"; then
    echo "exists"
else
	echo "Copying config file from secure secret storage"
	cp $HOME$sec_secret_storage_loc/config.ini .
	if [ $? -eq 0 ]; then echo "OK"; else echo "Problem copying config.ini file"; exit 1; fi
fi
echo "------------------------------------------------"

echo "Getting python3 executable loc"
python_exec_loc=$(which python3)
if [ $? -eq 0 ]; then echo "OK"; else echo "Problem getting python3 exec location"; exit 1; fi
echo "$python_exec_loc"
echo "------------------------------------------------"

echo "Running config test"
$python_exec_loc test_config.py
if [ $? -eq 0 ]; then echo "OK"; else echo "Configuration test FAILED"; exit 1; fi
echo "------------------------------------------------"

echo "Running asteroid worker test"
$python_exec_loc test_naked.py
if [ $? -eq 0 ]; then echo "OK"; else echo "Worker test FAILED"; exit 1; fi
echo "------------------------------------------------"

echo "Running DB migrations"
$python_exec_loc migrate_db.py
if [ $? -eq 0 ]; then echo "OK"; else echo "DB migration FAILED"; exit 1; fi
echo "------------------------------------------------"

echo "Running DB migration test"
$python_exec_loc test_naked_original.py
if [ $? -eq 0 ]; then echo "OK"; else echo "DB migration test FAILED"; exit 1; fi
echo "------------------------------------------------"

echo "ALL TEST OK"
echo "Running asteroid worker:"
$python_exec_loc naked.py