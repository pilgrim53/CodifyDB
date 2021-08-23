----------------------------------
-- Drop commands if required
----------------------------------
DROP VIEW public.lastcheck;
DROP TABLE public.checkresults;
DROP TABLE public.dbc_target;
DROP SEQUENCE public.inventoryid;
DROP INDEX public.inv_inst;
DROP INDEX public."CR_Column";
DROP INDEX public.check_date;
DROP INDEX public.check_inv;
DROP TABLE public.checklist;
DROP TABLE public.dbc_target_rejects;
----------------------------------



-- SEQUENCE: public.inventoryid

CREATE SEQUENCE public.inventoryid
    INCREMENT 1
    START 1
    MINVALUE 1
    CACHE 1;

ALTER SEQUENCE public.inventoryid
    OWNER TO postgres;

-- Table: public.dbc_target

CREATE TABLE public.dbc_target
(
    inventoryid integer NOT NULL DEFAULT nextval('inventoryid'::regclass),
    inventorycreate date NOT NULL,
    dbcreateddate date,
    lastcheckdate timestamp without time zone,
    dbid character varying(20) COLLATE pg_catalog."default",
    vendor character varying(50) COLLATE pg_catalog."default",
    instancename character varying(50) COLLATE pg_catalog."default",
    hostname character varying(50) COLLATE pg_catalog."default",
    version character varying(50) COLLATE pg_catalog."default",
    homedirectory character varying(255) COLLATE pg_catalog."default",
    owner character varying(50) COLLATE pg_catalog."default",
    port integer,
    status character varying(255) COLLATE pg_catalog."default",
    archivelogmode character varying(50) COLLATE pg_catalog."default",
    blocksize integer,
    highlysensitiveinfo bit(1),
    databasetype character varying(50) COLLATE pg_catalog."default",
    importantnotes character varying(1000) COLLATE pg_catalog."default",
    role character varying(25) COLLATE pg_catalog."default",
    container character varying(15) COLLATE pg_catalog."default",
    in_oms "char",
    decommissioned date,
    dbora character varying(25) COLLATE pg_catalog."default",
    hosttype text COLLATE pg_catalog."default",
    standbydest text COLLATE pg_catalog."default",
    os text COLLATE pg_catalog."default",
    v_instance text COLLATE pg_catalog."default",
    CONSTRAINT dbc_target_pkey PRIMARY KEY (inventoryid),
    CONSTRAINT "DBC_Target" UNIQUE (instancename, hostname, container)
)

TABLESPACE pg_default;

ALTER TABLE public.dbc_target
    OWNER to postgres;

GRANT ALL ON TABLE public.dbc_target TO postgres;

-- Index: inv_inst

CREATE INDEX inv_inst
    ON public.dbc_target USING btree
    (inventoryid ASC NULLS LAST, instancename COLLATE pg_catalog."default" ASC NULLS LAST, hostname COLLATE pg_catalog."default" ASC NULLS LAST)
    TABLESPACE pg_default;

-- Table: public.checkresults

CREATE TABLE public.checkresults
(
    inventoryid integer,
    checkdate timestamp without time zone,
    check_result text COLLATE pg_catalog."default",
    check_column text COLLATE pg_catalog."default"
)

TABLESPACE pg_default;

ALTER TABLE public.checkresults
    OWNER to postgres;

-- Index: CR_Column

CREATE INDEX "CR_Column"
    ON public.checkresults USING hash
    (check_column COLLATE pg_catalog."default")
    TABLESPACE pg_default;

-- Index: check_date

CREATE INDEX check_date
    ON public.checkresults USING btree
    (checkdate ASC NULLS LAST)
    TABLESPACE pg_default;

-- Index: check_inv

CREATE INDEX check_inv
    ON public.checkresults USING btree
    (inventoryid ASC NULLS LAST)
    TABLESPACE pg_default;

--- View: public.lastcheck

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
  ORDER BY id.inventoryid;

ALTER TABLE public.lastcheck
    OWNER TO postgres;


-- Table: public.dbc_target_rejects

CREATE TABLE public.dbc_target_rejects
(
    inventoryid integer,
    inventorycreate date,
    lastcheckdate timestamp without time zone,
    vendor character varying(50) COLLATE pg_catalog."default",
    instancename character varying(50) COLLATE pg_catalog."default",
    hostname character varying(50) COLLATE pg_catalog."default",
    homedirectory character varying(255) COLLATE pg_catalog."default",
    owner character varying(50) COLLATE pg_catalog."default",
    port integer,
    status character varying(255) COLLATE pg_catalog."default",
    databasetype character varying(50) COLLATE pg_catalog."default",
    importantnotes character varying(1000) COLLATE pg_catalog."default"
)

TABLESPACE pg_default;

ALTER TABLE public.dbc_target_rejects
    OWNER to postgres;

-- Table: public.checklist

CREATE TABLE public.checklist
(
    id integer NOT NULL,
    vendor text COLLATE pg_catalog."default",
    frequency text COLLATE pg_catalog."default",
    check_type text COLLATE pg_catalog."default",
    description text COLLATE pg_catalog."default",
    check_command text COLLATE pg_catalog."default",
    result_column text COLLATE pg_catalog."default",
    priority integer,
    CONSTRAINT checklist_pkey PRIMARY KEY (id)
)

TABLESPACE pg_default;

ALTER TABLE public.checklist
    OWNER to postgres;

---------------------------------------------

-- iN OMS Repository
connect / as sysdba
Alter user cloud_dbc enable editions;
create edition Edition_V1;
grant select on sysman.MGMT$AGENTS_MONITORING_TARGETS to cloud_dbc;

connect cloud_dbc

   CREATE OR REPLACE VIEW OMS_TARGETS (TARGET, HOST) as 
    select SUBSTR(target, Instr(target, '_', 1, 1)+1), host from 
  (select upper(NVL(SUBSTR(target_name, 1, Instr(target_name, '_', 1, 1)-1), target_name)) TARGET, 
          upper(SUBSTR(agent_host_name, 1, Instr(agent_host_name, '.', 1, 1)-1))  HOST 
     from sysman.MGMT$AGENTS_MONITORING_TARGETS 
    where target_type = 'oracle_database'
UNION
select  distinct upper(NVL(SUBSTR(target_name, Instr(target_name, '_', 1, 1)+1), target_name)) TARGET, 
       upper(SUBSTR(agent_host_name, 1, Instr(agent_host_name, '.', 1, 1)-1))  HOST 
     from sysman.MGMT$AGENTS_MONITORING_TARGETS 
    where target_type = 'oracle_pdb')
    order by host, target
    with read only;

