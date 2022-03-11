#!/bin/bash
# set -e
export PGPASSWORD=$POSTGRES_PASSWORD;
psql -v ON_ERROR_STOP=0 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
  \connect $APP_DB_NAME $APP_DB_USER



SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
-- SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;
SET default_tablespace = '';
SET default_table_access_method = heap;


CREATE INDEX "CR_Column"
    ON check_results USING hash
    (check_column COLLATE pg_catalog."default")
    TABLESPACE pg_default;
-- Index: RESULTS

-- DROP INDEX "RESULTS";

CREATE INDEX "RESULTS"
    ON check_results USING btree
    (inventory_id ASC NULLS LAST, check_date ASC NULLS LAST, check_column COLLATE pg_catalog."default" ASC NULLS LAST)
    INCLUDE(inventory_id, check_date, check_column)
    TABLESPACE pg_default;
-- Index: check_date

-- DROP INDEX check_date;

CREATE INDEX check_date
    ON check_results USING btree
    (check_date ASC NULLS LAST)
    TABLESPACE pg_default;
-- Index: check_inv

-- DROP INDEX check_inv;

CREATE INDEX check_inv
    ON check_results USING btree
    (inventory_id ASC NULLS LAST)
    TABLESPACE pg_default;

--
-- Name: lastcheck; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW lastcheck AS
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


ALTER TABLE lastcheck OWNER TO codify;

--
-- Name: servers; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW servers AS
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
   FROM ((targets id
     LEFT JOIN check_results a ON (((id.inventory_id = a.inventory_id) AND (a.check_date = ( SELECT max(a1.check_date) AS max
           FROM check_results a1
          WHERE ((a1.inventory_id = id.inventory_id) AND (a1.check_column = 'started'::text)))) AND (a.check_column = 'started'::text))))
     LEFT JOIN check_results b ON (((id.inventory_id = b.inventory_id) AND (b.check_date = ( SELECT max(b1.check_date) AS max
           FROM check_results b1
          WHERE ((b1.inventory_id = id.inventory_id) AND (b1.check_column = 'osaccess'::text)))) AND (b.check_column = 'osaccess'::text))))
  WHERE ((id.decommissioned IS NULL) AND (id.target_type = 'Server'::text))
  ORDER BY id.inventory_id;


ALTER TABLE servers OWNER TO codify;


ALTER TABLE servers
    OWNER TO codify;



-- This section should be completed in Django
--
-- Name: checklist; Type: TABLE; Schema: public; Owner: postgres 
--

ALTER TABLE codify.checklist
    OWNER to codify;


--
--
-- Name: targets; Type: TABLE; Schema: public; Owner: postgres
--

ALTER TABLE targets
    OWNER to codify;

CREATE INDEX inv_inst
    ON targets USING btree
    (inventory_id ASC NULLS LAST, instance_name COLLATE pg_catalog."default" ASC NULLS LAST, hostname COLLATE pg_catalog."default" ASC NULLS LAST)
    TABLESPACE pg_default;

COMMENT ON COLUMN targets.target_type
    IS 'Database,  Server, Other';

COPY codify.notifications (id, threshold, result_column, frequency) FROM stdin;
1        < 1000 system_free     HOURLY
2        < 1000 sysaux_free     HOURLY
3       != 0    pdb_violations  HOURLY
4       > 5     pdb_count       HOURLY
5       >1      closed_wallet   HOURLY
\.


