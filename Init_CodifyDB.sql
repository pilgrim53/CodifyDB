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
    handler text COLLATE pg_catalog."default",
    CONSTRAINT checklist_pkey PRIMARY KEY (id)
)

TABLESPACE pg_default;

ALTER TABLE public.checklist
    OWNER to codify;

--
-- Name: checkresults; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.check_results
(
    inventory_id integer,
    check_date timestamp without time zone,
    check_result text COLLATE pg_catalog."default",
    check_column text COLLATE pg_catalog."default"
)

TABLESPACE pg_default;

ALTER TABLE public.check_results
    OWNER to codify;

CREATE INDEX "CR_Column"
    ON public.check_results USING hash
    (check_column COLLATE pg_catalog."default")
    TABLESPACE pg_default;
-- Index: RESULTS

CREATE INDEX "RESULTS"
    ON public.check_results USING btree
    (inventory_id ASC NULLS LAST, check_date ASC NULLS LAST, check_column COLLATE pg_catalog."default" ASC NULLS LAST)
    INCLUDE(inventory_id, check_date, check_column)
    TABLESPACE pg_default;
-- Index: check_date

CREATE INDEX check_date
    ON public.check_results USING btree
    (check_date ASC NULLS LAST)
    TABLESPACE pg_default;
-- Index: check_inv

CREATE INDEX check_inv
    ON public.check_results USING btree
    (inventory_id ASC NULLS LAST)
    TABLESPACE pg_default;
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

CREATE TABLE public.target
(
    inventory_id integer NOT NULL DEFAULT nextval('public.inventory_id'::regclass),
    inventory_create date NOT NULL,
    db_created_date text COLLATE pg_catalog."default",
    last_check_date timestamp without time zone,
    serial_number character varying(20) COLLATE pg_catalog."default",
    vendor character varying(50) COLLATE pg_catalog."default",
    instance_name character varying(50) COLLATE pg_catalog."default",
    hostname character varying(50) COLLATE pg_catalog."default",
    version character varying(50) COLLATE pg_catalog."default",
    home_dir character varying(255) COLLATE pg_catalog."default",
    owner character varying(50) COLLATE pg_catalog."default",
    port integer,
    status character varying(255) COLLATE pg_catalog."default",
    archivelog_mode character varying(50) COLLATE pg_catalog."default",
    blocksize integer,
    highlysensitiveinfo bit(1),
    database_type character varying(50) COLLATE pg_catalog."default",
    important_notes character varying(1000) COLLATE pg_catalog."default",
    role character varying(25) COLLATE pg_catalog."default",
    container character varying(15) COLLATE pg_catalog."default",
    decommissioned date,
    host_type text COLLATE pg_catalog."default",
    standby_dest text COLLATE pg_catalog."default",
    os text COLLATE pg_catalog."default",
    v_instance text COLLATE pg_catalog."default",
    target_type text COLLATE pg_catalog."default" NOT NULL,
    support_tier text COLLATE pg_catalog."default",
    CONSTRAINT dbc_target_pkey PRIMARY KEY (inventory_id),
    CONSTRAINT "Instance" UNIQUE (hostname, instance_name, container)
)

TABLESPACE pg_default;

ALTER TABLE public.target
    OWNER to codify;

GRANT ALL ON TABLE public.target TO postgres;

CREATE INDEX inv_inst
    ON public.target USING btree
    (inventory_id ASC NULLS LAST, instance_name COLLATE pg_catalog."default" ASC NULLS LAST, hostname COLLATE pg_catalog."default" ASC NULLS LAST)
    TABLESPACE pg_default;

--
-- Name: COLUMN target.target_type; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.target.target_type
    IS 'Database,  Server, Other';

--
-- Name: target_rejects; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.target_rejects
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

