# 模块化结构重构设计文档

## 概述

本文档描述了将 work_tools 项目按照导航菜单分组重构为模块化结构的详细设计方案。重构将把分散在 `work_tools/views/` 和 `work_tools/templates/` 中的文件按功能模块重新组织到 `work_tools/modules/` 目录下。

## 架构

### 当前架构

```
work_tools/
├── views/
│   ├── __init__.py
│   ├── base.py
│   ├── contract_price.py
│   ├── contract_item.py
│   ├── ... (20+ 个视图文件)
│   └── system_config.py
├── templates/
│   ├── contract_price_form.html
│   ├── contract_item_form.html
│   ├── ... (30+ 个模板文件)
│   └── modules/
│       └── system_config/  (已迁移)
└── modules/
    └── system_config/  (已迁移)
```

### 目标架构

```
work_tools/
├── views/
│   ├── __init__.py  (导入所有模块视图)
│   └── base.py      (公共基础视图)
├── modules/
│   ├── contract/
│   │   ├── __init__.py
│   │   ├── contract_price.py
│   │   ├── contract_item.py
│   │   ├── contract_budget.py
│   │   ├── enddate.py
│   │   ├── use_list.py
│   │   ├── appr_state.py
│   │   ├── contract_creator.py
│   │   ├── contract_terminate.py
│   │   └── sourcing_terminate.py
│   ├── procurement/
│   │   ├── __init__.py
│   │   ├── contract_unit.py
│   │   ├── gov_report.py
│   │   ├── importance.py
│   │   ├── price_type.py
│   │   ├── erp_terminate.py
│   │   ├── project_round.py
│   │   ├── plan_date.py
│   │   └── order_executor.py
│   ├── data_import/
│   │   ├── __init__.py
│   │   ├── org_api.py
│   │   ├── user_org_manage.py
│   │   └── item_manage.py
│   ├── job_management/
│   │   ├── __init__.py
│   │   └── job_manage.py
│   ├── system_config/  (需要补充)
│   │   ├── __init__.py
│   │   ├── system_config.py  (已存在)
│   │   ├── dropdown_config.py  (需要移动)
│   │   ├── configurable_config.py  (需要移动)
│   │   └── database_config.py  (需要移动)
│   └── configurable/
│       ├── __init__.py
│       └── configurable_data.py
├── templates/
│   ├── base_config.html  (共享)
│   ├── sidebar.html      (共享)
│   ├── success.html      (共享)
│   ├── errors/           (共享)
│   ├── tags/             (共享)
│   └── modules/
│       ├── contract/
│       ├── procurement/
│       ├── data_import/
│       ├── job_management/
│       ├── system_config/  (已存在)
│       └── configurable/
└── static/
    └── css/
        ├── contract.css       (如需要)
        ├── procurement.css    (如需要)
        └── system-pages.css   (已存在)
```

## 组件和接口

### 模块结构

每个模块遵循统一的结构：

#### 1. contract 模块（合同）

**视图文件**:
- `work_tools/modules/contract/contract_price.py` - 明细单价修改
- `work_tools/modules/contract/contract_item.py` - 物资编码修改
- `work_tools/modules/contract/contract_budget.py` - 合同预算修改
- `work_tools/modules/contract/enddate.py` - 合同失效日期修改
- `work_tools/modules/contract/use_list.py` - 适用清单修改
- `work_tools/modules/contract/appr_state.py` - 合同状态修改
- `work_tools/modules/contract/contract_creator.py` - 合同创建人修改
- `work_tools/modules/contract/contract_terminate.py` - 终止合同
- `work_tools/modules/contract/sourcing_terminate.py` - 终止简化寻源合同

**模板目录**: `work_tools/templates/modules/contract/`

包含的模板文件：
- `contract_price_form.html`
- `contract_item_form.html`
- `contract_budget_form.html`
- `end_date_form.html`
- `use_list_update_form.html`
- `appr_state_change.html`
- `contract_creator_form.html`
- `contract_terminate.html`
- `sourcing_terminate.html`

#### 2. procurement 模块（计划-寻源）

