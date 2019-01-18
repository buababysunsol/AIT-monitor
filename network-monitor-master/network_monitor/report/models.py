from djongo import models


class Settings(models.Model):
    key = models.CharField(primary_key=True, unique=True, max_length=255)
    value = models.CharField(null=True, max_length=255)
    value_date = models.DateTimeField(null=True)
