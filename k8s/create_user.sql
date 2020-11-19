CREATE ROLE tourist LOGIN PASSWORD 'tourist';
GRANT admin TO tourist; -- "tourist" can log into DB Console and also use defaultdb
