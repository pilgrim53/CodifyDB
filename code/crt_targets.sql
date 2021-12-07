-- Table: public.targets

ALTER TABLE public.targets
    OWNER to codify;

GRANT ALL ON TABLE public.targets TO postgres;

COMMENT ON COLUMN public.targets.target_type
    IS 'Database,  Server, Other';
-- Index: inv_inst

-- DROP INDEX public.inv_inst;

CREATE INDEX inv_inst
    ON public.targets USING btree
    (inventory_id ASC NULLS LAST, instance_name COLLATE pg_catalog."default" ASC NULLS LAST, hostname COLLATE pg_catalog."default" ASC NULLS LAST)
    TABLESPACE pg_default;
