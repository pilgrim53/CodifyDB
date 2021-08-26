-- Table: codify.checklist

-- DROP TABLE codify.checklist;

CREATE TABLE codify.checklist
(
    id 				integer NOT NULL,
    vendor 			text COLLATE pg_catalog."default",
    frequency 		text COLLATE pg_catalog."default",
    check_type 		text COLLATE pg_catalog."default",
    description 	text COLLATE pg_catalog."default",
    check_command 	text COLLATE pg_catalog."default",
    result_column 	text COLLATE pg_catalog."default",
    priority 		integer,
    CONSTRAINT checklist_pkey PRIMARY KEY (id)
)

TABLESPACE pg_default;

ALTER TABLE codify.checklist
    OWNER to codify;