Copy checklist from stdin;
41	ORACLE	HOURLY	DB	Start Time	select startup_time from v$instance	started	1	Oracle	None	Y
42	ORACLE	DAILY	OMS	in OMS?	select case when exists ( select 1 from oms_targets where upper(host) = '{}' and upper(target) = '{}' )  then 'Y' else 'N' end as rec_exists from dual	inoms	9	OMS	None	Y
43	ORACLE	DAILY	DB	Description	select open_mode from v$database	openmode	1	Oracle	None	Y
44	ORACLE	DAILY	DB	Description	select sum(bytes) from dba_data_files	dbsizeallocated	1	Oracle	None	Y
45	ORACLE	DAILY	DB	Database Size Used (bytes)	select sum(bytes) from dba_segments	dbsizeused	1	Oracle	None	Y
46	ORACLE	DAILY	DB	Description	select 'Y' from dual	dbcaccess	1	Oracle	None	Y
47	ORACLE	DAILY	DB	Description	select count(*) from v$encryption_wallet where status = 'CLOSED' 	closedwallet	1	Oracle	None	Y
48	ORACLE	HOURLY	DB	Percentage of Max Proccesses currently in use	select (current_utilization / (decode(to_number(limit_value),0,1,to_number(limit_value)))*100) from v$resource_limit where resource_name = 'processes'	processespct	1	Oracle	None	Y
49	ORACLE	WEEKLY!	DB	Description	select count(*) FILES from dba_data_files where file_name not like '%oradata%' union all select count(*) FILES from dba_temp_files where file_name not like '%oradata%'	badfileloc	1	Oracle	None	Y
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