**视图文件**:
- `work_tools/modules/procurement/contract_unit.py` - 合同起草、签约单位修改
- `work_tools/modules/procurement/gov_report.py` - 是否报送国资委
- `work_tools/modules/procurement/importance.py` - 物项重要性修改
- `work_tools/modules/procurement/price_type.py` - 浮动单价类型修改
- `work_tools/modules/procurement/erp_terminate.py` - 核电ERP终止
- `work_tools/modules/procurement/project_round.py` - 项目轮次
- `work_tools/modules/procurement/plan_date.py` - 需求计划明细日期修改
- `work_tools/modules/procurement/order_executor.py` - 订单执行人修改

**模板目录**: `work_tools/templates/modules/procurement/`

包含的模板文件：
- `unit_change_form.html`
- `gov_report_form.html`
- `importance_form.html`
- `floating_price_type_form.html`
- `erp_terminate_form.html`
- `project_round.html`
- `plan_date_form.html`
- `order_executor_form.html`

#### 3. data_import 模块（数据导入）

**视图文件**:
- `work_tools/modules/data_import/org_api.py` - 组织机构导入和搜索API
- `work_tools/modules/data_import/user_org_manage.py` - 用户组织机构导入
- `work_tools/modules/data_import/item_manage.py` - 物资信息导入和管理API

**模板目录**: `work_tools/templates/modules/data_import/`

包含的模板文件：
- `org_import.html`
- `user_org_import.html`
- `item_import.html`

#### 4. job_management 模块（任务管理）

**视图文件**:
- `work_tools/modules/job_management/job_manage.py` - 任务管理（列表、详情、状态、删除等）

**模板目录**: `work_tools/templates/modules/job_management/`

包含的模板文件：
- `jobs.html`
- `job_detail.html`

#### 5. system_config 模块（系统配置）

**状态**: 已部分迁移

**视图文件**:
- `work_tools/modules/system_config/system_config.py` - SQL合并策略、文件路径、临时文件清理（已存在，但实际在 views.py 中）
- `work_tools/modules/system_config/dropdown_config.py` - 下拉框配置管理（需要从 work_tools/views/ 移动）
- `work_tools/modules/system_config/configurable_config.py` - 可配置表管理（需要从 work_tools/views/ 移动）
- `work_tools/modules/system_config/database_config.py` - 数据库配置管理（需要从 work_tools/views/ 移动）

**注意**: 当前 system_config 模块的视图实际在 `views.py` 文件中，需要考虑是否重命名或保持现状

**模板目录**: `work_tools/templates/modules/system_config/`

已包含的模板文件：
- `system_config.html`
- `file_path_config.html`
- `cleanup_config.html`

需要迁移的模板文件：
- `dropdown_config.html`
- `configurable_config.html`
- `database_config.html`

#### 6. configurable 模块（特殊模板）

**视图文件**:
- `work_tools/modules/configurable/configurable_data.py` - 可配置数据修改（需要从 work_tools/views/ 移动）

**模板目录**: `work_tools/templates/modules/configurable/`

包含的模板文件：
- `configurable_data.html`

### 公共组件

保持在原位置不变：

1. **基础视图**: `work_tools/views/base.py`
   - 包含公共工具函数：`parse_ops_remark`, `extract_company_code`, `extract_company_name`

2. **共享模板**: `work_tools/templates/`
   - `base_config.html` - 基础配置页面模板
   - `sidebar.html` - 侧边栏模板
   - `success.html` - 成功页面模板
   - `errors/` - 错误页面模板
   - `tags/` - 模板标签

3. **共享静态资源**: `work_tools/static/`
   - `css/base/` - 基础样式
   - `css/components/` - 组件样式
   - `css/modern-ui.css` - 现代UI样式
   - `js/` - JavaScript文件

4. **其他公共组件**:
   - `work_tools/utils/` - 工具函数
   - `work_tools/middleware/` - 中间件
   - `work_tools/templatetags/` - 模板标签
   - `work_tools/forms.py` - 表单定义
   - `work_tools/models.py` - 数据模型

## 数据模型

数据模型保持不变，不需要修改。

## 正确性属性

*属性是应该在系统所有有效执行中保持为真的特征或行为——本质上是关于系统应该做什么的正式陈述。属性作为人类可读规范和机器可验证正确性保证之间的桥梁。*

