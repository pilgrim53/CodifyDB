----------------------------------
-- Drop commands if required
----------------------------------
DROP SCHEMA   CODIFY;
DROP VIEW     codify.lastcheck;
DROP TABLE    codify.checkresults;
DROP TABLE    codify.target;
DROP SEQUENCE codify.inventory_id;
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
    inventory_id integer,
    check_date timestamp without time zone,
    check_result text,
    check_column text
);


ALTER TABLE public.checkresults OWNER TO codify;

--
-- Name: inventory_id; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.inventory_id
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.inventory_id OWNER TO codify;

--
-- Name: target; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.target (
    inventory_id integer DEFAULT nextval('public.inventory_id'::regclass) NOT NULL,
    inventory_create date NOT NULL,
    db_created_date text,
    last_check_date timestamp without time zone,
    serial_number character varying(20),
    vendor character varying(50),
    instance_name character varying(50),
    hostname character varying(50),
    version character varying(50),
    home_dir character varying(255),
    owner character varying(50),
    port integer,
    status character varying(255),
    archivelog_mode character varying(50),
    blocksize integer,
    highlysensitiveinfo bit(1),
    database_type character varying(50),
    important_notes character varying(1000),
    role character varying(25),
    container character varying(15),
    decommissioned date,
    host_type text,
    standbydest text,
    os text,
    v_instance text,
    target_type text NOT NULL
);


ALTER TABLE public.target OWNER TO codify;

--
-- Name: COLUMN target.target_type; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.target.target_type IS 'Database,  Server, Other';


--
-- Name: target_rejects; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.target_rejects (
    inventory_id integer,
    inventorycreate date,
    last_check_date timestamp without time zone,
    vendor character varying(50),
    instance_name character varying(50),
    hostname character varying(50),
    home_dir character varying(255),
    owner character varying(50),
    port integer,
    status character varying(255),
    databasetype character varying(50),
    importantnotes character varying(1000)
);


ALTER TABLE public.target_rejects OWNER TO codify;

--
-- Name: lastcheck; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.lastcheck AS
 SELECT id.inventory_id,
    id.hostname,
    id.instance_name,
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
   FROM ((((((((((((((public.target id
     LEFT JOIN public.checkresults a ON (((id.inventory_id = a.inventory_id) AND (a.check_date = ( SELECT max(a1.check_date) AS max
           FROM public.checkresults a1
          WHERE ((a1.inventory_id = id.inventory_id) AND (a1.check_column = 'started'::text)))) AND (a.check_column = 'started'::text))))
     LEFT JOIN public.checkresults b ON (((id.inventory_id = b.inventory_id) AND (b.check_date = ( SELECT max(b1.check_date) AS max
           FROM public.checkresults b1
          WHERE ((b1.inventory_id = id.inventory_id) AND (b1.check_column = 'closedwallet'::text)))) AND (b.check_column = 'closedwallet'::text))))
     LEFT JOIN public.checkresults c ON (((id.inventory_id = c.inventory_id) AND (c.check_date = ( SELECT max(c1.check_date) AS max
           FROM public.checkresults c1
          WHERE ((c1.inventory_id = id.inventory_id) AND (c1.check_column = 'dbcaccess'::text)))) AND (c.check_column = 'dbcaccess'::text))))
     LEFT JOIN public.checkresults d ON (((id.inventory_id = d.inventory_id) AND (d.check_date = ( SELECT max(d1.check_date) AS max
           FROM public.checkresults d1
          WHERE ((d1.inventory_id = id.inventory_id) AND (d1.check_column = 'appsessions'::text)))) AND (d.check_column = 'appsessions'::text))))
     LEFT JOIN public.checkresults e ON (((id.inventory_id = e.inventory_id) AND (e.check_date = ( SELECT max(e1.check_date) AS max
           FROM public.checkresults e1
          WHERE ((e1.inventory_id = id.inventory_id) AND (e1.check_column = 'openmode'::text)))) AND (e.check_column = 'openmode'::text))))
     LEFT JOIN public.checkresults f ON (((id.inventory_id = f.inventory_id) AND (f.check_date = ( SELECT max(f1.check_date) AS max
           FROM public.checkresults f1
          WHERE ((f1.inventory_id = id.inventory_id) AND (f1.check_column = 'swrelease'::text)))) AND (f.check_column = 'swrelease'::text))))
     LEFT JOIN public.checkresults g ON (((id.inventory_id = g.inventory_id) AND (g.check_date = ( SELECT max(g1.check_date) AS max
           FROM public.checkresults g1
          WHERE ((g1.inventory_id = id.inventory_id) AND (g1.check_column = 'systemfree'::text)))) AND (g.check_column = 'systemfree'::text))))
     LEFT JOIN public.checkresults h ON (((id.inventory_id = h.inventory_id) AND (h.check_date = ( SELECT max(h1.check_date) AS max
           FROM public.checkresults h1
          WHERE ((h1.inventory_id = id.inventory_id) AND (h1.check_column = 'sysauxfree'::text)))) AND (h.check_column = 'sysauxfree'::text))))
     LEFT JOIN public.checkresults i ON (((id.inventory_id = i.inventory_id) AND (i.check_date = ( SELECT max(i1.check_date) AS max
           FROM public.checkresults i1
          WHERE ((i1.inventory_id = id.inventory_id) AND (i1.check_column = 'dbsizeallocated'::text)))) AND (i.check_column = 'dbsizeallocated'::text))))
     LEFT JOIN public.checkresults j ON (((id.inventory_id = j.inventory_id) AND (j.check_date = ( SELECT max(j1.check_date) AS max
           FROM public.checkresults j1
          WHERE ((j1.inventory_id = id.inventory_id) AND (j1.check_column = 'dbsizeused'::text)))) AND (j.check_column = 'dbsizeused'::text))))
     LEFT JOIN public.checkresults k ON (((id.inventory_id = k.inventory_id) AND (k.check_date = ( SELECT max(k1.check_date) AS max
           FROM public.checkresults k1
          WHERE ((k1.inventory_id = id.inventory_id) AND (k1.check_column = 'processespct'::text)))) AND (k.check_column = 'processespct'::text))))
     LEFT JOIN public.checkresults l ON (((id.inventory_id = l.inventory_id) AND (l.check_date = ( SELECT max(l1.check_date) AS max
           FROM public.checkresults l1
          WHERE ((l1.inventory_id = id.inventory_id) AND (l1.check_column = 'badfileloc'::text)))) AND (l.check_column = 'badfileloc'::text))))
     LEFT JOIN public.checkresults m ON (((id.inventory_id = m.inventory_id) AND (m.check_date = ( SELECT max(m1.check_date) AS max
           FROM public.checkresults m1
          WHERE ((m1.inventory_id = id.inventory_id) AND (m1.check_column = 'dbstatus'::text)))) AND (m.check_column = 'dbstatus'::text))))
     LEFT JOIN public.checkresults n ON (((id.inventory_id = n.inventory_id) AND (n.check_date = ( SELECT max(n1.check_date) AS max
           FROM public.checkresults n1
          WHERE ((n1.inventory_id = id.inventory_id) AND (n1.check_column = 'inoms'::text)))) AND (n.check_column = 'inoms'::text))))
  WHERE ((id.decommissioned IS NULL) AND (id.target_type = 'Database'::text))
  ORDER BY id.inventory_id;


