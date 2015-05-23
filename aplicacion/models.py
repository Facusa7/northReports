# encoding:utf-8
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse_lazy
from django.db import models, connections

# Create your models here.

class GruposLoguin(models.Model):
    nombre = models.CharField(max_length=50, unique=True)
    descripcion = models.TextField(null=True)

    def __unicode__(self):
        return self.nombre