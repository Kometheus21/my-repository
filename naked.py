import requests
import json
import datetime
import time
import yaml
import logging
import logging.config
import mysql.connector

from datetime import datetime
from configparser import ConfigParser
from mysql.connector import Error

# Loading logging configuration
with open('./log_worker.yaml', 'r') as stream:
	log_config = yaml.safe_load(stream)

logging.config.dictConfig(log_config)

# Creating logger
logger = logging.getLogger('root')

logger.info('Asteroid processing service')

# Initiating and reading config values
logger.info('Loading configuration from file')

# Reads the config.ini file and assigns the NASA API and mysql information stored in it to variables
try:
	config = ConfigParser()
	config.read('config.ini')

	nasa_api_key = config.get('nasa', 'api_key')
	nasa_api_url = config.get('nasa', 'api_url')
	
	mysql_config_mysql_host = config.get('mysql_config', 'mysql_host')
	mysql_config_mysql_db = config.get('mysql_config', 'mysql_db')
	mysql_config_mysql_user = config.get('mysql_config', 'mysql_user')
	mysql_config_mysql_pass = config.get('mysql_config', 'mysql_pass')

except:
	logger.exception('')
logger.info('DONE')

# Connects to the database
def init_db():
	global connection
	connection = mysql.connector.connect(host=mysql_config_mysql_host, database=mysql_config_mysql_db, user=mysql_config_mysql_user, password=mysql_config_mysql_pass)

def get_cursor():
	global connection
	try:
		connection.ping(reconnect=True, attempts=1, delay=0)
		connection.commit()
	except mysql.connector.Error as err:
		logger.error("No connection to db " + str(err))
		connection = init_db()
		connection.commit()
	return connection.cursor()

# Check if asteroid exists in db
def mysql_check_if_ast_exists_in_db(request_day, ast_id):
	records = []
	cursor = get_cursor()
	try:
		cursor = connection.cursor()
		result  = cursor.execute("SELECT count(*) FROM ast_daily WHERE `create_date` = '" + str(request_day) + "' AND `ast_id` = '" + str(ast_id) + "'")
		records = cursor.fetchall()
		connection.commit()
	except Error as e :
		logger.error("SELECT count(*) FROM ast_daily WHERE `create_date` = '" + str(request_day) + "' AND `ast_id` = '" + str(ast_id) + "'")
		logger.error('Problem checking if asteroid exists: ' + str(e))
		pass
	return records[0][0]

# Asteroid value insert
def mysql_insert_ast_into_db(create_date, hazardous, name, url, diam_min, diam_max, ts, dt_utc, dt_local, speed, distance, ast_id):
	cursor = get_cursor()
	try:
		cursor = connection.cursor()
		result  = cursor.execute( "INSERT INTO `ast_daily` (`create_date`, `hazardous`, `name`, `url`, `diam_min`, `diam_max`, `ts`, `dt_utc`, `dt_local`, `speed`, `distance`, `ast_id`) VALUES ('" + str(create_date) + "', '" + str(hazardous) + "', '" + str(name) + "', '" + str(url) + "', '" + str(diam_min) + "', '" + str(diam_max) + "', '" + str(ts) + "', '" + str(dt_utc) + "', '" + str(dt_local) + "', '" + str(speed) + "', '" + str(distance) + "', '" + str(ast_id) + "')")
		connection.commit()
	except Error as e :
		logger.error( "INSERT INTO `ast_daily` (`create_date`, `hazardous`, `name`, `url`, `diam_min`, `diam_max`, `ts`, `dt_utc`, `dt_local`, `speed`, `distance`, `ast_id`) VALUES ('" + str(create_date) + "', '" + str(hazardous) + "', '" + str(name) + "', '" + str(url) + "', '" + str(diam_min) + "', '" + str(diam_max) + "', '" + str(ts) + "', '" + str(dt_utc) + "', '" + str(dt_local) + "', '" + str(speed) + "', '" + str(distance) + "', '" + str(ast_id) + "')")
		logger.error('Problem inserting asteroid values into DB: ' + str(e))
		pass