ALTER TABLE public.lastcheck OWNER TO codify;

--
-- Name: servers; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.servers AS
 SELECT id.inventory_id,
    id.hostname,
    id.vendor,
    id.os,
    id.db_created_date AS created,
    id.serial_number,
    id.owner,
    id.host_type,
    a.check_result AS started,
    b.check_result AS osaccess
   FROM ((public.target id
     LEFT JOIN public.checkresults a ON (((id.inventory_id = a.inventory_id) AND (a.check_date = ( SELECT max(a1.check_date) AS max
           FROM public.checkresults a1
          WHERE ((a1.inventory_id = id.inventory_id) AND (a1.check_column = 'started'::text)))) AND (a.check_column = 'started'::text))))
     LEFT JOIN public.checkresults b ON (((id.inventory_id = b.inventory_id) AND (b.check_date = ( SELECT max(b1.check_date) AS max
           FROM public.checkresults b1
          WHERE ((b1.inventory_id = id.inventory_id) AND (b1.check_column = 'osaccess'::text)))) AND (b.check_column = 'osaccess'::text))))
  WHERE ((id.decommissioned IS NULL) AND (id.target_type = 'Server'::text))
  ORDER BY id.inventory_id;


ALTER TABLE public.servers OWNER TO codify;

--
-- Name: checklist checklist_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.checklist
    ADD CONSTRAINT checklist_pkey PRIMARY KEY (id);


--
-- Name: target target_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.target
    ADD CONSTRAINT target_pkey PRIMARY KEY (inventory_id);


--
-- Name: CR_Column; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "CR_Column" ON public.checkresults USING hash (check_column);


--
-- Name: RESULTS; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "RESULTS" ON public.checkresults USING btree (inventory_id, check_date, check_column) INCLUDE (inventory_id, check_date, check_column);


--
-- Name: check_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX check_date ON public.checkresults USING btree (check_date);


--
-- Name: check_inv; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX check_inv ON public.checkresults USING btree (inventory_id);


--
-- Name: inv_inst; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX inv_inst ON public.target USING btree (inventory_id, instance_name, hostname);


--
-- PostgreSQL database dump complete
--
