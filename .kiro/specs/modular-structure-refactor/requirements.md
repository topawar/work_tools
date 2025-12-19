# 模块化结构重构需求文档

## 简介

本文档定义了将 work_tools 项目重构为模块化结构的需求。目标是将分散在 `work_tools/views/` 和 `work_tools/templates/` 目录中的相关文件按照已有的导航菜单分组，重新组织到 `work_tools/modules/` 目录下，提高代码的可维护性和可扩展性。

## 术语表

- **模块 (Module)**: 具有相关功能的代码、模板和静态资源的集合，对应导航菜单中的一个分组
- **视图 (View)**: Django 视图函数或类，处理 HTTP 请求
- **模板 (Template)**: HTML 模板文件
- **静态资源 (Static Assets)**: CSS、JavaScript 等前端资源
- **公共包 (Common Package)**: 被多个模块共享使用的代码和资源
- **导航分组 (Navigation Group)**: 在 navigation.py 中定义的菜单分组

## 需求

### 需求 1: 按导航分组识别功能模块

**用户故事**: 作为开发人员，我希望按照已有的导航菜单分组来组织代码，以便代码结构与用户界面保持一致。

#### 验收标准

1. WHEN 分析现有代码时，THEN 系统应当识别出以下功能模块（对应 navigation.py 中的分组）：
   - **contract** 模块（合同）：明细单价修改、物资编码修改、合同预算修改、合同失效日期修改、适用清单修改、合同状态修改、合同创建人修改、终止合同、终止简化寻源合同
   - **procurement** 模块（计划-寻源）：合同起草签约单位修改、是否报送国资委、物项重要性修改、浮动单价类型修改、核电ERP终止、项目轮次、需求计划明细日期修改、订单执行人修改
   - **data_import** 模块（数据导入）：组织机构导入、用户组织机构导入、物资信息导入
   - **job_management** 模块（任务管理）：导入任务
   - **system_config** 模块（系统配置）：SQL合并策略、文件路径配置、临时文件清理、下拉框配置管理、可配置表管理、数据库配置管理
   - **configurable** 模块（特殊模板）：动态生成的可配置表页面

2. WHEN 识别模块时，THEN 系统应当记录每个模块包含的视图文件、模板文件和相关静态资源

3. WHEN 识别公共组件时，THEN 系统应当识别出以下公共包：
   - 基础工具（utils）：通用工具函数
   - 表单组件（forms）：共享表单定义
   - 中间件（middleware）：请求处理中间件
   - 模板标签（templatetags）：自定义模板标签
   - 静态资源（static）：共享的 CSS、JavaScript
   - 共享模板（templates）：base_config.html、sidebar.html、success.html、errors/、tags/

### 需求 2: 设计模块目录结构

**用户故事**: 作为开发人员，我希望有一个清晰的模块目录结构，以便快速定位和修改代码。

#### 验收标准

1. WHEN 设计目录结构时，THEN 每个功能模块应当遵循以下结构（参考已有的 system_config 模块）：
   ```
   work_tools/modules/{module_name}/
   ├── __init__.py
   └── views.py          # 该模块的所有视图函数
   
   work_tools/templates/modules/{module_name}/
   └── *.html            # 该模块的所有模板文件
   
   work_tools/static/css/
   └── {module_name}.css # 该模块专用样式（如果需要）
   ```

2. WHEN 设计公共包结构时，THEN 应当保持以下目录不变：
   ```
   work_tools/
   ├── utils/            # 通用工具（保持不变）
   ├── middleware/       # 中间件（保持不变）
   ├── templatetags/     # 模板标签（保持不变）
   ├── forms.py          # 共享表单定义（保持不变）
   ├── models.py         # 数据模型（保持不变）
   ├── templates/        # 共享模板
   │   ├── base_config.html
   │   ├── sidebar.html
   │   ├── success.html
   │   ├── errors/
   │   └── tags/
   └── static/           # 共享静态资源
       ├── css/
       │   ├── base/
       │   ├── components/
       │   └── modern-ui.css
       └── js/
   ```

3. WHEN 组织模块时，THEN 应当确保模块之间的依赖关系清晰，避免循环依赖

4. WHEN 模块已经部分迁移时（如 system_config），THEN 应当保持其现有结构不变

### 需求 3: 创建文件迁移映射表

**用户故事**: 作为开发人员，我希望有一个详细的文件迁移映射表，以便了解每个文件应该移动到哪里。

#### 验收标准

