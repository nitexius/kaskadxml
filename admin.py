from django.contrib import admin
from .models import Alarm, HistoryAttr, Tag, Cutout

from import_export.admin import ImportExportModelAdmin
from import_export import resources


admin.site.register(Alarm)
admin.site.register(HistoryAttr)


class TagsResource(resources.ModelResource):
    class Meta:
        model = Tag


class TagsAdmin(ImportExportModelAdmin):
    resource_class = TagsResource
    list_display = ['id', 'name', 'alarm_id', 'bdtp', 'noffl', 'bad_tag', 'new_tag', 'controller']
    search_fields = ['id', 'name', 'alarm_id']


admin.site.register(Tag, TagsAdmin)


class CutoutResource(resources.ModelResource):
    class Meta:
        model = Cutout


class CutoutAdmin(ImportExportModelAdmin):
    resource_class = CutoutResource
    list_display = ['name', 'cutout', 'xo_type']
    search_fields = ['name', 'cutout', 'xo_type']


admin.site.register(Cutout, CutoutAdmin)
