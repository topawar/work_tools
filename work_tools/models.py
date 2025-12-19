from django.db import models

class OrgDetail(models.Model):
    company_code = models.CharField(max_length=255, null=True, blank=True)  # 移除unique=True约束
    company_name = models.CharField(max_length=255, null=True, blank=True)
    plate_code = models.CharField(max_length=255, null=True, blank=True)
    plate_name = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = 'org_detail'

class UserOrgDetail(models.Model):
    """用户组织机构表"""
    login_name = models.CharField(max_length=255, null=True, blank=True, verbose_name='登录名')
    user_name = models.CharField(max_length=255, null=True, blank=True, verbose_name='用户名')
    dept_code = models.CharField(max_length=255, null=True, blank=True, verbose_name='部门编码')
    dept_name = models.CharField(max_length=255, null=True, blank=True, verbose_name='部门名称')
    company_code = models.CharField(max_length=255, null=True, blank=True, verbose_name='公司编码')
    company_name = models.CharField(max_length=255, null=True, blank=True, verbose_name='公司名称')
    plate_code = models.CharField(max_length=255, null=True, blank=True, verbose_name='板块编码')
    plate_name = models.CharField(max_length=255, null=True, blank=True, verbose_name='板块名称')

    class Meta:
        db_table = 'user_org_detail'
        verbose_name = '用户组织机构'
        verbose_name_plural = '用户组织机构'

class ItemDetail(models.Model):
    # 添加自增主键，item_id改为普通字段，允许重复
    id = models.AutoField(primary_key=True)
    item_id = models.CharField(max_length=100)  # 移除primary_key=True
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


class ConfigurableTable(models.Model):
    """可配置表元数据"""
    table_code = models.CharField(max_length=50, unique=True, verbose_name='表编码')
    table_name = models.CharField(max_length=100, verbose_name='数据库表名')
    display_name = models.CharField(max_length=200, verbose_name='显示名称')
    description = models.TextField(blank=True, verbose_name='功能描述')
    database_configs = models.ManyToManyField(
        'DatabaseConfig',
        blank=True,
        related_name='tables',
        verbose_name='启用的数据库配置'
    )
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    sort_order = models.IntegerField(default=0, verbose_name='排序顺序')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'configurable_table'
        verbose_name = '可配置表'
        verbose_name_plural = '可配置表'
        ordering = ['sort_order', 'table_code']

    def __str__(self):
        return f"{self.display_name} ({self.table_code})"


class ConfigurableField(models.Model):
    """可配置字段元数据"""
    FIELD_TYPE_CHOICES = [
        ('update', '修改字段'),
        ('query', '查询字段'),
    ]
    
    DATA_TYPE_CHOICES = [
        ('text', '文本'),
        ('number', '数字'),
        ('date', '日期'),
        ('dropdown', '下拉框'),
    ]
    
    table = models.ForeignKey(
        ConfigurableTable,
        on_delete=models.CASCADE,
        related_name='fields',
        verbose_name='所属表'
    )
    field_type = models.CharField(max_length=20, choices=FIELD_TYPE_CHOICES, verbose_name='字段类型')
    field_name = models.CharField(max_length=100, verbose_name='数据库字段名')
    display_name = models.CharField(max_length=200, verbose_name='显示名称')
    data_type = models.CharField(max_length=20, choices=DATA_TYPE_CHOICES, verbose_name='数据类型')
    dropdown_group = models.ForeignKey(
        DropdownGroup,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='fields',
        verbose_name='下拉框数据源分组'
    )
    is_required = models.BooleanField(default=False, verbose_name='是否必填')
    is_nullable = models.BooleanField(default=True, verbose_name='是否可为空')
    sql_file_name = models.CharField(max_length=100, blank=True, verbose_name='SQL文件名')
    max_length = models.IntegerField(null=True, blank=True, verbose_name='最大长度')
    default_value = models.CharField(max_length=255, blank=True, verbose_name='默认值')
    sort_order = models.IntegerField(default=0, verbose_name='排序顺序')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'configurable_field'
        verbose_name = '可配置字段'
        verbose_name_plural = '可配置字段'
        unique_together = [['table', 'field_name']]
        ordering = ['table', 'field_type', 'sort_order', 'field_name']
        indexes = [
            models.Index(fields=['table', 'field_type', 'is_active']),
            models.Index(fields=['table', 'field_name']),
        ]

    def __str__(self):
        return f"{self.display_name} ({self.field_name})"


class DatabaseConfig(models.Model):
    """数据库配置"""
    config_code = models.CharField(max_length=50, unique=True, verbose_name='配置编码')
    config_name = models.CharField(max_length=100, verbose_name='配置名称')
    db_host = models.CharField(max_length=255, verbose_name='数据库地址')
    db_name = models.CharField(max_length=100, verbose_name='数据库名')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    sort_order = models.IntegerField(default=0, verbose_name='排序顺序')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'database_config'
        verbose_name = '数据库配置'
        verbose_name_plural = '数据库配置'
        ordering = ['sort_order', 'config_code']

    def __str__(self):
        return f"{self.config_name} ({self.config_code})"
