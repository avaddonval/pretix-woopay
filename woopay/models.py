from django.db import models


class ReferencedWoopayObject(models.Model):
    reference = models.CharField(max_length=190, db_index=True, unique=True)
    key = models.CharField(max_length=15, db_index=True, unique=True,null=True)
    url = models.TextField(null=True)
    order = models.ForeignKey('pretixbase.Order')

class SessionWoopayObject(models.Model):
    session = models.CharField(max_length=190, db_index=True, unique=True)