### 属性 1: 模块导入一致性

*对于任何*模块，从 `work_tools.views` 导入的视图函数应该与从 `work_tools.modules.{module_name}.views` 直接导入的结果相同
**验证需求: 1.1, 4.1**

### 属性 2: URL 路由不变性

*对于任何*现有的 URL 路径，重构前后应该路由到相同的视图函数
**验证需求: 5.3**

### 属性 3: 模板路径解析

*对于任何*视图函数，当渲染模板时，Django 模板加载器应该能够从模块目录或共享目录找到正确的模板文件
**验证需求: 6.2**

### 属性 4: 静态资源可访问性

*对于任何*静态资源引用，Django 静态文件查找器应该能够从模块目录或共享目录找到该文件
**验证需求: 7.2**

### 属性 5: 导入语句正确性

*对于任何*被移动的文件，所有引用该文件的导入语句应该更新为新路径，且代码功能保持不变
**验证需求: 4.1, 4.2**

### 属性 6: 模块独立性

*对于任何*两个不同的模块，它们之间不应该存在直接的导入依赖（除了通过公共组件）
**验证需求: 2.3**

### 属性 7: 打包完整性

*对于任何*静态资源文件，在执行 collectstatic 后应该被正确收集到 STATIC_ROOT 目录
**验证需求: 7.3**

## 错误处理

### 导入错误处理

如果模块导入失败，应该：
1. 在 `work_tools/views/__init__.py` 中捕获 ImportError
2. 记录详细的错误信息到日志
3. 提供清晰的错误消息指示哪个模块导入失败

### 模板未找到处理

如果模板文件未找到，应该：
1. Django 会抛出 TemplateDoesNotExist 异常
2. 检查模板路径是否正确更新
3. 检查 TEMPLATES 配置中的 DIRS 和 APP_DIRS 设置

### 静态文件未找到处理

如果静态文件未找到，应该：
1. 在开发环境中返回 404
2. 检查静态文件路径是否正确更新
3. 确保运行了 collectstatic 命令

## 测试策略

### 单元测试

为每个模块创建单元测试：

1. **导入测试**: 验证所有视图函数可以正确导入
2. **URL 测试**: 验证所有 URL 路由正确解析到视图函数
3. **模板测试**: 验证所有模板文件可以被找到和渲染
4. **功能测试**: 验证每个视图函数的基本功能正常

### 集成测试

1. **端到端测试**: 测试每个页面的完整流程
2. **导航测试**: 验证侧边栏导航链接正确
3. **静态资源测试**: 验证页面正确加载所有CSS和JS文件

### 手动测试

重构完成后，手动测试每个导航菜单项：
1. 点击每个菜单项，确保页面正常显示
2. 测试每个表单的提交功能
3. 测试文件下载功能
4. 测试API接口

## 迁移步骤

### 阶段 1: 准备工作

1. 创建所有模块目录结构
2. 创建模块的 `__init__.py` 文件
3. 创建模板目录结构

### 阶段 2: 迁移 contract 模块

1. 移动视图文件到 `work_tools/modules/contract/`:
   - `contract_price.py`
   - `contract_item.py`
   - `contract_budget.py`
   - `enddate.py`
   - `use_list.py`
   - `appr_state.py`
   - `contract_creator.py`
   - `contract_terminate.py`
   - `sourcing_terminate.py`
2. 移动模板文件到 `work_tools/templates/modules/contract/`
3. 更新视图文件中的模板路径引用（从 `template_name.html` 改为 `modules/contract/template_name.html`）
4. 更新 `work_tools/modules/contract/__init__.py` 导入所有视图
5. 更新 `work_tools/views/__init__.py` 从新位置导入
6. 测试所有功能

### 阶段 3: 迁移 procurement 模块

1. 移动视图文件到 `work_tools/modules/procurement/`:
   - `contract_unit.py`
   - `gov_report.py`
   - `importance.py`
   - `price_type.py`
   - `erp_terminate.py`
   - `project_round.py`
   - `plan_date.py`
   - `order_executor.py`
