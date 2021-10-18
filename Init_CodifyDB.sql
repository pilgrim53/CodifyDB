----------------------------------
-- Drop commands if required
----------------------------------
DROP SCHEMA   CODIFY;
DROP VIEW     codify.lastcheck;
DROP TABLE    codify.checkresults;
DROP TABLE    codify.target;
DROP SEQUENCE codify.inventoryid;
DROP INDEX    codify.inv_inst;
DROP INDEX    codify.CR_Column;
DROP INDEX    codify.check_date;
DROP INDEX    codify.check_inv;
DROP TABLE    codify.checklist;
DROP TABLE    codify.target_rejects;
----------------------------------

DO
$do$
BEGIN
   IF NOT EXISTS (
      SELECT FROM pg_catalog.pg_roles  -- SELECT list can be empty for this
      WHERE  rolname = 'codify') 
	  THEN
      CREATE ROLE codify superuser;
	  GRANT codify to postgres;
	  ALTER ROLE codify with login PASSWORD 'codify_2021';
   END IF;
END
$do$;

CREATE SCHEMA codify AUTHORIZATION codify;

--
-- PostgreSQL database dump
--

-- Dumped from database version 13.1
-- Dumped by pg_dump version 13.1

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: checklist; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.checklist (
    id integer NOT NULL,
    vendor text,
    frequency text,
    check_type text,
    description text,
    check_command text,
    result_column text,
    priority integer,
    handler text
);


ALTER TABLE public.checklist OWNER TO codify;

--
-- Name: checkresults; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.checkresults (
    inventoryid integer,
    checkdate timestamp without time zone,
    check_result text,
    check_column text
);


ALTER TABLE public.checkresults OWNER TO codify;

--
-- Name: inventoryid; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.inventoryid
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.inventoryid OWNER TO codify;

--
-- Name: dbc_target; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.dbc_target (
    inventoryid integer DEFAULT nextval('public.inventoryid'::regclass) NOT NULL,
    inventorycreate date NOT NULL,
    dbcreateddate text,
    lastcheckdate timestamp without time zone,
    serialnumber character varying(20),
    vendor character varying(50),
    instancename character varying(50),
    hostname character varying(50),
    version character varying(50),
    homedirectory character varying(255),
    owner character varying(50),
    port integer,
    status character varying(255),
    archivelogmode character varying(50),
    blocksize integer,
    highlysensitiveinfo bit(1),
    databasetype character varying(50),
    importantnotes character varying(1000),
    role character varying(25),
    container character varying(15),
    decommissioned date,
    hosttype text,
    standbydest text,
    os text,
    v_instance text,
    targettype text NOT NULL
);


ALTER TABLE public.dbc_target OWNER TO codify;

--
-- Name: COLUMN dbc_target.targettype; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.dbc_target.targettype IS 'Database,  Server, Other';


--
-- Name: dbc_target_rejects; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.dbc_target_rejects (
    inventoryid integer,
    inventorycreate date,
    lastcheckdate timestamp without time zone,
    vendor character varying(50),
    instancename character varying(50),
    hostname character varying(50),
    homedirectory character varying(255),
    owner character varying(50),
    port integer,
    status character varying(255),
    databasetype character varying(50),
    importantnotes character varying(1000)
);


ALTER TABLE public.dbc_target_rejects OWNER TO codify;

