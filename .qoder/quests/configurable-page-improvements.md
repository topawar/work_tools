# 可配置页面功能完善实施计划

## 已完成✅

### 1. 数据库结构调整
- ✅ ConfigurableTable移除sql_file_prefix字段
- ✅ ConfigurableField添加is_nullable字段（是否可为空）
- ✅ ConfigurableField添加sql_file_name字段（SQL文件名）
- ✅ 新增DatabaseConfig模型（数据库配置）
- ✅ 执行数据库迁移

## 待完成任务

### 2. 配置管理界面更新（高优先级）
**文件**: `work_tools/views/configurable_config.py`
**文件**: `work_tools/templates/configurable_config.html`

#### 2.1 表配置管理
- [ ] 移除表配置中的SQL文件名前缀字段

#### 2.2 字段配置管理
- [ ] 添加字段表单：添加is_nullable、sql_file_name字段
- [ ] 编辑字段表单：添加is_nullable、sql_file_name字段
- [ ] 字段列表显示：显示是否可为空、SQL文件名
- [ ] 视图处理：保存和编辑时处理新字段

#### 2.3 数据库配置管理
- [ ] 新增数据库配置管理页面（位于系统配置分组）
- [ ] 支持添加、编辑、删除、启用/禁用数据库配置
- [ ] 显示配置编码、名称、IP地址、库名

### 3. 数据修改页面UI优化（高优先级）
**文件**: `work_tools/templates/configurable_data.html`

#### 3.1 布局调整
- [ ] 修改字段和原值字段水平排列（使用form-row布局）
- [ ] 每行显示：修改字段 | 原值字段

#### 3.2 数据库选择
- [ ] 添加数据库选择区域
- [ ] 使用复选框列表显示所有启用的数据库配置
- [ ] 默认全选所有启用的数据库

### 4. 视图逻辑完善（高优先级）
**文件**: `work_tools/views/configurable_data.py`

#### 4.1 SQL文件名生成
- [ ] 根据实际填写的修改字段，收集对应的sql_file_name
- [ ] 多个字段用顿号连接：`编号_字段1文件名、字段2文件名.sql`
- [ ] 单个字段：`编号_字段文件名.sql`

#### 4.2 空值处理
- [ ] 检查字段的is_nullable配置
- [ ] 如果字段可为空且用户未填写值，生成空字符串赋值：`FIELD_NAME=''`
- [ ] 不可为空的字段如果未填写则跳过

#### 4.3 数据库配置应用
- [ ] 从表单获取选中的数据库配置
- [ ] 根据选中的配置生成"3.数据库"部分
- [ ] 格式：
```
3.数据库
ip：xxx.xxx.xxx.xxx
库名：xxxx

ip：xxx.xxx.xxx.xxx
库名：xxxx
```

#### 4.4 回退SQL优化
- [ ] 空值字段的回退也要考虑is_nullable
- [ ] 如果原值为空，回退时也赋空字符串

### 5. 动态表单生成优化（中优先级）
**文件**: `work_tools/views/configurable_data.py` - `create_dynamic_form`

- [ ] 添加数据库选择字段（多选复选框）
- [ ] 从DatabaseConfig读取启用的配置
- [ ] 默认全选

### 6. Excel模板生成优化（中优先级）
**文件**: `work_tools/views/configurable_data.py` - `download_template`

- [ ] 模板说明更新，包含is_nullable信息
- [ ] 空值字段也可以在Excel中留空

### 7. 导航菜单优化（低优先级）
**文件**: `work_tools/navigation.py`

- [ ] 在系统配置分组添加"数据库配置管理"菜单项

## 实现顺序建议

1. **第一阶段**：配置管理完善（让用户可以配置新字段）
   - 修改字段配置表单，添加is_nullable和sql_file_name
   - 创建数据库配置管理页面
   
2. **第二阶段**：数据修改页面UI优化
   - 修改模板，水平排列原值和修改值
   - 添加数据库选择区域

3. **第三阶段**：核心逻辑实现
   - 实现动态文件名生成
   - 实现空值字段处理
   - 实现数据库配置应用

4. **第四阶段**：测试和完善
   - 单条修改测试
   - 批量导入测试
   - 回退SQL测试

## 技术要点

### 文件名生成逻辑
```python
# 收集实际填写的修改字段的sql_file_name
file_names = []
for field in update_fields_data:
    field_key = f'update_{field.field_name}'
    if field_key in cd and (cd[field_key] or field.is_nullable):
        if field.sql_file_name:
            file_names.append(field.sql_file_name)

# 组合文件名
if file_names:
    file_prefix = '、'.join(file_names)
    filename = f"{cd.get('dynamic_id')}_{file_prefix}.sql" if cd.get('dynamic_id') else f"{file_prefix}.sql"
```

### 空值字段SQL生成
```python
# 修改字段值收集
for field in update_fields_data:
    field_key = f'update_{field.field_name}'
    value = cd.get(field_key)
    
    if value:  # 有值
        record['update'][field.field_name] = value
    elif field.is_nullable:  # 无值但可为空
        record['update'][field.field_name] = ''  # 空字符串
    # 不可为空且无值则跳过
```

### 数据库配置输出
```python
# 获取选中的数据库配置
selected_db_ids = request.POST.getlist('database_configs')
db_configs = DatabaseConfig.objects.filter(
    id__in=selected_db_ids,
    is_active=True
).order_by('sort_order')

# 生成数据库信息部分
sql.append("3.数据库")
for db in db_configs:
    sql.append(f"ip：{db.db_host}")
    sql.append(f"库名：{db.db_name}")
    if db != db_configs.last():
        sql.append("")  # 空行分隔
```
