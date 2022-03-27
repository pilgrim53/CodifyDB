from django import db
from django.db import models
import functools

def set_sql_for_field(field, sql):
    def decorator(model_save_func):
        @functools.wraps(model_save_func)
        def wrapper(obj, *args, **kwargs):
            assert hasattr(obj, field), (
                'set_sql_for_field was given a field that does not exist on '
                'the model. Double-check model fields and decorators for '
                f'{obj.__class__}.{field} and SQL {sql}'
            )

            if getattr(obj, field) is None:
                # Multi-DB safe! Get DB for class from default manager.
                database = obj.__class__._default_manager.db

                from django.db import connections
                with connections[database].cursor() as cursor:
                    cursor.execute(f'{sql}')
                    setattr(obj, field, cursor.fetchone()[0])

            return model_save_func(obj, *args, **kwargs)
        return wrapper
    return decorator

class Notification(models.Model):
    id = models.IntegerField(primary_key=True) 
    threshold = models.TextField(blank=True, null=True)
    result_column = models.TextField(blank=False, null=False)
    frequency = models.TextField(blank=False, null=False, default="HOURLY")

    class Meta:
      db_table = 'notifications'

class CheckList(models.Model):
    id = models.IntegerField(primary_key=True) 
    vendor = models.TextField(blank=True, null=True)
    frequency = models.TextField(blank=False, null=False)
    check_type = models.TextField(blank=True, null=True)
    sub_type = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    check_command = models.TextField(blank=False, null=False)
    result_column = models.TextField(blank=False, null=False)
    priority = models.IntegerField(blank=True, null=True,  default=1)
    handler = models.TextField(blank=False, null=False)
    enabled = models.TextField(blank=False, null=True,  default='Y')

    class Meta:
      db_table = 'checklist'

# This is the Target class for objects you want to inventory and monitor 
class Target(models.Model):
    inventory_id = models.IntegerField(primary_key=True) 
    inventory_create = models.DateField(blank=True, null=True)
    db_created_date  = models.DateField(blank=True, null=True)
    last_check_date = models.DateTimeField(blank=True, null=True)
    serial_number = models.TextField(blank=True, null=True)
    vendor= models.TextField(blank=True, null=True)
    instance_name = models.TextField(blank=True, null=True)
    hostname = models.TextField(blank=False)
    version= models.TextField(blank=True, null=True)
    home_dir = models.TextField(blank=True, null=True)
    owner = models.TextField(blank=True, null=True)
    port = models.IntegerField(blank=True, null=True,  default=0)
    status = models.TextField(blank=True, null=True)
    archivelog_mode = models.TextField(blank=True, null=True)
    blocksize = models.IntegerField(blank=True, null=True, default=0)
    highlysensitiveinfo = models.BinaryField(blank=True, null=True)
    sub_type = models.TextField(blank=True, null=True)
    important_notes = models.TextField(blank=True, null=True)
    role = models.TextField(blank=True, null=True)
    container = models.TextField(blank=True, null=True)
    decommissioned  = models.DateField(blank=True, null=True)
    host_type = models.TextField(blank=True, null=True)
    standby_dest = models.TextField(blank=True, null=True)
    os = models.TextField(blank=True, null=True)
    v_instance = models.TextField(blank=True, null=True)
    target_type = models.TextField(blank=True, null=True)
    support_tier = models.TextField(blank=True, null=True)
    clustered = models.TextField(blank=True, null=True)

    class Meta:
      db_table = 'targets'

    @set_sql_for_field('inventory_id', 'select nextval(\'targets_id_seq\')')

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)


class TargetReject(models.Model):
    inventory_id = models.IntegerField(blank=True, null=True)
    inventory_create = models.DateField(blank=True, null=True)
    last_check_date = models.DateTimeField(blank=True, null=True)
    vendor = models.CharField(max_length=50, blank=True, null=True)
    instance_name = models.CharField(max_length=50, blank=True, null=True)
    hostname = models.CharField(max_length=50, blank=True, null=True)
    home_directory = models.CharField(max_length=255, blank=True, null=True)
    owner = models.CharField(max_length=50, blank=True, null=True)
    port = models.IntegerField(blank=True, null=True)
    status = models.CharField(max_length=255, blank=True, null=True)
    database_type = models.CharField(max_length=50, blank=True, null=True)
    important_notes = models.CharField(max_length=1000, blank=True, null=True)

    class Meta:
        db_table = 'target_rejects'

class CheckResult(models.Model):
    inventory_id = models.IntegerField(blank=True, null=True)
    check_date = models.DateTimeField(blank=True, null=True)
    check_result = models.TextField(blank=True, null=True)
    check_column = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'check_results'