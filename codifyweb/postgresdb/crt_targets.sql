-- Table: targets

ALTER TABLE targets
    OWNER to codify;

GRANT ALL ON TABLE targets TO postgres;

COMMENT ON COLUMN targets.target_type
    IS 'Database,  Server, Other';
-- Index: inv_inst

-- DROP INDEX inv_inst;

CREATE INDEX inv_inst
    ON targets USING btree
    (inventory_id ASC NULLS LAST, instance_name COLLATE pg_catalog."default" ASC NULLS LAST, hostname COLLATE pg_catalog."default" ASC NULLS LAST)
    TABLESPACE pg_default;
