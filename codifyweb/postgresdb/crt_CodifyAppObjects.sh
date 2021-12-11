#!/bin/bash
set -e
export PGPASSWORD=$POSTGRES_PASSWORD;
psql -v ON_ERROR_STOP=0 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
  \connect $APP_DB_NAME $APP_DB_USER
  BEGIN;
----------------------------------
-- Drop commands if required
----------------------------------
-- DROP SCHEMA   CODIFY;
-- DROP VIEW     codify.lastcheck;
-- DROP TABLE    codify.checkresults;
-- DROP TABLE    codify.target;
-- DROP SEQUENCE codify.inventoryid;
-- DROP INDEX    codify.inv_inst;
-- DROP INDEX    codify.CR_Column;
-- DROP INDEX    codify.check_date;
-- DROP INDEX    codify.check_inv;
-- DROP TABLE    codify.checklist;
-- DROP TABLE    codify.target_rejects;
----------------------------------
  
DO
\$do\$
BEGIN
   IF NOT EXISTS (
      SELECT FROM pg_catalog.pg_roles  -- SELECT list can be empty for this
      WHERE  rolname = 'codify') 
	  THEN
      CREATE ROLE codify superuser;
	  GRANT codify to postgres;
	  ALTER ROLE codify with login PASSWORD 'codify_2021';
	  COMMIT;
   END IF;
END
\$do\$;


-- SEQUENCE: codify.inventoryid
CREATE SEQUENCE codify.inventory_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    CACHE 1;

ALTER SEQUENCE codify.inventory_seq
    OWNER TO codify;

-- Table: codify.targets   Now Managed by Django Models
--  \i /code/crt_targets.sql

-- Index: Target.inv_inst
-- CREATE INDEX inv_inst ON codify.targets USING btree
--    (inventoryid ASC NULLS LAST, instancename ASC NULLS LAST,  hostname ASC NULLS LAST) ;

-- Table: codify.checklist  Now Managed by Django Models
--  \i /code/crt_checklist.sql

-- Application Tables and Views
\i /code/postgresdb/crt_check_results.sql
\i /code/postgresdb/crt_lastcheck.sql
\i /code/postgresdb/crt_target_rejects.sql
\i /code/postgresdb/crt_notifications.sql
\i /code/postgresdb/crt_servers.sql
\i /code/postgresdb/crt_lastcheck.sql
---------------------------------------------
---------------------------------------------
  
-- CREATE VIEW checklist AS SELECT * FROM codify.checklist;
-- CREATE VIEW checkresults AS SELECT * FROM codify.checkresults;
-- CREATE VIEW targets AS SELECT * FROM codify.targets;
-- CREATE VIEW lastcheck AS SELECT * FROM codify.lastcheck;
-- alter view targets owner to codify;

EOSQL
