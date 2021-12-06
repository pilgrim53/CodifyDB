-- Table: public.checklist

-- DROP TABLE public.checklist;

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
    
copy public.checklist(
	id, vendor, frequency, check_type, description, check_command, result_column, priority, handler)  FROM stdin;
2	ORACLE	WEEKLY	DB	in OMS?	select case when exists ( select 1 from oms_targets where upper(host) = '{}' and upper(target) = '{}' )  then 'Y' else 'N' end as rec_exists from dual	in_oms	1	OMS
3	ORACLE	DAILY	DB	Description	select open_mode from v$database	open_mode	5	Oracle
4	ORACLE	DAILY	DB	Description	select sum(bytes) from dba_data_files	db_size_allocated	7	Oracle
5	ORACLE	DAILY	DB	Database Size Used (bytes)	select sum(bytes) from dba_segments	db_size_used	2	Oracle
6	ORACLE	DAILY	DB	Description	select 'Y' from dual	dbc_access	9	Oracle
7	ORACLE	DAILY	DB	Description	select count(*) from v$encryption_wallet where status = 'CLOSED' 	closed_wallet	10	Oracle
54	ORACLE	DBHC	DB	access check	select count(*) from dba_users where username='C##BELLDBC'	dbc_access	1	Oracle
9	ORACLE	DISABLED	DB	Description	select count(*) FILES from dba_data_files where file_name not like '%oradata%' union all select count(*) FILES from dba_temp_files where file_name not like '%oradata%'	bad_file_loc	9	Oracle
10	ORACLE	DAILY	DB	Description	select count(*) from V$SESSION_CONNECT_INFO c, v$session a where a.sid = c.sid and c.osuser <> 'oraoemag' and program not like '%caddld-590%' 	app_sessions	4	Oracle
50	ORACLE_9i	DAILY	DB	\N	select count(*) from V$SESSION_CONNECT_INFO c, v$session a where a.sid = c.sid and c.osuser <> 'oraoemag' and program not like '%caddld-590%' 	app_sessions	1	Oracle
11	ORACLE	WEEKLY!	OS	Oracle Patches	opatch lspatches | grep -i Database | grep -v Java | grep -v "^$" | awk -F':' '{print $2}' | grep -v "^$"   2>/dev/null ; opatch lspatches | grep -i Database | grep -v Java | grep -v "^$" | awk -F':' '{print $2}' | grep -v "^$"  2>/dev/null ; \n${ORACLE_HOME}/OPatch/opatch lspatches | grep -i Database | grep -v Java | grep -v "^$" | awk -F':' '{print $2}' | grep -v "^$"  2>/dev/null 	sw_release	1	ssh
51	ORACLE_9i	DAILY	DB	\N	select nvl(sum(bytes),0) from dba_tablespaces t, dba_free_space f where t.tablespace_name  = f.tablespace_name (+) and t.tablespace_name = 'SYSTEM' group by t.tablespace_name	system_free	2	Oracle
55	ORACLE	DAILY	DB	check PDB status	select pdb_name, status from cdb_pdbs where status != 'NORMAL'	pdb_status	8	Oracle
45	ALL	MONTHLY	OS	Memory Free	free	free_memory	1	ssh
52	ORACLE_9i	WEEKLY	DB	\N	begin\ndeclare\n  ver number(2);\n  psu varchar2(100);\n  sql_text varchar2(1000);\nbegin\n select substr(version,1,instr(version, '.')-1) into ver from v$instance;\n--  dbms_output.put_line ( 'Version is: '||ver ) ;\n  case\n    when ver = 9\n    then sql_text := 'select max (PS) from\n                      ((select max(substr(version, instr(version, :1||''.'',1,1))) PS\n                         from dba_registry\n                         where upper(comp_name) like ''%CATALOG%'')\n                        union\n                        (select version PS from v$instance))';\n    when ver = 10\n    then sql_text := 'select max (PS) from\n                       ((select max(substr(version, instr(version, :1||''.'',1,1))) PS\n                          from dba_registry\n                          where upper(comp_name) like ''%CATALOG%'')\n                         union\n                        (select nvl(max(substr(comments, instr(comments, ''10.'',1,1))),0) PS\n                          from dba_registry_history\n                          where upper(comments) like ''PSU%'' or upper(comments) like ''CPU%''))';\n    when ver = 11\n    then sql_text := 'select nvl(max(substr(COMMENTS, instr(comments, :1||''.'',1,1))),''None'')\n                      from DBA_REGISTRY_HISTORY\n                      where upper(comments) like ''PSU%''\n                         or upper(comments) like ''CPU%''';\n    when ver = 12\n    then sql_text := 'select nvl(max(substr(DESCRIPTION, instr(description, :1||''.'',1,1))),''None'')\n                      from dba_registry_sqlpatch\n                      where upper(description) like ''DATABASE%''';\n    when ver = 18\n    then sql_text := 'select nvl(max(substr(description, instr(description, :1||''.'',1,1))),''None'')\n                      from dba_registry_sqlpatch\n                      where upper(description) like ''DATABASE%''';\n    when ver = 19\n    then sql_text := 'select nvl(max(substr(description, instr(description, :1||''.'',1,1))),''None'')\n                      from dba_registry_sqlpatch\n                      where upper(description) like ''DATABASE%''';\n    when ver > 19\n    then sql_text := 'select ''Need new CASE for v''||:1 from dual';\n  end case;\n--  dbms_output.put_line ( sql_text ) ;\n  execute immediate sql_text into psu using ver;\n  dbms_output.put_line ( psu ) ;\n  return;\nend;\nend;	sw_release	1	PLSQL
47	LINUX	Server	OS	Get os creation date	sudo rpm -qi basesystem | grep Install	db_created_date	1	ssh
46	ALL	WEEKLY	OS	Oracle PMON running	echo "`ps -ef | grep -i _pmon_ | grep -v grep | awk ' { print $1, $(NF) , \\", \\"  } '`"	pmon	1	ssh
48	ORACLE	WEEKLY	DB	find current patch level	begin\ndeclare\n  ver number(2);\n  psu varchar2(100);\n  sql_text varchar2(1000);\nbegin\n select substr(version,1,instr(version, '.')-1) into ver from v$instance;\n--  dbms_output.put_line ( 'Version is: '||ver ) ;\n  case\n    when ver = 9\n    then sql_text := 'select max (PS) from\n                      ((select max(substr(version, instr(version, :1||''.'',1,1))) PS\n                         from dba_registry\n                         where upper(comp_name) like ''%CATALOG%'')\n                        union\n                        (select version PS from v$instance))';\n    when ver = 10\n    then sql_text := 'select max (PS) from\n                       ((select max(substr(version, instr(version, :1||''.'',1,1))) PS\n                          from dba_registry\n                          where upper(comp_name) like ''%CATALOG%'')\n                         union\n                        (select nvl(max(substr(comments, instr(comments, ''10.'',1,1))),0) PS\n                          from dba_registry_history\n                          where upper(comments) like ''PSU%'' or upper(comments) like ''CPU%''))';\n    when ver = 11\n    then sql_text := 'select nvl(max(substr(COMMENTS, instr(comments, :1||''.'',1,1))),''None'')\n                      from DBA_REGISTRY_HISTORY\n                      where upper(comments) like ''PSU%''\n                         or upper(comments) like ''CPU%''';\n    when ver = 12\n    then sql_text := 'select nvl(max(substr(DESCRIPTION, instr(description, :1||''.'',1,1))),''None'')\n                      from dba_registry_sqlpatch\n                      where upper(description) like ''DATABASE%''';\n    when ver = 18\n    then sql_text := 'select nvl(max(substr(description, instr(description, :1||''.'',1,1))),''None'')\n                      from dba_registry_sqlpatch\n                      where upper(description) like ''DATABASE%''';\n    when ver = 19\n    then sql_text := 'select nvl(max(substr(description, instr(description, :1||''.'',1,1))),''None'')\n                      from dba_registry_sqlpatch\n                      where upper(description) like ''DATABASE%''';\n    when ver > 19\n    then sql_text := 'select ''Need new CASE for v''||:1 from dual';\n  end case;\n--  dbms_output.put_line ( sql_text ) ;\n  execute immediate sql_text into psu using ver;\n  dbms_output.put_line ( psu ) ;\n  return;\nend;\nend;	sw_release	1	PLSQL
49	ASM	DAILY	DB	ASM DISK Statius	select count(*) from v$asm_disk where header_status !='MEMBER' or MODE_STATUS !='ONLINE' or STATE !='NORMAL'	asm_disk	1	ASM
14	ALL	WEEKLY	OS	Physical vs Hardware	 dmesg | grep "Hardware name:" | head -n 1 | awk -F":" '{print $2}'	host_type	9	ssh
1	ORACLE	HOURLY	DB	Start Time	select startup_time from v$instance	started	1	Oracle
53	ORACLE_9i	HOURLY	DB	\N	select startup_time from v$instance	started	1	Oracle
44	ALL	HOURLY	OS	5 min load Average	uptime | awk '{print $(NF-2)}' | sed s/,//g	load_5	2	ssh
8	ORACLE	HOURLY	DB	Percentage of Max Proccesses currently in use	select (current_utilization / (decode(to_number(limit_value),0,1,to_number(limit_value)))*100) from v$resource_limit where resource_name = 'processes'	processes_pct	2	Oracle
56	ALL	WEEKLY	OS	kernel	uname -a | awk -F" " ' {print $3}'	kernel	1	ssh
12	ORACLE	DAILY	DB	SYSTEM Free Space	select nvl(sum(bytes),0) from dba_tablespaces t, dba_free_space f where t.tablespace_name  = f.tablespace_name (+) and t.tablespace_name = 'SYSTEM' group by t.tablespace_name	system_free	6	Oracle
13	ORACLE	DAILY	DB	SYSAUX Free Space	select nvl(sum(bytes),0) from dba_tablespaces t, dba_free_space f where t.tablespace_name  = f.tablespace_name (+) and t.tablespace_name = 'SYSAUX' group by t.tablespace_name	sysaux_free	8	Oracle
16	ORACLE	WEEKLY	OS	/etc/init.d/dbora installed 	if [ ! -f /etc/init.d/dbora ];  then echo \\"NONE\\" ; else grep Version /etc/init.d/dbora | sed s/#//g ; fi	dbora	2	ssh
17	ORACLE	Database	OS	get Oracle Home from /etc/oratab	grep -i " + instance + ": /etc/oratab | awk -F':' '{print $2}' | head -n 1	home_dir	3	ssh
22	ORACLE	Database	DB	Creation Date for DB	select to_char(created, 'YYYY-MM-DD') from v$database	db_created_date	2	Oracle
23	ORACLE	Database	DB	Database ID	select dbid from v$database	serial_number	3	Oracle
21	ORACLE	DISABLED	DB	DB Host Name	select nvl(substr(upper(host_name), 0, instr(host_name,'.')-1), upper(host_name)) from v$instance;	hostname	9	Oracle
32	ORACLE	Database	OS	Oracle_Home Directory	. ./.bash_profile 2>&1>/dev/null;   if [ -x "${ORACLE_HOME}"  ] ; then echo "${ORACLE_HOME}" ; else  grep -i "^${ORACLE_SID}:" /etc/oratab | awk -F':' '{print $2}' | head -n 1  ;  fi	home_dir	2	ssh
35	ORACLE	CLOUD_DBC	OS	Fix Cloud_DBC	. ./.bash_profile;    sqlplus / as sysdba <<sqlOUT\nALTER SESSION SET "_oracle_script"=TRUE;\ncreate user Cloud_DBC identified by "Just4Now" account unlock;\nALTER USER "CLOUD_DBC" IDENTIFIED BY VALUES 'S:61859E8AB393649BC54960D3EA4435D167AD22A6C4F3C470760B8D68FCF5;T:19966973DCAC258E40C002DBDDB133775FE50162CEBD21B91812FC579E196FF96C3F5A1941135946915CD8D37DD8F785EB1D9251683EA8EB962324981FD53B4A633DC1F02AC16D49A2D66CCC8C448CDA;7884D90DA348BA0D' account unlock;\nALTER USER "CLOUD_DBC" profile NOEXPIRE_PWD;\ngrant dba to Cloud_DBC;\nALTER USER Cloud_DBC SET CONTAINER_DATA=ALL CONTAINER=CURRENT;\nexit\nsqlOUT	none	1	ssh
36	ALL	OSHC	OS	ssh check	pwd	home	1	ssh
33	ALL	Database	OS	Server OS Type	uname -rs	os	1	ssh
19	ALL	ONCE	OS	email list	sed -i 's/^EMAIL=.*/EMAIL="BellITCloudDBC@bell.ca"/'  OraParameters.ksh	email	9	ssh
15	ORACLE	DAILY	DB	PDB Violations	select CASE when substr(version,0,instr(version,'.')-1) > 11\nthen ( select to_char( count(*) ) from pdb_plug_in_violations where status <>'RESOLVED' and message not like '%CDB installed version%' )\nelse '0'\nend as pdbviolations from v$instance	pdb_violations	3	Oracle
39	ORACLE	WEEKLY	DB	SGA	show sga	sga	8	Oracle
37	ORACLE	Database	DB	Standby Info	select distinct * from (   \n             select i.instance_name, i.host_name,    \n                    d.open_mode, d.database_role,   \n                    case when (select count(*) from v$archive_dest where target='STANDBY') = 0    \n                          and d.database_role = 'PRIMARY'   \n                         then 'Stand alone'   \n                         when d.database_role like '%STANDBY%'   \n                         then (select 'Primary: '||destination from v$archive_dest where target='REMOTE')    \n                         else a.target||': '||a.destination   \n                         end as Destination_Name,   \n                    case when (select count(*) from v$archive_dest where target in ('STANDBY','REMOTE')) = 0 then null   \n                         else a.status   \n                         end as Status,   \n                    case when (select count(*) from v$archive_dest  where target in ('STANDBY','REMOTE')) = 0 then null   \n                         else a.schedule   \n                         end as Schedule        \n             from v$instance i, v$database d, v$archive_dest a   \n             where a.target in ('STANDBY','REMOTE')   \n                or d.database_role='PRIMARY')   \n             where Destination_Name like 'STANDBY%'   \n                or Destination_Name='Stand alone'   \n                or Destination_Name like 'Primary%' 	standby_dest	7	Oracle
38	ORACLE	WEEKLY!	OS	swrelease with  prepending ORACLE_HOME	. ./.bash_profile 2>&1>/dev/null;   ${ORACLE_HOME}/OPatch/opatch lspatches | grep -i Database | grep -v Java | grep -v "^$" | awk -F':' '{print $2}' | grep -v "^$"  	sw_release	9	ssh
42	ALL	Server	OS	Physical / Virtual	 dmesg | grep "Hardware name:" | head -n 1 | awk -F":" '{print $2}'	host_type	1	ssh
41	ALL	Server	OS	Server OS Type	uname -rs	os	1	ssh
40	ALL	HOURLY	OS	uptime / load average	uptime	uptime	1	ssh
20	ORACLE	Database	DB	Database Instance Name	select upper(instance_name) from v$instance	v_instance	6	Oracle
24	ORACLE	Database	DB	Software Version	select version from v$instance	version	1	Oracle
25	ORACLE	Database	DB	Archive Log Mode	select log_mode from v$database	archivelog_mode	5	Oracle
31	ORACLE	Database	DB	Oracle_Home Directory	select CASE when substr(version,0,instr(version,'.')-1) > 11\n                                                                           then SYS_CONTEXT('USERENV','ORACLE_HOME')\n                                                                           else 'UNKNOWN'\n                                                          end as oracle_home from v$instance	home_dir	12	Oracle
34	ORACLE	WEEKLY	DB	Count the # of PDBS	select CASE when substr(version,0,instr(version,'.')-1) > 11\nthen ( select count(*) from cdb_pdbs )\nelse 0\nend as pdbcount from v$instance	pdb_count	2	Oracle
43	ALL	DAILY	OS	Check os access	id	os_access	1	ssh
26	ORACLE	Database	DB	Instance Status	select status from v$instance	status	4	Oracle
30	ORACLE	Database	DB	Container Name	select CASE when substr(version,0,instr(version,'.')-1) > 11\n                                     then case\n                                          when SYS_CONTEXT('USERENV','CON_NAME') = instance_name\n                                          then 'STANDALONE'\n                                          else SYS_CONTEXT('USERENV','CON_NAME')\n                                          end\n                                     else 'STANDALONE'\n                                     end as container from v$instance	container	10	Oracle
29	ORACLE	Database	DB	Oracle Owner FID	select distinct(username) from v$process where background=1 	owner	11	Oracle
27	ORACLE	Database	DB	Database Role	select database_role from v$database	role	8	Oracle
28	ORACLE	Database	DB	DB Block Size	select value from v$parameter where name ='db_block_size'	blocksize	9	Oracle
\.

