from django import db
from django.db import models
from django.db.models.fields import NullBooleanField
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




class CheckList(models.Model):
    id = models.IntegerField(primary_key=True) 
    vendor = models.TextField(blank=True)
    frequency = models.TextField(blank=True)
    check_type = models.TextField(blank=True)
    description = models.TextField(blank=True)
    check_command = models.TextField(blank=True)
    result_column = models.TextField(blank=True)
    priority = models.IntegerField(blank=True)
    handler = models.TextField(blank=True)

    class Meta:
      db_table = 'checklist'



# This is the Target class for objects you want to inventory and monitor 
class Target(models.Model):
    inventory_id = models.IntegerField(primary_key=True) 
    inventory_create = models.DateField(blank=True)
    db_created_date  = models.DateField(blank=True)
    last_check_date = models.DateTimeField(blank=True)
    serial_number = models.TextField(blank=True)
    vendor= models.TextField(blank=True)
    instance_name = models.TextField(blank=True)
    hostname = models.TextField(blank=True)
    version= models.TextField(blank=True)
    home_dir = models.TextField(blank=True)
    owner = models.TextField(blank=True)
    port = models.IntegerField(blank=True)
    status = models.TextField(blank=True)
    archivelog_mode = models.TextField(blank=True)
    blocksize = models.IntegerField(blank=True)
    highlysensitiveinfo = models.BinaryField(blank=True)
    database_type = models.TextField(blank=True)
    important_notes = models.TextField(blank=True)
    role = models.TextField(blank=True)
    container = models.TextField(blank=True)
    decommissioned  = models.DateField(blank=True)
    host_type = models.TextField(blank=True)
    standby_dest = models.TextField(blank=True)
    os = models.TextField(blank=True)
    v_instance = models.TextField(blank=True)
    target_type = models.TextField(blank=True)
    support_tier = models.TextField(blank=True)
    clustered = models.TextField(blank=True)

    class Meta:
      db_table = 'target'

    @set_sql_for_field('inventory_id', 'select nextval(\'inventoryid\')')

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
