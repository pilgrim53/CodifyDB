#!/bin/bash
# set -e
export PGPASSWORD=$POSTGRES_PASSWORD;
psql -v ON_ERROR_STOP=0 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
  CREATE USER $APP_DB_USER WITH PASSWORD '$APP_DB_PASS';
  CREATE DATABASE $APP_DB_NAME;
  GRANT ALL PRIVILEGES ON DATABASE $APP_DB_NAME TO $APP_DB_USER;
  CREATE SCHEMA codify AUTHORIZATION codify;
  grant postgres to codify;
  ALTER DATABASE $APP_DB_NAME SET search_path = $APP_DB_USER, public;

  \connect $APP_DB_NAME $APP_DB_USER


-- Name: checkresults; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE check_results
(
    inventory_id integer,
    check_date timestamp without time zone,
    check_result text COLLATE pg_catalog."default",
    check_column text COLLATE pg_catalog."default"
)

TABLESPACE pg_default;

ALTER TABLE check_results
    OWNER to $APP_DB_USER;

CREATE INDEX "CR_Column"
    ON check_results USING hash
    (check_column COLLATE pg_catalog."default")
    TABLESPACE pg_default;
-- Index: RESULTS

CREATE INDEX "RESULTS"
    ON check_results USING btree
    (inventory_id ASC NULLS LAST, check_date ASC NULLS LAST, check_column COLLATE pg_catalog."default" ASC NULLS LAST)
    INCLUDE(inventory_id, check_date, check_column)
    TABLESPACE pg_default;
-- Index: check_date

CREATE INDEX check_date
    ON check_results USING btree
    (check_date ASC NULLS LAST)
    TABLESPACE pg_default;
-- Index: check_inv

CREATE INDEX check_inv
    ON check_results USING btree
    (inventory_id ASC NULLS LAST)
    TABLESPACE pg_default;

--
-- Name: target_rejects; Type: TABLE; Schema: public; Owner: $APP_DB_USER
--

CREATE TABLE target_rejects
(
    inventory_id integer,
    inventory_create date,
    last_check_date timestamp without time zone,
    vendor character varying(50) COLLATE pg_catalog."default",
    instance_name character varying(50) COLLATE pg_catalog."default",
    hostname character varying(50) COLLATE pg_catalog."default",
    home_directory character varying(255) COLLATE pg_catalog."default",
    owner character varying(50) COLLATE pg_catalog."default",
    port integer,
    status character varying(255) COLLATE pg_catalog."default",
    database_type character varying(50) COLLATE pg_catalog."default",
    important_notes character varying(1000) COLLATE pg_catalog."default"
)

TABLESPACE pg_default;

ALTER TABLE target_rejects
    OWNER to $APP_DB_USER;




\q
EOSQL