# Checks if the asteroids in the array are already in the database and adds them if they arent
def push_asteroids_arrays_to_db(request_day, ast_array, hazardous):
	for asteroid in ast_array:
		if mysql_check_if_ast_exists_in_db(request_day, asteroid[9]) == 0:
			logger.debug("Asteroid NOT in db")
			mysql_insert_ast_into_db(request_day, hazardous, asteroid[0], asteroid[1], asteroid[2], asteroid[3], asteroid[4], asteroid[5], asteroid[6], asteroid[7], asteroid[8], asteroid[9])
		else:
			logger.debug("Asteroid already IN DB")

# Sorts the asteroids by their miss distance in ascending order
def sort_ast_by_pass_dist(ast_arr):
	if len(ast_arr) > 0:
		min_len = 1000000
		max_len = -1
		for val in ast_arr:
			if len(val) > max_len:
				max_len = len(val)
			if len(val) < min_len:
				min_len = len(val)
		if min_len == max_len and min_len >= 10:
			ast_arr.sort(key = lambda x: x[8], reverse=False)
			return ast_arr
		else:
			return []
	else:
		return []

if __name__ == "__main__":

	connection = None
	connected = False

	init_db()

	# Opening connection to mysql DB
	logger.info('Connecting to MySQL DB')
	try:
		# connection = mysql.connector.connect(host=mysql_config_mysql_host, database=mysql_config_mysql_db, user=mysql_config_mysql_user, password=mysql_config_mysql_pass)
		cursor = get_cursor()
		if connection.is_connected():
			db_Info = connection.get_server_info()
			logger.info('Connected to MySQL database. MySQL Server version on ' + str(db_Info))
			cursor = connection.cursor()
			cursor.execute("select database();")
			record = cursor.fetchone()
			logger.debug('Your connected to - ' + str(record))
			connection.commit()
	except Error as e :
		logger.error('Error while connecting to MySQL' + str(e))

	# Getting todays date
	dt = datetime.now()
	request_date = str(dt.year) + "-" + str(dt.month).zfill(2) + "-" + str(dt.day).zfill(2)  
	logger.debug("Generated today's date: " + str(request_date))

	logger.debug("Request url: " + str(nasa_api_url + "rest/v1/feed?start_date=" + request_date + "&end_date=" + request_date + "&api_key=" + nasa_api_key))
	# Requests data about asteroids passing earth today by sending todays data and the API key to the nasa API endpoint
	r = requests.get(nasa_api_url + "rest/v1/feed?start_date=" + request_date + "&end_date=" + request_date + "&api_key=" + nasa_api_key)

	# Logs out the status code of the request
	logger.debug("Response status code: " + str(r.status_code))
	# Logs out the headers of the request
	logger.debug("Response headers: " + str(r.headers))
	# Logs out the content of the response in unicode
	logger.debug("Response content: " + str(r.text))

	# The following will be executed if the response was successful
	if r.status_code == 200:

		# Parses the responses content into a python dictionary
		json_data = json.loads(r.text)

		# Creates an array for safe asteroids
		ast_safe = []
		# Creates and array for hazardous asteroids
		ast_hazardous = []

		# Checks if the element "element_count" is in json_data to avoid errors if the JSON structure of the response has changed
		if 'element_count' in json_data:
			# Assigns the asteroid count of that day to a variable
			ast_count = int(json_data['element_count'])
			# Logs out the asteroid count of that day
			logger.info("Asteroid count today: " + str(ast_count))

			# Checks if there are any asteroids to process
			if ast_count > 0:
				# Loops through all the "near_earth_objects" values
				for val in json_data['near_earth_objects'][request_date]:
					# Checks if certain variables are present in the value that is being looped through
					if 'name' and 'nasa_jpl_url' and 'estimated_diameter' and 'is_potentially_hazardous_asteroid' and 'close_approach_data' in val:
						logger.debug("------------------------------------------------------- >>") #My logger addition
						# Assigning the name of the asteroid to a variable
						tmp_ast_name = val['name']
						logger.debug('Name of hazardojus asteroid: ' + tmp_ast_name) #My logger addition
						# Assigning the url of an asteroids description to a variable
						tmp_ast_nasa_jpl_url = val['nasa_jpl_url']
						logger.debug('Hazardojus asteroid url: ' + tmp_ast_nasa_jpl_url) #My logger addition
						# Assigns the id of an asteroid to a variable
						tmp_ast_id = val['id']
						logger.debug('Hazardojus asteroid id: ' + tmp_ast_id) #My logger addition
						# Assigns minimum and maximum diameter of asteroids to variables
						if 'kilometers' in val['estimated_diameter']:
							logger.debug("------------------------------------------------------- >>") #My logger addition
							if 'estimated_diameter_min' and 'estimated_diameter_max' in val['estimated_diameter']['kilometers']:
								tmp_ast_diam_min = round(val['estimated_diameter']['kilometers']['estimated_diameter_min'], 3)
								logger.debug('Min asteroid diameter: ' + str(tmp_ast_diam_min)) #My logger addition
								tmp_ast_diam_max = round(val['estimated_diameter']['kilometers']['estimated_diameter_max'], 3)
								logger.debug('Max asteroid diameter: ' + str(tmp_ast_diam_max)) #My logger addition
							else:
								tmp_ast_diam_min = -2
								logger.error('Min asteroid diameter: ' + str(tmp_ast_diam_min)) #My logger addition
								tmp_ast_diam_max = -2
								logger.error('Max asteroid diameter: ' + str(tmp_ast_diam_max)) #My logger addition
						else:
							tmp_ast_diam_min = -1
							logger.error('Min asteroid diameter: ' + str(tmp_ast_diam_min)) #My logger addition
							tmp_ast_diam_max = -1
							logger.error('Max asteroid diameter: ' + str(tmp_ast_diam_max)) #My logger addition

						# Assigns tha value of "is_potentially_hazardous_asteroid" to a variable
						tmp_ast_hazardous = val['is_potentially_hazardous_asteroid']
						logger.debug('Hazardous: ' + str(tmp_ast_hazardous)) #My logger addition

						# Checks if there are any "close_approach_data" values in the data
						if len(val['close_approach_data']) > 0:
							logger.debug("------------------------------------------------------- >>") #My logger addition
							# Assigns data about an asteroids close approach, its speed and its miss distance to variables
							if 'epoch_date_close_approach' and 'relative_velocity' and 'miss_distance' in val['close_approach_data'][0]:
								tmp_ast_close_appr_ts = int(val['close_approach_data'][0]['epoch_date_close_approach']/1000)
								logger.debug('Close approach TS: ' + str(tmp_ast_close_appr_ts)) #My logger addition
								tmp_ast_close_appr_dt_utc = datetime.utcfromtimestamp(tmp_ast_close_appr_ts).strftime('%Y-%m-%d %H:%M:%S')
								logger.debug('Date/time UTC TZ: ' + str(tmp_ast_close_appr_dt_utc)) #My logger addition
								tmp_ast_close_appr_dt = datetime.fromtimestamp(tmp_ast_close_appr_ts).strftime('%Y-%m-%d %H:%M:%S')
								logger.debug('Local TZ: ' + str(tmp_ast_close_appr_dt_utc)) #My logger addition

								if 'kilometers_per_hour' in val['close_approach_data'][0]['relative_velocity']:
									tmp_ast_speed = int(float(val['close_approach_data'][0]['relative_velocity']['kilometers_per_hour']))
									logger.debug('Speed: ' + str(tmp_ast_speed)) #My logger addition
								else:
									tmp_ast_speed = -1
									logger.error('Speed: ' + str(tmp_ast_speed)) #My logger addition

								if 'kilometers' in val['close_approach_data'][0]['miss_distance']:
									tmp_ast_miss_dist = round(float(val['close_approach_data'][0]['miss_distance']['kilometers']), 3)
									logger.debug('Miss distance: ' + str(tmp_ast_miss_dist)) #My logger addition
								else:
									tmp_ast_miss_dist = -1
									logger.error('Miss distance: ' + str(tmp_ast_miss_dist)) #My logger addition
							else:
								tmp_ast_close_appr_ts = -1
								logger.error('Close approach TS: ' + str(tmp_ast_close_appr_ts)) #My logger addition
								tmp_ast_close_appr_dt_utc = "1969-12-31 23:59:59"
								logger.error('Date/time UTC TZ: ' + str(tmp_ast_close_appr_dt_utc)) #My logger addition
								tmp_ast_close_appr_dt = "1969-12-31 23:59:59"
								logger.error('Local TZ: ' + str(tmp_ast_close_appr_dt_utc)) #My logger addition
						else:
							logger.warning("No close approach data in message")
							tmp_ast_close_appr_ts = 0
							logger.error('Close approach TS: ' + str(tmp_ast_close_appr_ts)) #My logger addition
							tmp_ast_close_appr_dt_utc = "1970-01-01 00:00:00"
							logger.error('Date/time UTC TZ: ' + str(tmp_ast_close_appr_dt_utc)) #My logger addition
							tmp_ast_close_appr_dt = "1970-01-01 00:00:00"
							logger.error('Local TZ: ' + str(tmp_ast_close_appr_dt_utc)) #My logger addition
							tmp_ast_speed = -1
							logger.error('Speed: ' + str(tmp_ast_speed)) #My logger addition
							tmp_ast_miss_dist = -1
							logger.error('Miss distance: ' + str(tmp_ast_miss_dist)) #My logger addition

						# Used to separate asteroids in the print out
						logger.info("------------------------------------------------------- >>")
						# Logs out the asteroids name, the url leading to its description, its minimum and maximum diameter and if it is hazardous or not
						logger.info("Asteroid name: " + str(tmp_ast_name) + " | INFO: " + str(tmp_ast_nasa_jpl_url) + " | Diameter: " + str(tmp_ast_diam_min) + " - " + str(tmp_ast_diam_max) + " km | Hazardous: " + str(tmp_ast_hazardous))
						# Logs out the asteroids close approach distance, the time of it in UTC and local
						logger.info("Close approach TS: " + str(tmp_ast_close_appr_ts) + " | Date/time UTC TZ: " + str(tmp_ast_close_appr_dt_utc) + " | Local TZ: " + str(tmp_ast_close_appr_dt))
						# Logs out the asteroids speed and the distance it will miss Earth by
						logger.info("Speed: " + str(tmp_ast_speed) + " km/h" + " | MISS distance: " + str(tmp_ast_miss_dist) + " km")
						
						# Adding asteroid data to the corresponding array
						if tmp_ast_hazardous == True:
							ast_hazardous.append([tmp_ast_name, tmp_ast_nasa_jpl_url, tmp_ast_diam_min, tmp_ast_diam_max, tmp_ast_close_appr_ts, tmp_ast_close_appr_dt_utc, tmp_ast_close_appr_dt, tmp_ast_speed, tmp_ast_miss_dist, tmp_ast_id])
						else:
							ast_safe.append([tmp_ast_name, tmp_ast_nasa_jpl_url, tmp_ast_diam_min, tmp_ast_diam_max, tmp_ast_close_appr_ts, tmp_ast_close_appr_dt_utc, tmp_ast_close_appr_dt, tmp_ast_speed, tmp_ast_miss_dist, tmp_ast_id])

			else:
				logger.info("No asteroids are going to hit earth today")

		# Logs out how many asteroids are in each array
		logger.info("Hazardous asteorids: " + str(len(ast_hazardous)) + " | Safe asteroids: " + str(len(ast_safe)))

		if len(ast_hazardous) > 0:
			# Sorts the asteroids by the time of its close approach
			ast_hazardous.sort(key = lambda x: x[4], reverse=False)

			logger.info("Today's possible apocalypse (asteroid impact on earth) times:")
			# Cycles through the values in the ast_hazardous array
			for asteroid in ast_hazardous:
				# Logs out an asteroids date and time of close approach in local time, its name and a url to its description
				logger.info(str(asteroid[6]) + " " + str(asteroid[0]) + " " + " | more info: " + str(asteroid[1]))

			# Sorts the asteroids by their miss distance in ascending order
			ast_hazardous = sort_ast_by_pass_dist(ast_hazardous)
			# Logs the asteroids name, its miss distance and a url to its description
			logger.info("Closest passing distance is for: " + str(ast_hazardous[0][0]) + " at: " + str(int(ast_hazardous[0][8])) + " km | more info: " + str(ast_hazardous[0][1]))
			
		else:
			logger.info("No asteroids close passing earth today")

		push_asteroids_arrays_to_db(request_date, ast_hazardous, 1)
		push_asteroids_arrays_to_db(request_date, ast_safe, 0)
	else:
		logger.error("Unable to get response from API. Response code: " + str(r.status_code) + " | content: " + str(r.text))