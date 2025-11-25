from django.contrib import admin
from django_db_logger.models import StatusLog
from django_db_logger.admin import StatusLogAdmin as BaseStatusLogAdmin


class StatusLogAdmin(BaseStatusLogAdmin):
    list_per_page = 20


admin.site.unregister(StatusLog)
admin.site.register(StatusLog, StatusLogAdmin)
