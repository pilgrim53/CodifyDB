-- Table: codify.target

-- DROP TABLE codify.target;

CREATE TABLE codify.target
(
    inventoryid 		integer NOT NULL DEFAULT nextval('codify.inventory_seq'::regclass),
    inventorycreate 	date NOT NULL,
    inservicedate 		date,
    lastcheckdate 		timestamp without time zone,
    serialnumber 		text COLLATE pg_catalog."default",
    vendor 				text COLLATE pg_catalog."default",
    instancename 		text COLLATE pg_catalog."default",
    hostname 			text COLLATE pg_catalog."default",
    version 			text COLLATE pg_catalog."default",
    homedirectory 		text COLLATE pg_catalog."default",
    owner 				text COLLATE pg_catalog."default",
    port 				integer,
    status 				text COLLATE pg_catalog."default",
    backupmode 			text COLLATE pg_catalog."default",
    blocksize 			integer,
    highlysensitiveinfo bit(1),
    targettype 			text COLLATE pg_catalog."default",
    importantnotes 		text COLLATE pg_catalog."default",
    role 				text COLLATE pg_catalog."default",
    container 			text COLLATE pg_catalog."default",
    decommissioned 		date,
    hosttype 			text COLLATE pg_catalog."default",
    secondarynode 		text COLLATE pg_catalog."default",
    os 					text COLLATE pg_catalog."default",
    v_instance 			text COLLATE pg_catalog."default",
    CONSTRAINT target_pkey PRIMARY KEY (inventoryid),
    CONSTRAINT target_unique UNIQUE (instancename, hostname, container)
)

TABLESPACE pg_default;

ALTER TABLE codify.target
    OWNER to codify;