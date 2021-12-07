#!/bin/bash
set -e
export PGPASSWORD=$POSTGRES_PASSWORD;
psql -v ON_ERROR_STOP=0 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
  CREATE USER $APP_DB_USER WITH PASSWORD '$APP_DB_PASS';
  CREATE DATABASE $APP_DB_NAME;
  GRANT ALL PRIVILEGES ON DATABASE $APP_DB_NAME TO $APP_DB_USER;
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
COMMIT;
  
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

CREATE SCHEMA codify AUTHORIZATION codify;

-- SEQUENCE: codify.inventoryid
CREATE SEQUENCE codify.inventory_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    CACHE 1;

ALTER SEQUENCE codify.inventory_seq
    OWNER TO codify;
	
COMMIT;

-- Table: codify.target   Now Managed by Django Models
--  \i /code/crt_Target.sql

-- Index: Target.inv_inst
-- CREATE INDEX inv_inst ON codify.target USING btree
--    (inventoryid ASC NULLS LAST, instancename ASC NULLS LAST,  hostname ASC NULLS LAST) ;

-- Table: codify.checklist  Now Managed by Django Models
--  \i /code/crt_CheckList.sql

-- Table: codify.checkresults
\i /code/crt_CheckResults.sql

--- View: codify.lastcheck
\i /code/crt_LastCheck.sql

-- Table: codify.target_rejects
\i /code/crt_TargetRejects.sql

---------------------------------------------
---------------------------------------------
	
-- Index: CR_Column
CREATE INDEX "CR_Column"
    ON codify.checkresults USING hash
    (check_column COLLATE pg_catalog."default")
    TABLESPACE pg_default;

-- Index: check_date
CREATE INDEX check_date
    ON codify.checkresults USING btree
    (checkdate ASC NULLS LAST)
    TABLESPACE pg_default;

-- Index: check_inv
CREATE INDEX check_inv
    ON codify.checkresults USING btree
    (inventoryid ASC NULLS LAST)
    TABLESPACE pg_default;

  COMMIT;
  
-- CREATE VIEW public.checklist AS SELECT * FROM codify.checklist;
-- CREATE VIEW public.checkresults AS SELECT * FROM codify.checkresults;
-- CREATE VIEW public.target AS SELECT * FROM codify.target;
-- CREATE VIEW public.lastcheck AS SELECT * FROM codify.lastcheck;

EOSQL
