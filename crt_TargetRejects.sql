-- Table: codify.target_rejects

-- DROP TABLE codify.target_rejects;

CREATE TABLE codify.target_rejects
(
    inventoryid 	integer,
    inventorycreate date,
    lastcheckdate 	timestamp without time zone,
    vendor 			text,
    instancename 	text,
    hostname 		text,
    homedirectory 	text,
    owner 			text,
    port 			integer,
    status 			text,
    databasetype 	text,
    importantnotes 	text
)
TABLESPACE pg_default;

ALTER TABLE codify.target_rejects
    OWNER to codify;

COMMIT;