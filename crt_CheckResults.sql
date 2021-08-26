-- Table: codify.checkresults

-- DROP TABLE codify.checkresults;

CREATE TABLE codify.checkresults
(
    inventoryid 	integer,
    checkdate 		timestamp without time zone,
    check_result 	text COLLATE pg_catalog."default",
    check_column 	text COLLATE pg_catalog."default"
)
TABLESPACE pg_default;

ALTER TABLE codify.checkresults
    OWNER to codify;
	
-- Index: CR_Column

-- DROP INDEX codify."CR_Column";

CREATE INDEX "CR_Column"
    ON codify.checkresults USING hash
    (check_column COLLATE pg_catalog."default")
    TABLESPACE pg_default;
	
-- Index: check_date

-- DROP INDEX codify.check_date;

CREATE INDEX check_date
    ON codify.checkresults USING btree
    (checkdate ASC NULLS LAST)
    TABLESPACE pg_default;
	
-- Index: check_inv

-- DROP INDEX codify.check_inv;

CREATE INDEX check_inv
    ON codify.checkresults USING btree
    (inventoryid ASC NULLS LAST)
    TABLESPACE pg_default;

COMMIT;