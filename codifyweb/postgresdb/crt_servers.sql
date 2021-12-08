-- View: servers

-- DROP VIEW servers;

CREATE OR REPLACE VIEW servers
 AS
 SELECT id.inventory_id AS inventoryid,
    id.hostname,
    id.vendor,
    id.os,
    id.db_created_date AS created,
    id.serial_number AS serialnumber,
    id.owner,
    id.host_type AS hosttype,
    a.check_result AS started,
    b.check_result AS osaccess
   FROM ((targets id
     LEFT JOIN check_results a ON (((id.inventory_id = a.inventory_id) AND (a.check_date = ( SELECT max(a1.check_date) AS max
           FROM check_results a1
          WHERE ((a1.inventory_id = id.inventory_id) AND (a1.check_column = 'started'::text)))) AND (a.check_column = 'started'::text))))
     LEFT JOIN check_results b ON (((id.inventory_id = b.inventory_id) AND (b.check_date = ( SELECT max(b1.check_date) AS max
           FROM check_results b1
          WHERE ((b1.inventory_id = id.inventory_id) AND (b1.check_column = 'osaccess'::text)))) AND (b.check_column = 'osaccess'::text))))
  WHERE ((id.decommissioned IS NULL) AND (id.target_type = 'Server'::text))
  ORDER BY id.inventory_id;

ALTER TABLE servers
    OWNER TO codify;

