-- Table: public.target

ALTER TABLE public.target
    OWNER to codify;

GRANT ALL ON TABLE public.target TO postgres;

COMMENT ON COLUMN public.target.target_type
    IS 'Database,  Server, Other';
-- Index: inv_inst

-- DROP INDEX public.inv_inst;

CREATE INDEX inv_inst
    ON public.target USING btree
    (inventory_id ASC NULLS LAST, instance_name COLLATE pg_catalog."default" ASC NULLS LAST, hostname COLLATE pg_catalog."default" ASC NULLS LAST)
    TABLESPACE pg_default;
