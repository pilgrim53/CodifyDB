-- Table: public.notifications

-- DROP TABLE public.notifications;

CREATE TABLE public.notifications
(
    id integer NOT NULL,
    threshold text COLLATE pg_catalog."default",
    result_column text COLLATE pg_catalog."default",
    frequency text COLLATE pg_catalog."default",
    CONSTRAINT notifications_pk PRIMARY KEY (id)
)

TABLESPACE pg_default;

ALTER TABLE public.notifications
    OWNER to codify;
    
    
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

--
-- Data for Name: notifications; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.notifications (id, threshold, result_column, frequency) FROM stdin;
1        < 1000 system_free     HOURLY
2        < 1000 sysaux_free     HOURLY
3       != 0    pdb_violations  HOURLY
4       > 5     pdb_count       HOURLY
5       >1      closed_wallet   HOURLY
\.

