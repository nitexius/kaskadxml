from django.contrib import admin
from .models import klogic, klogger, alarms, history_tags, GoodTags, BadTags, NewTags, Cutout, Shift

from import_export.admin import ImportExportActionModelAdmin, ImportExportModelAdmin
from import_export import resources


admin.site.register(klogic)
admin.site.register(Shift)
admin.site.register(klogger)
admin.site.register(alarms)
admin.site.register(history_tags)


class GoodTagsResource(resources.ModelResource):
    class Meta:
        model = GoodTags


class GoodTagsAdmin(ImportExportActionModelAdmin):
    resource_class = GoodTagsResource
    list_display = ['id', 'Name', 'alarm_id', 'bdtp', 'noffl']
    search_fields = ['id', 'Name', 'alarm_id']


admin.site.register(GoodTags, GoodTagsAdmin)


class BadTagsResource(resources.ModelResource):
    class Meta:
        model = BadTags


class BadTagsAdmin(ImportExportActionModelAdmin):
    resource_class = BadTagsResource
    list_display = ['id', 'Name']
    search_fields = ['id', 'Name']


admin.site.register(BadTags, BadTagsAdmin)


class NewTagsResource(resources.ModelResource):
    class Meta:
        model = NewTags


class NewTagsAdmin(ImportExportModelAdmin):
    resource_class = NewTagsResource
    list_display = ['id', 'Name', 'Controller', 'alarm_id', 'bdtp', 'noffl']
    search_fields = ['Name', 'Controller']


admin.site.register(NewTags, NewTagsAdmin)


class CutoutResource(resources.ModelResource):
    class Meta:
        model = Cutout


class CutoutAdmin(ImportExportModelAdmin):
    resource_class = CutoutResource
    list_display = ['name', 'cutout']
    search_fields = ['name', 'cutout']


admin.site.register(Cutout, CutoutAdmin)
