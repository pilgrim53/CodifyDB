-- Table: codify.target_rejects

-- DROP TABLE codify.target_rejects;

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
    OWNER to codify;