2. 移动模板文件到 `work_tools/templates/modules/procurement/`
3. 更新视图文件中的模板路径引用
4. 更新 `work_tools/modules/procurement/__init__.py` 导入所有视图
5. 更新 `work_tools/views/__init__.py` 从新位置导入
6. 测试所有功能

### 阶段 4: 迁移 data_import 模块

1. 移动视图文件到 `work_tools/modules/data_import/`:
   - `org_api.py`
   - `user_org_manage.py`
   - `item_manage.py`
2. 移动模板文件到 `work_tools/templates/modules/data_import/`
3. 更新视图文件中的模板路径引用
4. 更新 `work_tools/modules/data_import/__init__.py` 导入所有视图
5. 更新 `work_tools/views/__init__.py` 从新位置导入
6. 测试所有功能

### 阶段 5: 迁移 job_management 模块

1. 移动视图文件到 `work_tools/modules/job_management/`:
   - `job_manage.py`
2. 移动模板文件到 `work_tools/templates/modules/job_management/`
3. 更新视图文件中的模板路径引用
4. 更新 `work_tools/modules/job_management/__init__.py` 导入所有视图
5. 更新 `work_tools/views/__init__.py` 从新位置导入
6. 测试所有功能

### 阶段 6: 完善 system_config 模块

1. 移动视图文件到 `work_tools/modules/system_config/`:
   - `dropdown_config.py` (从 work_tools/views/)
   - `configurable_config.py` (从 work_tools/views/)
   - `database_config.py` (从 work_tools/views/)
2. 移动模板文件到 `work_tools/templates/modules/system_config/`:
   - `dropdown_config.html`
   - `configurable_config.html`
   - `database_config.html`
3. 更新视图文件中的模板路径引用
4. 更新 `work_tools/modules/system_config/__init__.py` 导入新增的视图
5. 更新 `work_tools/views/__init__.py` 从新位置导入
6. 测试所有功能

### 阶段 7: 迁移 configurable 模块

1. 移动视图文件到 `work_tools/modules/configurable/`:
   - `configurable_data.py`
2. 移动模板文件到 `work_tools/templates/modules/configurable/`:
   - `configurable_data.html`
3. 更新视图文件中的模板路径引用
4. 更新 `work_tools/modules/configurable/__init__.py` 导入所有视图
5. 更新 `work_tools/views/__init__.py` 从新位置导入
6. 测试所有功能

### 阶段 8: 更新导入和清理

1. 更新 `work_tools/views/__init__.py` 导入所有模块视图
2. 删除旧的视图文件（保留 base.py）
3. 删除旧的模板文件（保留共享模板）
4. 运行所有测试
5. 更新文档

### 阶段 9: 验证和优化

1. 运行完整的测试套件
2. 手动测试所有功能
3. 检查代码质量
4. 优化导入语句
5. 更新文档

## 向后兼容性

### URL 兼容性

所有现有的 URL 路径保持不变，确保：
- 外部链接不会失效
- 书签继续有效
- API 接口保持稳定

### 导入兼容性

通过 `work_tools/views/__init__.py` 重新导出所有视图函数，确保：
- 现有的导入语句继续有效
- 第三方代码不需要修改
- 测试代码不需要大量修改

### 配置兼容性

所有配置文件格式保持不变：
- settings.py 只需要更新 TEMPLATES 配置（如果需要）
- urls.py 保持不变（通过 views.__init__ 导入）
- 数据库模型和迁移不变

## 性能考虑

### 导入性能

- 模块化后，可以实现按需导入
- 减少启动时的导入开销
- 但当前实现仍然在 `__init__.py` 中导入所有模块以保持兼容性

### 模板加载性能

- Django 模板加载器会按顺序搜索模板目录
- 模块化后可能略微增加模板查找时间
- 可以通过缓存模板加载器优化

### 静态文件性能

- 静态文件查找性能不受影响
- collectstatic 时间可能略微增加
- 生产环境使用 CDN 或静态文件服务器不受影响

## 文档更新

需要更新的文档：

1. **README.md**: 更新项目结构说明
2. **模块开发指南**: 创建新文档说明如何添加新模块
3. **迁移指南**: 创建文档说明从旧结构到新结构的变化
4. **API 文档**: 更新导入路径示例
5. **部署文档**: 确保部署步骤仍然有效
