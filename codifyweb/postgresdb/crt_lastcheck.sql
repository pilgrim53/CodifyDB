-- View: lastcheck

-- DROP VIEW lastcheck;

CREATE OR REPLACE VIEW lastcheck
 AS
 SELECT id.inventory_id AS inventoryid,
    id.hostname,
    id.instance_name AS instancename,
    a.check_result AS started,
    b.check_result AS closedwallet,
    c.check_result AS dbcaccess,
    d.check_result AS appsessions,
    e.check_result AS openmode,
    f.check_result AS swrelease,
    g.check_result AS systemfree,
    h.check_result AS sysauxfree,
    i.check_result AS dbsizeallocated,
    j.check_result AS dbsizeused,
    k.check_result AS processespct,
    l.check_result AS badfileloc,
    m.check_result AS dbstatus,
    n.check_result AS inoms
   FROM ((((((((((((((targets id
     LEFT JOIN check_results a ON (((id.inventory_id = a.inventory_id) AND (a.check_date = ( SELECT max(a1.check_date) AS max
           FROM check_results a1
          WHERE ((a1.inventory_id = id.inventory_id) AND (a1.check_column = 'started'::text)))) AND (a.check_column = 'started'::text))))
     LEFT JOIN check_results b ON (((id.inventory_id = b.inventory_id) AND (b.check_date = ( SELECT max(b1.check_date) AS max
           FROM check_results b1
          WHERE ((b1.inventory_id = id.inventory_id) AND (b1.check_column = 'closedwallet'::text)))) AND (b.check_column = 'closedwallet'::text))))
     LEFT JOIN check_results c ON (((id.inventory_id = c.inventory_id) AND (c.check_date = ( SELECT max(c1.check_date) AS max
           FROM check_results c1
          WHERE ((c1.inventory_id = id.inventory_id) AND (c1.check_column = 'dbcaccess'::text)))) AND (c.check_column = 'dbcaccess'::text))))
     LEFT JOIN check_results d ON (((id.inventory_id = d.inventory_id) AND (d.check_date = ( SELECT max(d1.check_date) AS max
           FROM check_results d1
          WHERE ((d1.inventory_id = id.inventory_id) AND (d1.check_column = 'appsessions'::text)))) AND (d.check_column = 'appsessions'::text))))
     LEFT JOIN check_results e ON (((id.inventory_id = e.inventory_id) AND (e.check_date = ( SELECT max(e1.check_date) AS max
           FROM check_results e1
          WHERE ((e1.inventory_id = id.inventory_id) AND (e1.check_column = 'openmode'::text)))) AND (e.check_column = 'openmode'::text))))
     LEFT JOIN check_results f ON (((id.inventory_id = f.inventory_id) AND (f.check_date = ( SELECT max(f1.check_date) AS max
           FROM check_results f1
          WHERE ((f1.inventory_id = id.inventory_id) AND (f1.check_column = 'swrelease'::text)))) AND (f.check_column = 'swrelease'::text))))
     LEFT JOIN check_results g ON (((id.inventory_id = g.inventory_id) AND (g.check_date = ( SELECT max(g1.check_date) AS max
           FROM check_results g1
          WHERE ((g1.inventory_id = id.inventory_id) AND (g1.check_column = 'systemfree'::text)))) AND (g.check_column = 'systemfree'::text))))
     LEFT JOIN check_results h ON (((id.inventory_id = h.inventory_id) AND (h.check_date = ( SELECT max(h1.check_date) AS max
           FROM check_results h1
          WHERE ((h1.inventory_id = id.inventory_id) AND (h1.check_column = 'sysauxfree'::text)))) AND (h.check_column = 'sysauxfree'::text))))
     LEFT JOIN check_results i ON (((id.inventory_id = i.inventory_id) AND (i.check_date = ( SELECT max(i1.check_date) AS max
           FROM check_results i1
          WHERE ((i1.inventory_id = id.inventory_id) AND (i1.check_column = 'dbsizeallocated'::text)))) AND (i.check_column = 'dbsizeallocated'::text))))
     LEFT JOIN check_results j ON (((id.inventory_id = j.inventory_id) AND (j.check_date = ( SELECT max(j1.check_date) AS max
           FROM check_results j1
          WHERE ((j1.inventory_id = id.inventory_id) AND (j1.check_column = 'dbsizeused'::text)))) AND (j.check_column = 'dbsizeused'::text))))
     LEFT JOIN check_results k ON (((id.inventory_id = k.inventory_id) AND (k.check_date = ( SELECT max(k1.check_date) AS max
           FROM check_results k1
          WHERE ((k1.inventory_id = id.inventory_id) AND (k1.check_column = 'processespct'::text)))) AND (k.check_column = 'processespct'::text))))
     LEFT JOIN check_results l ON (((id.inventory_id = l.inventory_id) AND (l.check_date = ( SELECT max(l1.check_date) AS max
           FROM check_results l1
          WHERE ((l1.inventory_id = id.inventory_id) AND (l1.check_column = 'badfileloc'::text)))) AND (l.check_column = 'badfileloc'::text))))
     LEFT JOIN check_results m ON (((id.inventory_id = m.inventory_id) AND (m.check_date = ( SELECT max(m1.check_date) AS max
           FROM check_results m1
          WHERE ((m1.inventory_id = id.inventory_id) AND (m1.check_column = 'dbstatus'::text)))) AND (m.check_column = 'dbstatus'::text))))
     LEFT JOIN check_results n ON (((id.inventory_id = n.inventory_id) AND (n.check_date = ( SELECT max(n1.check_date) AS max
           FROM check_results n1
          WHERE ((n1.inventory_id = id.inventory_id) AND (n1.check_column = 'inoms'::text)))) AND (n.check_column = 'inoms'::text))))
  WHERE ((id.decommissioned IS NULL) AND (id.target_type = 'Database'::text))
  ORDER BY id.inventory_id;

ALTER TABLE lastcheck
    OWNER TO codify;
