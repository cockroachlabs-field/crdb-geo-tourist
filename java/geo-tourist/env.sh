export DB_URL="jdbc:cockroachdb://localhost:26257/defaultdb?user=root&ssl=false&application_name=BootGeoTourist&retryConnectionErrors=true&retryTransientErrors=true"

# If the DB_URL starts with "jdbc:cockroachdb://", this next line is required:
export JDBC_DRIVER_CLASS="io.cockroachdb.jdbc.CockroachDriver"

# The server.port value will be set to this value:
export FLASK_PORT=8081

