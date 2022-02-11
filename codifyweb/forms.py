from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

from .models import Target, CheckList


#class TargetForm(forms.ModelForm):
#    class Meta:
#        model = Target
#        fields = ['hostname', 'instance_name', 'owner', 'version']


class TargetForm(forms.Form):
    inventory_id = forms.IntegerField(required=False)
    hostname = forms.CharField(max_length=15)
    instance_name = forms.CharField(max_length=15)
    container = forms.CharField(max_length=15, required=False)
    owner = forms.CharField(max_length=15, required=False)
    DBID = forms.CharField(max_length=15, required=False)
    home_dir = forms.CharField(max_length=15, required=False)
    status = forms.CharField(max_length=15, required=False)
    port = forms.CharField(max_length=15, required=False, initial=1521)
    target_type = forms.CharField(max_length=15, required=False)



VENDORS = (
        ('Oracle', 'Oracle'),
        ('SQLServer','SQLServer'),
        ('Postgresql','Postgresql'),
        ('RHEL','RHEL'),
        ('AIX','AIX'),
        ('SunOS','SunOS'),
)

TARGET_TYPES = (
        ('Database', 'Database'),
        ('Server','Server'),
)

ACTION_TYPES = (
    ('Add', 'Add'),
    ('Update', 'Update'),
)

CHECK_FREQUENCIES = (
    ('HOURLY','Hourly'),
    ('DAILY','Daily'),
    ('WEEKLY','Weekly'),
    ('MONTHLY','Monthly'),
)

INTERVALS = (
    ('1', 1),
    ('6', 6),
    ('12', 12),
    ('24', 24),
)

class AddOrUpdateForm(forms.Form):
    target_type = forms.ChoiceField(choices=TARGET_TYPES)
    action = forms.ChoiceField(choices=ACTION_TYPES)

class CheckTargetsForm(forms.Form):
    target_type = forms.ChoiceField(choices=TARGET_TYPES)
    frequencies = forms.ChoiceField(choices=CHECK_FREQUENCIES)

class AlertsForm(forms.Form):
    target_type = forms.ChoiceField(choices=TARGET_TYPES)
    interval = forms.ChoiceField(choices=INTERVALS)

class ScanForm(forms.Form): 
    target_type = forms.ChoiceField(choices=TARGET_TYPES)

class ExportForm(forms.Form): 
    target_type = forms.ChoiceField(choices=TARGET_TYPES)


FREQUENCIES = (
    ('HOURLY','hourly'),
    ('DAILY','daily'),
    ('MONTHLY','monthly'),
    ('ADHOC','adhoc'),
    ('Database','Database'),
    ('Server','Server'),
)


class CheckForm(forms.Form):
    target_type = forms.ChoiceField(choices=TARGET_TYPES)
    vendor = forms.ChoiceField(choices=VENDORS)
    frequency = forms.ChoiceField(choices=FREQUENCIES)

