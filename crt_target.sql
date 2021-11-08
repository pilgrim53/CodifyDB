-- Table: public.target

-- DROP TABLE public.target;

CREATE TABLE public.target
(
    inventory_id integer NOT NULL DEFAULT nextval('inventoryid'::regclass),
    inventory_create date NOT NULL,
    db_created_date text COLLATE pg_catalog."default",
    last_check_date timestamp without time zone,
    serial_number character varying(20) COLLATE pg_catalog."default",
    vendor character varying(50) COLLATE pg_catalog."default",
    instance_name character varying(50) COLLATE pg_catalog."default",
    hostname character varying(50) COLLATE pg_catalog."default",
    version character varying(50) COLLATE pg_catalog."default",
    home_dir character varying(255) COLLATE pg_catalog."default",
    owner character varying(50) COLLATE pg_catalog."default",
    port integer,
    status character varying(255) COLLATE pg_catalog."default",
    archivelog_mode character varying(50) COLLATE pg_catalog."default",
    blocksize integer,
    highlysensitiveinfo bit(1),
    database_type character varying(50) COLLATE pg_catalog."default",
    important_notes character varying(1000) COLLATE pg_catalog."default",
    role character varying(25) COLLATE pg_catalog."default",
    container character varying(15) COLLATE pg_catalog."default",
    decommissioned date,
    host_type text COLLATE pg_catalog."default",
    standby_dest text COLLATE pg_catalog."default",
    os text COLLATE pg_catalog."default",
    v_instance text COLLATE pg_catalog."default",
    target_type text COLLATE pg_catalog."default" NOT NULL,
    support_tier text COLLATE pg_catalog."default",
    CONSTRAINT dbc_target_pkey PRIMARY KEY (inventory_id),
    CONSTRAINT "Instance" UNIQUE (hostname, instance_name, container)
)

TABLESPACE pg_default;

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
