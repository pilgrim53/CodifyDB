----------------------------------
-- Drop commands if required
----------------------------------
DROP SCHEMA   CODIFY;
DROP VIEW     codify.lastcheck;
DROP TABLE    codify.checkresults;
DROP TABLE    codify.target;
DROP SEQUENCE codify.inventoryid;
DROP INDEX    codify.inv_inst;
DROP INDEX    codify.CR_Column;
DROP INDEX    codify.check_date;
DROP INDEX    codify.check_inv;
DROP TABLE    codify.checklist;
DROP TABLE    codify.target_rejects;
----------------------------------

DO
$do$
BEGIN
   IF NOT EXISTS (
      SELECT FROM pg_catalog.pg_roles  -- SELECT list can be empty for this
      WHERE  rolname = 'codify') 
	  THEN
      CREATE ROLE codify superuser;
	  GRANT codify to postgres;
	  ALTER ROLE codify with login PASSWORD 'codify_2021';
   END IF;
END
$do$;

CREATE SCHEMA codify AUTHORIZATION codify;

-- SEQUENCE: codify.inventoryid
CREATE SEQUENCE codify.inventory_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    CACHE 1;

ALTER SEQUENCE codify.inventory_seq
    OWNER TO codify;

-- Table: codify.target
@crt_Target.sql

-- Table: codify.checkresults
@crt_CheckResults.sql

--- View: codify.lastcheck
@crt_LastCheck.sql

-- Table: codify.target_rejects
@crt_TargetRejects.sql

-- Table: codify.checklist
@crt_CheckList.sql

---------------------------------------------
---------------------------------------------

-- Index: Target.inv_inst
CREATE INDEX inv_inst
    ON codify.target USING btree
    (inventoryid ASC NULLS LAST, 
	 instancename ASC NULLS LAST, 
	 hostname ASC NULLS LAST)
    TABLESPACE pg_default;
	
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