ALTER TABLE public.target_rejects
    OWNER to codify;

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
     LEFT JOIN public.check_results a ON (((id.inventory_id = a.inventory_id) AND (a.check_date = ( SELECT max(a1.check_date) AS max
           FROM public.check_results a1
          WHERE ((a1.inventory_id = id.inventory_id) AND (a1.check_column = 'started'::text)))) AND (a.check_column = 'started'::text))))
     LEFT JOIN public.check_results b ON (((id.inventory_id = b.inventory_id) AND (b.check_date = ( SELECT max(b1.check_date) AS max
           FROM public.check_results b1
          WHERE ((b1.inventory_id = id.inventory_id) AND (b1.check_column = 'closedwallet'::text)))) AND (b.check_column = 'closedwallet'::text))))
     LEFT JOIN public.check_results c ON (((id.inventory_id = c.inventory_id) AND (c.check_date = ( SELECT max(c1.check_date) AS max
           FROM public.check_results c1
          WHERE ((c1.inventory_id = id.inventory_id) AND (c1.check_column = 'dbcaccess'::text)))) AND (c.check_column = 'dbcaccess'::text))))
     LEFT JOIN public.check_results d ON (((id.inventory_id = d.inventory_id) AND (d.check_date = ( SELECT max(d1.check_date) AS max
           FROM public.check_results d1
          WHERE ((d1.inventory_id = id.inventory_id) AND (d1.check_column = 'appsessions'::text)))) AND (d.check_column = 'appsessions'::text))))
     LEFT JOIN public.check_results e ON (((id.inventory_id = e.inventory_id) AND (e.check_date = ( SELECT max(e1.check_date) AS max
           FROM public.check_results e1
          WHERE ((e1.inventory_id = id.inventory_id) AND (e1.check_column = 'openmode'::text)))) AND (e.check_column = 'openmode'::text))))
     LEFT JOIN public.check_results f ON (((id.inventory_id = f.inventory_id) AND (f.check_date = ( SELECT max(f1.check_date) AS max
           FROM public.check_results f1
          WHERE ((f1.inventory_id = id.inventory_id) AND (f1.check_column = 'swrelease'::text)))) AND (f.check_column = 'swrelease'::text))))
     LEFT JOIN public.check_results g ON (((id.inventory_id = g.inventory_id) AND (g.check_date = ( SELECT max(g1.check_date) AS max
           FROM public.check_results g1
          WHERE ((g1.inventory_id = id.inventory_id) AND (g1.check_column = 'systemfree'::text)))) AND (g.check_column = 'systemfree'::text))))
     LEFT JOIN public.check_results h ON (((id.inventory_id = h.inventory_id) AND (h.check_date = ( SELECT max(h1.check_date) AS max
           FROM public.check_results h1
          WHERE ((h1.inventory_id = id.inventory_id) AND (h1.check_column = 'sysauxfree'::text)))) AND (h.check_column = 'sysauxfree'::text))))
     LEFT JOIN public.check_results i ON (((id.inventory_id = i.inventory_id) AND (i.check_date = ( SELECT max(i1.check_date) AS max
           FROM public.check_results i1
          WHERE ((i1.inventory_id = id.inventory_id) AND (i1.check_column = 'dbsizeallocated'::text)))) AND (i.check_column = 'dbsizeallocated'::text))))
     LEFT JOIN public.check_results j ON (((id.inventory_id = j.inventory_id) AND (j.check_date = ( SELECT max(j1.check_date) AS max
           FROM public.check_results j1
          WHERE ((j1.inventory_id = id.inventory_id) AND (j1.check_column = 'dbsizeused'::text)))) AND (j.check_column = 'dbsizeused'::text))))
     LEFT JOIN public.check_results k ON (((id.inventory_id = k.inventory_id) AND (k.check_date = ( SELECT max(k1.check_date) AS max
           FROM public.check_results k1
          WHERE ((k1.inventory_id = id.inventory_id) AND (k1.check_column = 'processespct'::text)))) AND (k.check_column = 'processespct'::text))))
     LEFT JOIN public.check_results l ON (((id.inventory_id = l.inventory_id) AND (l.check_date = ( SELECT max(l1.check_date) AS max
           FROM public.check_results l1
          WHERE ((l1.inventory_id = id.inventory_id) AND (l1.check_column = 'badfileloc'::text)))) AND (l.check_column = 'badfileloc'::text))))
     LEFT JOIN public.check_results m ON (((id.inventory_id = m.inventory_id) AND (m.check_date = ( SELECT max(m1.check_date) AS max
           FROM public.check_results m1
          WHERE ((m1.inventory_id = id.inventory_id) AND (m1.check_column = 'dbstatus'::text)))) AND (m.check_column = 'dbstatus'::text))))
     LEFT JOIN public.check_results n ON (((id.inventory_id = n.inventory_id) AND (n.check_date = ( SELECT max(n1.check_date) AS max
           FROM public.check_results n1
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
     LEFT JOIN public.check_results a ON (((id.inventory_id = a.inventory_id) AND (a.check_date = ( SELECT max(a1.check_date) AS max
           FROM public.check_results a1
          WHERE ((a1.inventory_id = id.inventory_id) AND (a1.check_column = 'started'::text)))) AND (a.check_column = 'started'::text))))
     LEFT JOIN public.check_results b ON (((id.inventory_id = b.inventory_id) AND (b.check_date = ( SELECT max(b1.check_date) AS max
           FROM public.check_results b1
          WHERE ((b1.inventory_id = id.inventory_id) AND (b1.check_column = 'osaccess'::text)))) AND (b.check_column = 'osaccess'::text))))
  WHERE ((id.decommissioned IS NULL) AND (id.target_type = 'Server'::text))
  ORDER BY id.inventory_id;


ALTER TABLE public.servers OWNER TO codify;


ALTER TABLE public.servers
    OWNER TO codify;

--
-- PostgreSQL database dump complete
--