Copy codify.checklist from stdin;
1	ORACLE	HOURLY	DB	Start Time	select startup_time from v$instance	started	1	Oracle	None	Y
2	ORACLE	DAILY	OMS	in OMS?	select case when exists ( select 1 from oms_targets where upper(host) = '{}' and upper(target) = '{}' )  then 'Y' else 'N' end as rec_exists from dual	inoms	9	OMS	None	Y
3	ORACLE	DAILY	DB	Description	select open_mode from v$database	openmode	1	Oracle	None	Y
4	ORACLE	DAILY	DB	Description	select sum(bytes) from dba_data_files	dbsizeallocated	1	Oracle	None	Y
5	ORACLE	DAILY	DB	Database Size Used (bytes)	select sum(bytes) from dba_segments	dbsizeused	1	Oracle	None	Y
6	ORACLE	DAILY	DB	Description	select 'Y' from dual	dbcaccess	1	Oracle	None	Y
7	ORACLE	DAILY	DB	Description	select count(*) from v$encryption_wallet where status = 'CLOSED' 	closedwallet	1	Oracle	None	Y
8	ORACLE	HOURLY	DB	Percentage of Max Proccesses currently in use	select (current_utilization / (decode(to_number(limit_value),0,1,to_number(limit_value)))*100) from v$resource_limit where resource_name = 'processes'	processespct	1	Oracle	None	Y
9	ORACLE	WEEKLY!	DB	Description	select count(*) FILES from dba_data_files where file_name not like '%oradata%' union all select count(*) FILES from dba_temp_files where file_name not like '%oradata%'	badfileloc	1	Oracle	None	Y
10	ORACLE	DAILY	DB	Description	select count(*) from V$SESSION_CONNECT_INFO c, v$session a where a.sid = c.sid and c.osuser <> 'oraoemag' and program not like '%caddld-590%' 	appsessions	1	Oracle	None	Y
11	ORACLE	WEEKLY	OS	Oracle Patches	opatch lspatches | grep -i Database | grep -v Java | grep -v "^$" | awk -F':' '{print $2}' | grep -v "^$"   2>/dev/null ; opatch lspatches | grep -i Database | grep -v Java | grep -v "^$" | awk -F':' '{print $2}' | grep -v "^$"  	swrelease	9	ssh	None	Y
12	ORACLE	DAILY	DB	SYSTEM Free Space	select nvl(sum(bytes),0) from dba_tablespaces t, dba_free_space f where t.tablespace_name  = f.tablespace_name (+) and t.tablespace_name = 'SYSTEM' group by t.tablespace_name	systemfree	1	Oracle	None	Y
13	ORACLE	DAILY	DB	SYSAUX Free Space	select nvl(sum(bytes),0) from dba_tablespaces t, dba_free_space f where t.tablespace_name  = f.tablespace_name (+) and t.tablespace_name = 'SYSAUX' group by t.tablespace_name	sysauxfree	1	Oracle	None	Y
14	ALL	HOURLY	OS	Physical vs Hardware	 dmesg | grep "Hardware name:" | head -n 1 | awk -F":" '{print $2}'	hosttype	9	ssh	None	Y
15	ORACLE	DAILY	DB	PDB Violations	select CASE when substr(version,0,instr(version,'.')-1) > 11\nthen ( select to_char( count(*) ) from pdb_plug_in_violations where status <>'RESOLVED' and message not like '%CDB installed version%' )\nelse '0'\nend as pdbviolations from v$instance	pdbviolations	1	Oracle	None	Y
16	ORACLE	WEEKLY!	OS	/etc/init.d/dbora installed 	if [ ! -f /etc/init.d/dbora ];  then echo \\"NONE\\" ; else grep Version /etc/init.d/dbora | sed s/#//g ; fi	dbora	9	ssh	None	Y
17	ORACLE	DBC_TARGET	OS	get Oracle Home from /etc/oratab	grep -i " + instance + ": /etc/oratab | awk -F':' '{print $2}' | head -n 1	homedirectory	9	ssh	None	Y
18	ORACLE	HC	DB	Availability	select 'Y' from dual	dbcaccess	1	Oracle	None	Y
19	ALL	ONCE	OS	email list	sed -i 's/^EMAIL=.*/EMAIL="BellITCloudDBC@bell.ca"/'  OraParameters.ksh	email	9	ssh	None	Y
20	ORACLE	TARGET	DB	Database Instance Name	select upper(instance_name) from v$instance	v_instance	1	Oracle	None	Y
21	ORACLE	DISABLED	DB	DB Host Name	select nvl(substr(upper(host_name), 0, instr(host_name,'.')-1), upper(host_name)) from v$instance;	hostname	1	Oracle	None	Y
22	ORACLE	TARGET	DB	Creation Date for DB	select to_char(created, 'YYYY-MM-DD') from v$database	dbcreateddate	1	Oracle	None	Y
23	OACLE	TARGET	DB	Database ID	select dbid from v$database	serialnumber	1	Oracle	None	Y
24	ORACLE	TARGET	DB	Software Version	select version from v$instance	version	1	Oracle	None	Y
25	ORACLE	TARGET	DB	Archive Log Mode	select log_mode from v$database	archivelogmode	1	Oracle	None	Y
26	ORACLE	TARGET	DB	Instance Status	select status from v$instance	status	1	Oracle	None	Y
27	ORACLE	TARGET	DB	Database Role	select database_role from v$database	role	1	Oracle	None	Y
28	ORACLE	TARGET	DB	DB Block Size	select value from v$parameter where name ='db_block_size'	blocksize	1	Oracle	None	Y
29	ORACLE	TARGET	DB	Oracle Owner FID	select distinct(username) from v$process where background=1 	owner	1	Oracle	None	Y
30	ORACLE	TARGET	DB	Container Name	select CASE when substr(version,0,instr(version,'.')-1) > 11\n                                     then case\n                                          when SYS_CONTEXT('USERENV','CON_NAME') = instance_name\n                                          then 'STANDALONE'\n                                          else SYS_CONTEXT('USERENV','CON_NAME')\n                                          end\n                                     else 'STANDALONE'\n                                     end as container from v$instance	container	1	Oracle	None	Y
31	ORACLE	TARGET	DB	Oracle_Home Directory	select CASE when substr(version,0,instr(version,'.')-1) > 11\n                                                                           then SYS_CONTEXT('USERENV','ORACLE_HOME')\n                                                                           else 'UNKNOWN'\n                                                          end as oracle_home from v$instance	homedirectory	9	Oracle	None	Y
32	ORACLE	TARGET	OS	Oracle_Home Directory	. ./.bash_profile 2>&1>/dev/null;   if [ -x "${ORACLE_HOME}"  ] ; then echo "${ORACLE_HOME}" ; else  grep -i "^${ORACLE_SID}:" /etc/oratab | awk -F':' '{print $2}' | head -n 1  ;  fi	homedirectory	1	ssh	None	Y
33	ALL	TARGET	OS	Server OS Type	uname -rs	os	9	ssh	None	Y
34	ORACLE	WEEKLY	DB	Count the # of PDBS	select CASE when substr(version,0,instr(version,'.')-1) > 11\nthen ( select count(*) from cdb_pdbs )\nelse 0\nend as pdbcount from v$instance	pdbcount	1	Oracle	None	Y
35	ORACLE	CLOUD_DBC	OS	Fix Cloud_DBC	. ./.bash_profile;    sqlplus / as sysdba <<sqlOUT\nALTER SESSION SET "_oracle_script"=TRUE;\ncreate user Cloud_DBC identified by "Just4Now" account unlock;\nALTER USER "CLOUD_DBC" IDENTIFIED BY VALUES 'S:61859E8AB393649BC54960D3EA4435D167AD22A6C4F3C470760B8D68FCF5;T:19966973DCAC258E40C002DBDDB133775FE50162CEBD21B91812FC579E196FF96C3F5A1941135946915CD8D37DD8F785EB1D9251683EA8EB962324981FD53B4A633DC1F02AC16D49A2D66CCC8C448CDA;7884D90DA348BA0D' account unlock;\nALTER USER "CLOUD_DBC" profile NOEXPIRE_PWD;\ngrant dba to Cloud_DBC;\nALTER USER Cloud_DBC SET CONTAINER_DATA=ALL CONTAINER=CURRENT;\nexit\nsqlOUT	none	1	ssh	None	Y
36	ALL	HC	OS	ssh check	pwd	home	1	ssh	None	Y
37	ORACLE	TARGET	DB	Standby Info	select distinct * from (   \n             select i.instance_name, i.host_name,    \n                    d.open_mode, d.database_role,   \n                    case when (select count(*) from v$archive_dest where target='STANDBY') = 0    \n                          and d.database_role = 'PRIMARY'   \n                         then 'Stand alone'   \n                         when d.database_role like '%STANDBY%'   \n                         then (select 'Primary: '||destination from v$archive_dest where target='REMOTE')    \n                         else a.target||': '||a.destination   \n                         end as Destination_Name,   \n                    case when (select count(*) from v$archive_dest where target in ('STANDBY','REMOTE')) = 0 then null   \n                         else a.status   \n                         end as Status,   \n                    case when (select count(*) from v$archive_dest  where target in ('STANDBY','REMOTE')) = 0 then null   \n                         else a.schedule   \n                         end as Schedule        \n             from v$instance i, v$database d, v$archive_dest a   \n             where a.target in ('STANDBY','REMOTE')   \n                or d.database_role='PRIMARY')   \n             where Destination_Name like 'STANDBY%'   \n                or Destination_Name='Stand alone'   \n                or Destination_Name like 'Primary%' 	standbydest	1	Oracle	None	Y
38	ORACLE	WEEKLY	OS	swrelease with  prepending ORACLE_HOME	opatch lspatches | grep -i Database | grep -v Java | grep -v "^$" | awk -F':' '{print $2}' | grep -v "^$"  	swrelease	9	Oracle	None	Y
39	ORACLE	WEEKLY	DB	SGA	show sga	sga	8	Oracle	None	Y
40	ALL	HOURLY	OS	uptime / load average	uptime | awk '{print $(NF-2)}'	uptime	7	ssh	None	Y
\.



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


    \q
EOSQL