--
-- Name: lastcheck; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.lastcheck AS
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
   FROM ((((((((((((((public.dbc_target id
     LEFT JOIN public.checkresults a ON (((id.inventoryid = a.inventoryid) AND (a.checkdate = ( SELECT max(a1.checkdate) AS max
           FROM public.checkresults a1
          WHERE ((a1.inventoryid = id.inventoryid) AND (a1.check_column = 'started'::text)))) AND (a.check_column = 'started'::text))))
     LEFT JOIN public.checkresults b ON (((id.inventoryid = b.inventoryid) AND (b.checkdate = ( SELECT max(b1.checkdate) AS max
           FROM public.checkresults b1
          WHERE ((b1.inventoryid = id.inventoryid) AND (b1.check_column = 'closedwallet'::text)))) AND (b.check_column = 'closedwallet'::text))))
     LEFT JOIN public.checkresults c ON (((id.inventoryid = c.inventoryid) AND (c.checkdate = ( SELECT max(c1.checkdate) AS max
           FROM public.checkresults c1
          WHERE ((c1.inventoryid = id.inventoryid) AND (c1.check_column = 'dbcaccess'::text)))) AND (c.check_column = 'dbcaccess'::text))))
     LEFT JOIN public.checkresults d ON (((id.inventoryid = d.inventoryid) AND (d.checkdate = ( SELECT max(d1.checkdate) AS max
           FROM public.checkresults d1
          WHERE ((d1.inventoryid = id.inventoryid) AND (d1.check_column = 'appsessions'::text)))) AND (d.check_column = 'appsessions'::text))))
     LEFT JOIN public.checkresults e ON (((id.inventoryid = e.inventoryid) AND (e.checkdate = ( SELECT max(e1.checkdate) AS max
           FROM public.checkresults e1
          WHERE ((e1.inventoryid = id.inventoryid) AND (e1.check_column = 'openmode'::text)))) AND (e.check_column = 'openmode'::text))))
     LEFT JOIN public.checkresults f ON (((id.inventoryid = f.inventoryid) AND (f.checkdate = ( SELECT max(f1.checkdate) AS max
           FROM public.checkresults f1
          WHERE ((f1.inventoryid = id.inventoryid) AND (f1.check_column = 'swrelease'::text)))) AND (f.check_column = 'swrelease'::text))))
     LEFT JOIN public.checkresults g ON (((id.inventoryid = g.inventoryid) AND (g.checkdate = ( SELECT max(g1.checkdate) AS max
           FROM public.checkresults g1
          WHERE ((g1.inventoryid = id.inventoryid) AND (g1.check_column = 'systemfree'::text)))) AND (g.check_column = 'systemfree'::text))))
     LEFT JOIN public.checkresults h ON (((id.inventoryid = h.inventoryid) AND (h.checkdate = ( SELECT max(h1.checkdate) AS max
           FROM public.checkresults h1
          WHERE ((h1.inventoryid = id.inventoryid) AND (h1.check_column = 'sysauxfree'::text)))) AND (h.check_column = 'sysauxfree'::text))))
     LEFT JOIN public.checkresults i ON (((id.inventoryid = i.inventoryid) AND (i.checkdate = ( SELECT max(i1.checkdate) AS max
           FROM public.checkresults i1
          WHERE ((i1.inventoryid = id.inventoryid) AND (i1.check_column = 'dbsizeallocated'::text)))) AND (i.check_column = 'dbsizeallocated'::text))))
     LEFT JOIN public.checkresults j ON (((id.inventoryid = j.inventoryid) AND (j.checkdate = ( SELECT max(j1.checkdate) AS max
           FROM public.checkresults j1
          WHERE ((j1.inventoryid = id.inventoryid) AND (j1.check_column = 'dbsizeused'::text)))) AND (j.check_column = 'dbsizeused'::text))))
     LEFT JOIN public.checkresults k ON (((id.inventoryid = k.inventoryid) AND (k.checkdate = ( SELECT max(k1.checkdate) AS max
           FROM public.checkresults k1
          WHERE ((k1.inventoryid = id.inventoryid) AND (k1.check_column = 'processespct'::text)))) AND (k.check_column = 'processespct'::text))))
     LEFT JOIN public.checkresults l ON (((id.inventoryid = l.inventoryid) AND (l.checkdate = ( SELECT max(l1.checkdate) AS max
           FROM public.checkresults l1
          WHERE ((l1.inventoryid = id.inventoryid) AND (l1.check_column = 'badfileloc'::text)))) AND (l.check_column = 'badfileloc'::text))))
     LEFT JOIN public.checkresults m ON (((id.inventoryid = m.inventoryid) AND (m.checkdate = ( SELECT max(m1.checkdate) AS max
           FROM public.checkresults m1
          WHERE ((m1.inventoryid = id.inventoryid) AND (m1.check_column = 'dbstatus'::text)))) AND (m.check_column = 'dbstatus'::text))))
     LEFT JOIN public.checkresults n ON (((id.inventoryid = n.inventoryid) AND (n.checkdate = ( SELECT max(n1.checkdate) AS max
           FROM public.checkresults n1
          WHERE ((n1.inventoryid = id.inventoryid) AND (n1.check_column = 'inoms'::text)))) AND (n.check_column = 'inoms'::text))))
  WHERE ((id.decommissioned IS NULL) AND (id.targettype = 'Database'::text))
  ORDER BY id.inventoryid;


ALTER TABLE public.lastcheck OWNER TO codify;

--
-- Name: servers; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.servers AS
 SELECT id.inventoryid,
    id.hostname,
    id.vendor,
    id.os,
    id.dbcreateddate AS created,
    id.serialnumber,
    id.owner,
    id.hosttype,
    a.check_result AS started,
    b.check_result AS osaccess
   FROM ((public.dbc_target id
     LEFT JOIN public.checkresults a ON (((id.inventoryid = a.inventoryid) AND (a.checkdate = ( SELECT max(a1.checkdate) AS max
           FROM public.checkresults a1
          WHERE ((a1.inventoryid = id.inventoryid) AND (a1.check_column = 'started'::text)))) AND (a.check_column = 'started'::text))))
     LEFT JOIN public.checkresults b ON (((id.inventoryid = b.inventoryid) AND (b.checkdate = ( SELECT max(b1.checkdate) AS max
           FROM public.checkresults b1
          WHERE ((b1.inventoryid = id.inventoryid) AND (b1.check_column = 'osaccess'::text)))) AND (b.check_column = 'osaccess'::text))))
  WHERE ((id.decommissioned IS NULL) AND (id.targettype = 'Server'::text))
  ORDER BY id.inventoryid;


ALTER TABLE public.servers OWNER TO codify;

--
-- Name: checklist checklist_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.checklist
    ADD CONSTRAINT checklist_pkey PRIMARY KEY (id);


--
-- Name: dbc_target dbc_target_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.dbc_target
    ADD CONSTRAINT dbc_target_pkey PRIMARY KEY (inventoryid);


--
-- Name: CR_Column; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "CR_Column" ON public.checkresults USING hash (check_column);


--
-- Name: RESULTS; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "RESULTS" ON public.checkresults USING btree (inventoryid, checkdate, check_column) INCLUDE (inventoryid, checkdate, check_column);


--
-- Name: check_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX check_date ON public.checkresults USING btree (checkdate);


--
-- Name: check_inv; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX check_inv ON public.checkresults USING btree (inventoryid);


--
-- Name: inv_inst; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX inv_inst ON public.dbc_target USING btree (inventoryid, instancename, hostname);


--
-- PostgreSQL database dump complete
--
