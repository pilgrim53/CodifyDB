from django.forms import TextInput, Textarea
from django.contrib import admin
from django.db import models
from codifyweb.models import CheckList, CheckResult
from codifyweb.models import Target, TargetReject

class ListAdmin(admin.ModelAdmin):    
    formfield_overrides = {
        models.CharField: {'widget': TextInput(attrs={'size':'20'})},
        models.TextField: {'widget': Textarea(attrs={
            'rows':1,
            'cols':20,
            'oninput':'this.style.height = "";this.style.height = this.scrollHeight + 3 + "px"',
            })},
    }

    list_display = ('id', 'vendor', 'frequency', 'priority','check_type','handler','result_column',
                    'description', 'check_command')

    fields = ['id','vendor','frequency','priority','check_type','handler','result_column','description','check_command']

    list_display_links = ['id']

    search_fields = ['frequency', 'handler', 'result_column']




class TargetAdmin(admin.ModelAdmin):
    formfield_overrides = {
        models.CharField: {'widget': TextInput(attrs={'size':'20'})},
        models.TextField: {'widget': Textarea(attrs={'rows':1, 'cols':20})},
    }
    list_display = ('inventory_id','vendor','target_type','hostname', 'instance_name', 'owner', 'version','home_dir','clustered','support_tier', 'inventory_create','decommissioned','db_created_date')
    fields = ['hostname','vendor','target_type','instance_name', 'owner', 'decommissioned']
    list_display_links = ['inventory_id']
    search_fields = ['hostname', 'instance_name', 'owner']



class TargetRejectAdmin(admin.ModelAdmin):
    formfield_overrides = {
        models.CharField: {'widget': TextInput(attrs={'size':'20'})},
        models.TextField: {'widget': Textarea(attrs={'rows':1, 'cols':20})},
    }
    list_display = ('inventory_id','vendor','database_type','hostname','owner','home_directory','inventory_create')
    fields = ['hostname','vendor','database_type','instance_name', 'owner']
    list_display_links = ['inventory_id']
    search_fields = ['hostname', 'instance_name', 'owner']


class CheckResultAdmin(admin.ModelAdmin):    
    formfield_overrides = {
        models.CharField: {'widget': TextInput(attrs={'size':'20'})},
        models.TextField: {'widget': Textarea(attrs={'rows':1, 'cols':20})},
    }

    list_display = ('inventory_id', 'check_date', 'check_result', 'check_column')
    fields = ['inventory_id', 'check_date', 'check_result', 'check_column']
    list_display_links = ['inventory_id']
    search_fields = ['check_date', 'check_result', 'check_column']


admin.site.register(CheckList, ListAdmin)
admin.site.register(Target, TargetAdmin)
admin.site.register(TargetReject, TargetRejectAdmin)
admin.site.register(CheckResult, CheckResultAdmin)

