from django.contrib import admin
from .models import Alarm_dgu, Dgu_tag
from import_export.admin import ImportExportModelAdmin
from import_export import resources


admin.site.register(Alarm_dgu)


class Dgu_tagsResource(resources.ModelResource):
    class Meta:
        model = Dgu_tag


class Dgu_tagTagsAdmin(ImportExportModelAdmin):
    resource_class = Dgu_tagsResource
    list_display = ['id', 'name', 'alarm_id', 'bdtp', 'noffl', 'tag_type', 'controller']
    list_filter = ('tag_type', 'bdtp', 'noffl', 'alarm_id')
    search_fields = ['id', 'name', 'alarm_id']


admin.site.register(Dgu_tag, Dgu_tagTagsAdmin)
