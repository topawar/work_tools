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


class DropdownGroup(models.Model):
    """下拉框配置分组表"""
    group_code = models.CharField(max_length=50, unique=True, verbose_name='分组编码')
    group_name = models.CharField(max_length=100, verbose_name='分组名称')
    description = models.TextField(blank=True, verbose_name='分组描述')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'dropdown_group'
        verbose_name = '下拉框配置分组'
        verbose_name_plural = '下拉框配置分组'
        ordering = ['group_code']

    def __str__(self):
        return f"{self.group_name} ({self.group_code})"


class DropdownOption(models.Model):
    """下拉框配置项表"""
    group = models.ForeignKey(
        DropdownGroup,
        on_delete=models.CASCADE,
        related_name='options',
        verbose_name='所属分组'
    )
    option_code = models.CharField(max_length=50, verbose_name='选项编码')
    option_label = models.CharField(max_length=200, verbose_name='选项标签')
    sort_order = models.IntegerField(default=0, verbose_name='排序顺序')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    is_system = models.BooleanField(default=False, verbose_name='是否系统内置')
    remark = models.TextField(blank=True, verbose_name='备注说明')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'dropdown_option'
        verbose_name = '下拉框配置项'
        verbose_name_plural = '下拉框配置项'
        unique_together = [['group', 'option_code']]
        ordering = ['group', 'sort_order', 'option_code']
        indexes = [
            models.Index(fields=['group', 'is_active']),
            models.Index(fields=['option_code']),
        ]

    def __str__(self):
        return f"{self.option_label} ({self.option_code})"
