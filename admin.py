from django.contrib import admin
from .models import Alarm, HistoryAttr, GoodTag, BadTag, NewTag, Cutout

from import_export.admin import ImportExportActionModelAdmin, ImportExportModelAdmin
from import_export import resources


admin.site.register(Alarm)
admin.site.register(HistoryAttr)


class GoodTagsResource(resources.ModelResource):
    class Meta:
        model = GoodTag


class GoodTagsAdmin(ImportExportModelAdmin):
    resource_class = GoodTagsResource
    list_display = ['id', 'name', 'alarm_id', 'bdtp', 'noffl']
    search_fields = ['id', 'name', 'alarm_id']


admin.site.register(GoodTag, GoodTagsAdmin)


class BadTagsResource(resources.ModelResource):
    class Meta:
        model = BadTag


class BadTagsAdmin(ImportExportActionModelAdmin):
    resource_class = BadTagsResource
    list_display = ['id', 'name']
    search_fields = ['id', 'name']


admin.site.register(BadTag, BadTagsAdmin)


class NewTagsResource(resources.ModelResource):
    class Meta:
        model = NewTag


class NewTagsAdmin(ImportExportModelAdmin):
    resource_class = NewTagsResource
    list_display = ['id', 'name', 'controller', 'alarm_id', 'bdtp', 'noffl']
    search_fields = ['name', 'controller']


admin.site.register(NewTag, NewTagsAdmin)


class CutoutResource(resources.ModelResource):
    class Meta:
        model = Cutout


class CutoutAdmin(ImportExportModelAdmin):
    resource_class = CutoutResource
    list_display = ['name', 'cutout', 'xo_type']
    search_fields = ['name', 'cutout', 'xo_type']


admin.site.register(Cutout, CutoutAdmin)
