-- Table: public.check_results

-- DROP TABLE public.check_results;

CREATE TABLE public.check_results
(
    inventory_id integer,
    check_date timestamp without time zone,
    check_result text COLLATE pg_catalog."default",
    check_column text COLLATE pg_catalog."default"
)

TABLESPACE pg_default;

ALTER TABLE public.check_results
    OWNER to postgres;
-- Index: CR_Column

-- DROP INDEX public."CR_Column";

CREATE INDEX "CR_Column"
    ON public.check_results USING hash
    (check_column COLLATE pg_catalog."default")
    TABLESPACE pg_default;
-- Index: RESULTS

-- DROP INDEX public."RESULTS";

CREATE INDEX "RESULTS"
    ON public.check_results USING btree
    (inventory_id ASC NULLS LAST, check_date ASC NULLS LAST, check_column COLLATE pg_catalog."default" ASC NULLS LAST)
    INCLUDE(inventory_id, check_date, check_column)
    TABLESPACE pg_default;
-- Index: check_date

-- DROP INDEX public.check_date;

CREATE INDEX check_date
    ON public.check_results USING btree
    (check_date ASC NULLS LAST)
    TABLESPACE pg_default;
-- Index: check_inv

-- DROP INDEX public.check_inv;

CREATE INDEX check_inv
    ON public.check_results USING btree
    (inventory_id ASC NULLS LAST)
    TABLESPACE pg_default;
