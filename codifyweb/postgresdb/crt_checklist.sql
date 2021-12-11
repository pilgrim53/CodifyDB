-- Table: checklist

ALTER TABLE checklist
    OWNER to codify;
    
INSERT INTO public.checklist(
	id, vendor, frequency, check_type, description, check_command, result_column, priority, handler, sub_type)
	VALUES ('1','ORACLE', 'WEEKLY', 'DB', 'SGA', 'show sga', 'sga', '1', 'oracle', '' );
