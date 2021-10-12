-- View: public.lastcheck

DROP VIEW public.lastcheck;

CREATE OR REPLACE VIEW public.lastcheck
 AS
 SELECT id.inventoryid,
    id.hostname,
    id.instancename,
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
   FROM ((((((((((((((dbc_target id
     LEFT JOIN checkresults a ON (((id.inventoryid = a.inventoryid) AND (a.checkdate = ( SELECT max(a1.checkdate) AS max
           FROM checkresults a1
          WHERE ((a1.inventoryid = id.inventoryid) AND (a1.check_column = 'started'::text)))) AND (a.check_column = 'started'::text))))
     LEFT JOIN checkresults b ON (((id.inventoryid = b.inventoryid) AND (b.checkdate = ( SELECT max(b1.checkdate) AS max
           FROM checkresults b1
          WHERE ((b1.inventoryid = id.inventoryid) AND (b1.check_column = 'closedwallet'::text)))) AND (b.check_column = 'closedwallet'::text))))
     LEFT JOIN checkresults c ON (((id.inventoryid = c.inventoryid) AND (c.checkdate = ( SELECT max(c1.checkdate) AS max
           FROM checkresults c1
          WHERE ((c1.inventoryid = id.inventoryid) AND (c1.check_column = 'dbcaccess'::text)))) AND (c.check_column = 'dbcaccess'::text))))
     LEFT JOIN checkresults d ON (((id.inventoryid = d.inventoryid) AND (d.checkdate = ( SELECT max(d1.checkdate) AS max
           FROM checkresults d1
          WHERE ((d1.inventoryid = id.inventoryid) AND (d1.check_column = 'appsessions'::text)))) AND (d.check_column = 'appsessions'::text))))
     LEFT JOIN checkresults e ON (((id.inventoryid = e.inventoryid) AND (e.checkdate = ( SELECT max(e1.checkdate) AS max
           FROM checkresults e1
          WHERE ((e1.inventoryid = id.inventoryid) AND (e1.check_column = 'openmode'::text)))) AND (e.check_column = 'openmode'::text))))
     LEFT JOIN checkresults f ON (((id.inventoryid = f.inventoryid) AND (f.checkdate = ( SELECT max(f1.checkdate) AS max
           FROM checkresults f1
          WHERE ((f1.inventoryid = id.inventoryid) AND (f1.check_column = 'swrelease'::text)))) AND (f.check_column = 'swrelease'::text))))
     LEFT JOIN checkresults g ON (((id.inventoryid = g.inventoryid) AND (g.checkdate = ( SELECT max(g1.checkdate) AS max
           FROM checkresults g1
          WHERE ((g1.inventoryid = id.inventoryid) AND (g1.check_column = 'systemfree'::text)))) AND (g.check_column = 'systemfree'::text))))
     LEFT JOIN checkresults h ON (((id.inventoryid = h.inventoryid) AND (h.checkdate = ( SELECT max(h1.checkdate) AS max
           FROM checkresults h1
          WHERE ((h1.inventoryid = id.inventoryid) AND (h1.check_column = 'sysauxfree'::text)))) AND (h.check_column = 'sysauxfree'::text))))
     LEFT JOIN checkresults i ON (((id.inventoryid = i.inventoryid) AND (i.checkdate = ( SELECT max(i1.checkdate) AS max
           FROM checkresults i1
          WHERE ((i1.inventoryid = id.inventoryid) AND (i1.check_column = 'dbsizeallocated'::text)))) AND (i.check_column = 'dbsizeallocated'::text))))
     LEFT JOIN checkresults j ON (((id.inventoryid = j.inventoryid) AND (j.checkdate = ( SELECT max(j1.checkdate) AS max
           FROM checkresults j1
          WHERE ((j1.inventoryid = id.inventoryid) AND (j1.check_column = 'dbsizeused'::text)))) AND (j.check_column = 'dbsizeused'::text))))
     LEFT JOIN checkresults k ON (((id.inventoryid = k.inventoryid) AND (k.checkdate = ( SELECT max(k1.checkdate) AS max
           FROM checkresults k1
          WHERE ((k1.inventoryid = id.inventoryid) AND (k1.check_column = 'processespct'::text)))) AND (k.check_column = 'processespct'::text))))
     LEFT JOIN checkresults l ON (((id.inventoryid = l.inventoryid) AND (l.checkdate = ( SELECT max(l1.checkdate) AS max
           FROM checkresults l1
          WHERE ((l1.inventoryid = id.inventoryid) AND (l1.check_column = 'badfileloc'::text)))) AND (l.check_column = 'badfileloc'::text))))
     LEFT JOIN checkresults m ON (((id.inventoryid = m.inventoryid) AND (m.checkdate = ( SELECT max(m1.checkdate) AS max
           FROM checkresults m1
          WHERE ((m1.inventoryid = id.inventoryid) AND (m1.check_column = 'dbstatus'::text)))) AND (m.check_column = 'dbstatus'::text))))
     LEFT JOIN checkresults n ON (((id.inventoryid = n.inventoryid) AND (n.checkdate = ( SELECT max(n1.checkdate) AS max
           FROM checkresults n1
          WHERE ((n1.inventoryid = id.inventoryid) AND (n1.check_column = 'inoms'::text)))) AND (n.check_column = 'inoms'::text))))
  WHERE (id.decommissioned IS NULL)
  and id.targettype='Database'
  ORDER BY id.inventoryid;

ALTER TABLE public.lastcheck
    OWNER TO postgres;
