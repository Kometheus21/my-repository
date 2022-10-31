from naked import *
import os

print("Database migration test")

# Testing if configuration file exists on disk in the current working directory
print("----------")
print("Checking if config file exists -->")
assert os.path.isfile("config.ini") == True
print("OK")
print("----------")

# Opening the configuration file
config = ConfigParser()
config.read('config.ini')

# Checking if possible to connect to MySQL with the existing config options
print("Checking if it is possible to connect to MYSQL with the given config options -->")
mysql_config_mysql_host = config.get('mysql_config', 'mysql_host')
mysql_config_mysql_db = config.get('mysql_config', 'mysql_db')
mysql_config_mysql_user = config.get('mysql_config', 'mysql_user')
mysql_config_mysql_pass = config.get('mysql_config', 'mysql_pass')
connection = mysql.connector.connect(host=mysql_config_mysql_host, database=mysql_config_mysql_db, user=mysql_config_mysql_user, password=mysql_config_mysql_pass)
assert connection.is_connected() == True
print("OK")
print("----------")

# Checking if there have been any migrations done
print("Checking if there have been any migrations done -->")
cursor = connection.cursor()
result  = cursor.execute("SELECT count(*) FROM migrations WHERE `id` > 0")
records = cursor.fetchall()
assert records[0][0] > 0
print("OK")
print("----------")

print("Database migration test DONE -> All OK")
print("----------")