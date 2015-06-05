from django.contrib import admin

# Register your models here.

from aplicacion.models import MetodosSirepa, GruposLoguin


admin.site.register(GruposLoguin)
admin.site.register(MetodosSirepa)


