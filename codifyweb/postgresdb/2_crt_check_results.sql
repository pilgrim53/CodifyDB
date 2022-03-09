-- Table: check_results

-- DROP TABLE check_results;

CREATE TABLE check_results
(
    inventory_id integer,
    check_date timestamp without time zone,
    check_result text COLLATE pg_catalog."default",
    check_column text COLLATE pg_catalog."default"
)

TABLESPACE pg_default;

ALTER TABLE check_results
    OWNER to postgres;
-- Index: CR_Column

-- DROP INDEX "CR_Column";

CREATE INDEX "CR_Column"
    ON check_results USING hash
    (check_column COLLATE pg_catalog."default")
    TABLESPACE pg_default;
-- Index: RESULTS

-- DROP INDEX "RESULTS";

CREATE INDEX "RESULTS"
    ON check_results USING btree
    (inventory_id ASC NULLS LAST, check_date ASC NULLS LAST, check_column COLLATE pg_catalog."default" ASC NULLS LAST)
    INCLUDE(inventory_id, check_date, check_column)
    TABLESPACE pg_default;
-- Index: check_date

-- DROP INDEX check_date;

CREATE INDEX check_date
    ON check_results USING btree
    (check_date ASC NULLS LAST)
    TABLESPACE pg_default;
-- Index: check_inv

-- DROP INDEX check_inv;

CREATE INDEX check_inv
    ON check_results USING btree
    (inventory_id ASC NULLS LAST)
    TABLESPACE pg_default;