1. WHEN 创建迁移映射表时，THEN 应当按照导航分组将视图文件映射到对应模块：
   - **contract 模块**: contract_price.py, contract_item.py, contract_budget.py, enddate.py, use_list.py, appr_state.py, contract_creator.py, contract_terminate.py, sourcing_terminate.py
   - **procurement 模块**: contract_unit.py, gov_report.py, importance.py, price_type.py, erp_terminate.py, project_round.py, plan_date.py, order_executor.py
   - **data_import 模块**: org_api.py, user_org_manage.py, item_manage.py
   - **job_management 模块**: job_manage.py
   - **system_config 模块**: 已迁移（system_config.py, dropdown_config.py, configurable_config.py, database_config.py）
   - **configurable 模块**: configurable_data.py

2. WHEN 创建迁移映射表时，THEN 应当将模板文件映射到对应模块的模板目录

3. WHEN 识别公共文件时，THEN base.py 应当保留在 work_tools/views/ 目录作为公共基础视图

### 需求 4: 更新导入语句

**用户故事**: 作为开发人员，我希望所有导入语句自动更新，以便代码能够在新结构下正常运行。

#### 验收标准

1. WHEN 文件被移动后，THEN 所有引用该文件的导入语句应当更新为新路径

2. WHEN 更新导入语句时，THEN 应当保持代码的功能不变

3. WHEN 更新完成后，THEN 应当运行测试以验证所有导入都正确

### 需求 5: 更新 URL 配置

**用户故事**: 作为开发人员，我希望 URL 配置能够反映新的模块结构，以便路由更加清晰。

#### 验收标准

1. WHEN 重构 URL 配置时，THEN 应当考虑为每个模块创建独立的 urls.py

2. WHEN 模块有独立的 urls.py 时，THEN 主 urls.py 应当使用 include() 引入模块路由

3. WHEN URL 配置更新后，THEN 所有现有的 URL 路径应当保持不变，确保向后兼容

### 需求 6: 更新模板路径

**用户故事**: 作为开发人员，我希望模板路径能够自动更新，以便视图能够找到正确的模板文件。

#### 验收标准

1. WHEN 模板文件被移动到模块目录时，THEN 视图中的模板路径应当更新

2. WHEN 使用模板时，THEN Django 的模板加载器应当能够从模块目录和共享目录加载模板

3. WHEN 模板继承时，THEN 基础模板的路径应当保持在共享目录

### 需求 7: 更新静态资源引用

**用户故事**: 作为开发人员，我希望静态资源引用能够自动更新，以便页面能够正确加载样式和脚本。

#### 验收标准

1. WHEN 静态资源被移动到模块目录时，THEN 模板中的静态资源引用应当更新

2. WHEN 加载静态资源时，THEN Django 的静态文件查找器应当能够从模块目录和共享目录查找文件

3. WHEN 打包应用时，THEN 所有静态资源应当被正确收集到 STATIC_ROOT

### 需求 8: 验证重构结果

**用户故事**: 作为开发人员，我希望能够验证重构后的代码功能完整，以便确保没有引入错误。

#### 验收标准

1. WHEN 重构完成后，THEN 应当运行所有现有测试，确保测试通过

2. WHEN 验证功能时，THEN 应当手动测试每个主要功能模块，确保页面正常显示和功能正常工作

3. WHEN 检查代码质量时，THEN 应当确保没有未使用的导入、循环依赖或其他代码问题

4. WHEN 验证打包时，THEN 应当确保打包后的应用能够正常运行

### 需求 9: 更新文档

**用户故事**: 作为开发人员，我希望文档能够反映新的项目结构，以便团队成员能够快速适应。

#### 验收标准

1. WHEN 重构完成后，THEN 应当更新 README.md 文档，说明新的目录结构

2. WHEN 更新文档时，THEN 应当提供模块化开发指南，说明如何添加新模块

3. WHEN 文档更新后，THEN 应当包含迁移指南，帮助理解从旧结构到新结构的变化

### 需求 10: 保持向后兼容

**用户故事**: 作为系统维护者，我希望重构过程保持向后兼容，以便现有功能不受影响。

#### 验收标准

1. WHEN 重构代码时，THEN 所有现有的 URL 路径应当保持不变

2. WHEN 重构代码时，THEN 所有现有的 API 接口应当保持不变

3. WHEN 重构代码时，THEN 数据库模型和迁移应当保持不变

4. WHEN 重构代码时，THEN 配置文件格式应当保持不变
