# sq-statsd-monitor
# Author: Reed Odeneal

import sys, pyodbc, logging, time, yaml, statsd

#constants
# TODO: Make this configurable per metric or environment
INTERVAL = 15

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# returns a connection object
def makeConnection(server,database,user,password):
	logger.info('Creating ODBC connection to ' + server + '/' + database + ' with user ' + user )
	connection = pyodbc.connect('DRIVER=/usr/local/lib/libtdsodbc.so;SERVER=' + server + ';PORT=1433;DATABASE=' + database + ';UID=' + user + ';PWD=' + password)
	return connection.cursor()

def makeQuery(cursor,query):
	cursor.execute(queries[query])
	row = cursor.fetchone()
	if row:
		logger.info(queries[query] + ': ' + str(row[0]))
		return row[0]

def recordMetric(name,value):
	logger.info('Streaming ' + name + ' metric value, ' + str(value) + ' to statsd endpoint at ' + statsd_endpoint["server"] + ":" + statsd_endpoint["port"])
	# get the metric type
	for m in metrics:
		if name == m["metric"]["name"]:
			# TODO: Support timer type.
			if m["metric"]["type"] == "count":
				sc.incr(name, int(value))
			elif m["metric"]["type"] == "gauge":
				sc.gauge(name, int(value))
			else:
				logger.error('Invalid metric type ' + m["metric"]["type"] + ' for ' + name)

if __name__ == "__main__":
	metrics = yaml.safe_load(open("conf/metrics.yaml"))
	environment = yaml.safe_load(open("conf/environment.yaml"))
	statsd_endpoint = yaml.safe_load(open("conf/statsd.yaml"))
	
	sc = statsd.StatsClient(statsd_endpoint["server"],statsd_endpoint["port"])

	# to hold our connection objects
	connections = {}

	# create connection objects for each database
	for d in environment:
		connections[d["database"]["name"] + '.' + d["database"]["environment"]] = makeConnection(
				d["database"]["server"],
				d["database"]["name"],
				d["database"]["user"],
				d["database"]["password"])

	# to hold our metric queries
	queries = {}

	# populate queries dictionary
	for m in metrics:
		queries[m["metric"]["name"]] = m["metric"]["query"]

	# loop through each database in the environment and return the query for each metric
	while True:
		logger.info('Querying for metrics every ' + str(INTERVAL) + ' seconds.')
		for d in environment:
			logger.info('Executing queries for ' + d["database"]["name"] + " in environment " + d["database"]["environment"])
			for m in d["database"]["metrics"]:
				r = makeQuery(connections[d["database"]["name"] + '.' + d["database"]["environment"]],m)
				recordMetric(m,r)
		time.sleep(INTERVAL)