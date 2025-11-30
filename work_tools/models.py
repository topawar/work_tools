from django.db import models

class OrgDetail(models.Model):
    company_code = models.CharField(max_length=255, unique=True, null=True, blank=True)
    company_name = models.CharField(max_length=255, null=True, blank=True)
    plate_code = models.CharField(max_length=255, null=True, blank=True)
    plate_name = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = 'org_detail'

class ItemDetail(models.Model):
    item_id = models.CharField(max_length=100, primary_key=True)
    item_name = models.CharField(max_length=1000)
    category = models.CharField(max_length=100)
    item_uom = models.CharField(max_length=25)
    purc_type = models.CharField(max_length=10)

    class Meta:
        db_table = 'item_detail'

class ImportJob(models.Model):
    job_type = models.CharField(max_length=16)
    status = models.CharField(max_length=16, default='pending')
    total = models.IntegerField(default=0)
    done = models.IntegerField(default=0)
    message = models.TextField(blank=True)
    error = models.TextField(blank=True)
    filename = models.CharField(max_length=512, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'import_job'
