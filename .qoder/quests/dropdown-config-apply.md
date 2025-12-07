# 下拉框配置应用到页面设计文档

## 背景与问题

### 当前状态
系统已实现下拉框配置管理功能，包括：
- 数据库表结构：DropdownGroup（配置分组）和 DropdownOption（配置项）
- 配置管理界面：dropdown_config.html，支持分组和选项的增删改查、启用禁用
- 工具函数：dropdown_utils.py 提供 get_dropdown_options 函数从数据库加载配置
- 初始化数据：已迁移4个分组（contract_status、bid_status、report_choice、importance_level）

### 存在问题
配置系统虽然已实现，但实际业务页面并未使用该配置，表现为：
- 页面模板中硬编码下拉选项（如 appr_state_change.html 中直接写死所有合同状态选项）
- Forms 定义中硬编码选项列表（如 APPR_STATE_CHOICES、BID_STATUS_CHOICES、IMPORTANCE_CHOICES 等）
- 在配置管理界面禁用某个选项后，业务页面依然显示该选项
- 无法通过配置动态调整下拉框显示内容

### 改造目标
使业务页面从数据库配置中动态加载下拉框选项，实现配置的真正生效，确保配置管理界面的启用禁用操作能够反映到实际页面中。

## 影响范围分析

### 涉及的配置分组
根据数据库迁移文件，当前系统已配置4个分组：

| 分组编码 | 分组名称 | 用途描述 | 选项数量 |
|---------|---------|---------|---------|
| contract_status | 合同状态 | 合同审批流程各阶段状态值 | 17个（含空选项） |
| bid_status | 中标状态 | 中标结果状态值 | 2个（含空选项） |
| report_choice | 国资委报送 | 是否报送国资委 | 2个 |
| importance_level | 物项重要性 | 物项重要性级别分类 | 5个 |

### 涉及的业务模块

#### 使用 contract_status 的模块
- 表单类：ApprStateChangeForm
- 视图函数：appr_state_change_view
- 模板文件：appr_state_change.html
- 硬编码位置：forms.py 中的 APPR_STATE_CHOICES，模板中的 select 标签

#### 使用 bid_status 的模块
- 表单类：ContractTerminateForm、SourcingTerminateForm
- 视图函数：contract_terminate_view、sourcing_terminate_view
- 模板文件：contract_terminate.html、sourcing_terminate.html
- 硬编码位置：forms.py 中的 BID_STATUS_CHOICES，模板中的 select 标签

#### 使用 report_choice 的模块
- 表单类：GovReportForm
- 视图函数：gov_report_view
- 模板文件：gov_report_form.html
- 硬编码位置：forms.py 中的 GovReportForm.REPORT_CHOICES，使用 RadioSelect 控件

#### 使用 importance_level 的模块
- 表单类：ImportanceForm
- 视图函数：importance_view
- 模板文件：importance_form.html
- 硬编码位置：forms.py 中的 ImportanceForm.IMPORTANCE_CHOICES，使用 Select 控件

## 设计方案

### 整体策略
采用渐进式改造方案，保持向后兼容，确保改造过程中系统稳定运行。

### 改造层次

#### 第一层：表单层改造
将 forms.py 中硬编码的 CHOICES 改为从数据库动态加载。

**改造原则：**
- 保留原有硬编码的 CHOICES 常量作为回退方案，当数据库配置不可用时使用
- 在表单实例化时动态设置字段的 choices 属性
- 利用 dropdown_utils.get_dropdown_options 函数加载配置

**需改造的表单字段：**

| 表单类 | 字段名 | 配置分组编码 | 是否包含空选项 |
|-------|-------|-------------|--------------|
| ApprStateChangeForm | new_appr_state | contract_status | 是 |
| ApprStateChangeForm | orig_appr_state | contract_status | 是 |
| ContractTerminateForm | orig_bid_status | bid_status | 是 |
| SourcingTerminateForm | orig_bid_status | bid_status | 是 |
| GovReportForm | report_choice | report_choice | 否 |
| GovReportForm | orig_report_choice | report_choice | 否 |
| ImportanceForm | importance_choice | importance_level | 否 |
| ImportanceForm | orig_importance_choice | importance_level | 否 |

**表单改造实现方式：**
- 在表单类的 __init__ 方法中调用 get_dropdown_options 加载配置
- 将加载结果赋值给对应字段的 choices 属性
- 处理加载失败情况，回退到硬编码选项

#### 第二层：模板层改造
将模板中硬编码的下拉选项改为从视图传入的上下文数据动态渲染。

**改造原则：**
- 模板不直接调用数据库或工具函数
- 由视图函数准备好下拉选项数据传递给模板
- 使用 Django 模板循环语法动态生成 option 标签

**需改造的模板文件：**

| 模板文件 | 硬编码位置 | 改造方式 |
|---------|-----------|---------|
| appr_state_change.html | 两个 select 标签手动列举 option | 改为通过上下文变量循环生成 |
| contract_terminate.html | select 标签手动列举 option | 改为通过上下文变量循环生成 |
| sourcing_terminate.html | select 标签手动列举 option | 改为通过上下文变量循环生成 |
| gov_report_form.html | RadioSelect 控件（由表单渲染） | 无需改造，表单层改造已覆盖 |
| importance_form.html | Select 控件（由表单渲染） | 无需改造，表单层改造已覆盖 |

**模板改造实现方式：**
- 在视图函数中通过 get_dropdown_options 获取选项列表
- 将选项列表作为上下文变量传递给模板
- 模板使用 {% for %} 循环渲染 option 标签

#### 第三层：视图层改造
调整视图函数，确保配置数据正确传递给模板，并处理 Excel 解析中的状态映射。

**改造要点：**

| 视图函数 | 改造内容 |
|---------|---------|
| appr_state_change_view | 加载 contract_status 选项传递给模板 |
| contract_terminate_view | 加载 bid_status 选项传递给模板 |
| sourcing_terminate_view | 加载 bid_status 选项传递给模板 |
| gov_report_view | 无需改造（使用表单渲染） |
| importance_view | 无需改造（使用表单渲染） |

**Excel解析逻辑改造：**
- 当前 Excel 解析使用硬编码的 STATE_MAP 映射字典
- 改造为从数据库配置动态构建映射字典
- 确保 Excel 中的中文标签能够正确映射为选项编码

改造方法：
- 在解析函数开始时调用 get_dropdown_options 获取配置
- 构建 {option_label: option_code} 映射字典
- 替换原有的硬编码映射字典

#### 第四层：缓存一致性保障
确保配置更新后页面能够及时反映变化。

**现有缓存机制：**
- dropdown_utils 中已实现缓存逻辑（30分钟过期）
- 配置管理视图在增删改禁用操作后会调用 clear_dropdown_cache 清除缓存

**需确保的流程：**
- 配置管理界面修改配置后，对应分组的缓存被清除
- 下次访问业务页面时，从数据库重新加载最新配置
- 无需额外改造，现有机制已满足需求

### 向后兼容策略

#### 回退机制设计
当数据库配置不可用时（如数据库连接失败、配置分组被删除、所有选项被禁用等情况），系统应能够回退到硬编码选项，保证功能可用。

**回退触发条件：**
- get_dropdown_options 返回空列表（排除空选项后）
- 数据库查询抛出异常
- 配置分组被标记为禁用（is_active=False）

**回退实现位置：**
- dropdown_utils._get_fallback_options 函数已实现回退逻辑
- forms.py 中保留原有 CHOICES 常量作为备用
- 在表单初始化失败时使用备用常量

#### 数据一致性保障
确保配置选项的编码值（option_code）与数据库中实际存储的值保持一致。

**验证要点：**
- 初始化数据中的 option_code 应与数据库实际值匹配
- 不允许修改系统内置选项的编码（is_system=True 的选项编码不可修改）
- 新增选项时需确认编码值符合业务规则

**数据迁移验证：**
检查 0005_init_dropdown_data.py 中的初始化数据，确认编码值正确性：
- contract_status 的编码应为大写英文（如 ACTIVE、DRAFT）
- bid_status 的编码应为数字字符串（如 '40'、'50'）
- report_choice 的编码应为 yes/no
- importance_level 的编码应为数字字符串（'0'、'1'、'2'、'3'、'4'）

### 特殊处理场景

#### Select2 搜索框兼容
appr_state_change.html 使用了 Select2 插件提供下拉搜索功能。

**兼容要求：**
- 动态生成的 select 标签需保留 class="select2-search" 属性
- 保留 Select2 初始化的 JavaScript 代码
- 确保动态选项能够被 Select2 正常识别和搜索

**实现方式：**
- 模板改造时保留 select 标签的所有属性
- 只替换 option 标签的生成逻辑

#### RadioSelect 控件处理
gov_report_form.html 中的报送选项使用 RadioSelect 控件（单选按钮组）。

**处理方式：**
- RadioSelect 由 Django 表单自动渲染
- 表单层改造完成后，控件会自动使用新的 choices
- 模板无需修改，直接使用 {{ form.report_choice }} 渲染

#### 空选项处理策略
不同字段对空选项的需求不同。

**需要空选项的字段：**
- contract_status 的两个字段（新/原合同状态）：需要"请选择"提示
- bid_status 的字段（中标状态）：需要"请选择"提示

**不需要空选项的字段：**
- report_choice：只有是/否两个选项，使用 RadioSelect，无需空选项
- importance_level：使用 Select 控件但业务上需选择具体值，无需空选项

**实现方式：**
- 通过 get_dropdown_options 的 include_empty 参数控制
- 根据字段特性传入对应的参数值

## 实施步骤

### 第一阶段：表单层改造

#### 步骤1.1：改造 ApprStateChangeForm
- 在 __init__ 方法中加载 contract_status 配置
- 为 new_appr_state 和 orig_appr_state 字段设置动态 choices
- 添加异常处理，失败时使用 APPR_STATE_CHOICES 常量

#### 步骤1.2：改造 ContractTerminateForm 和 SourcingTerminateForm
- 在 __init__ 方法中加载 bid_status 配置
- 为 orig_bid_status 字段设置动态 choices
- 添加异常处理，失败时使用 BID_STATUS_CHOICES 常量

#### 步骤1.3：改造 GovReportForm
- 在 __init__ 方法中加载 report_choice 配置
- 为 report_choice 和 orig_report_choice 字段设置动态 choices
- 添加异常处理，失败时使用表单内定义的 REPORT_CHOICES 常量

#### 步骤1.4：改造 ImportanceForm
- 在 __init__ 方法中加载 importance_level 配置
- 为 importance_choice 和 orig_importance_choice 字段设置动态 choices
- 添加异常处理，失败时使用表单内定义的 IMPORTANCE_CHOICES 常量

### 第二阶段：视图和模板层改造

#### 步骤2.1：改造 appr_state_change 模块
视图函数改造：
- 在 appr_state_change_view 中调用 get_dropdown_options 加载合同状态选项
- 将选项列表添加到模板上下文（键名：contract_status_options）

模板改造：
- 将 id_new_appr_state 和 id_orig_appr_state 的 select 标签中硬编码的 option 替换为循环生成
- 循环遍历 contract_status_options，生成 option 标签

Excel解析改造：
- 在 parse_appr_state_excel 函数开始时加载配置构建 STATE_MAP
- 替换硬编码的映射字典

#### 步骤2.2：改造 contract_terminate 模块
视图函数改造：
- 在 contract_terminate_view 中加载 bid_status 选项
- 将选项列表添加到模板上下文

模板改造：
- 将 select 标签中的硬编码 option 替换为循环生成

Excel解析改造：
- 在解析函数中动态构建 BID_STATUS_MAP

#### 步骤2.3：改造 sourcing_terminate 模块
视图函数改造：
- 在 sourcing_terminate_view 中加载 bid_status 选项
- 将选项列表添加到模板上下文

模板改造：
- 将 select 标签中的硬编码 option 替换为循环生成

Excel解析改造：
- 在解析函数中动态构建状态映射

### 第三阶段：测试与验证

#### 功能测试项

| 测试项 | 测试内容 | 预期结果 |
|-------|---------|---------|
| 页面加载测试 | 访问各业务页面，检查下拉框是否正常显示 | 下拉选项与数据库配置一致 |
| 配置生效测试 | 在配置管理界面禁用某个选项后，访问业务页面 | 被禁用的选项不再显示 |
| 配置启用测试 | 重新启用被禁用的选项，刷新业务页面 | 选项重新出现 |
| 新增选项测试 | 在配置管理界面新增一个选项，访问业务页面 | 新选项出现在下拉框中 |
| 排序测试 | 修改选项的 sort_order，刷新业务页面 | 选项按新的排序顺序显示 |
| 回退机制测试 | 禁用整个配置分组或清空所有选项 | 页面回退到硬编码选项，功能正常 |

#### Excel解析测试项

| 测试项 | 测试内容 | 预期结果 |
|-------|---------|---------|
| 中文标签解析 | Excel中使用中文状态名称（如"草稿"） | 正确映射为编码值（如"DRAFT"） |
| 编码直接使用 | Excel中直接使用编码（如"ACTIVE"） | 正确识别并处理 |
| 禁用选项提交 | 提交包含已禁用选项的Excel | 应提示错误或使用回退映射 |

#### 缓存一致性测试

| 测试项 | 测试内容 | 预期结果 |
|-------|---------|---------|
| 修改后立即刷新 | 修改配置后立即访问业务页面 | 页面显示最新配置 |
| 缓存过期测试 | 修改配置30分钟后访问 | 页面显示最新配置 |
| 多分组隔离 | 修改分组A，访问使用分组B的页面 | 分组B页面不受影响 |

### 第四阶段：文档和培训

#### 更新系统文档
- 在配置管理界面添加使用说明，说明配置如何影响业务页面
- 明确标注哪些选项为系统内置（不可删除、编码不可修改）
- 说明禁用分组或选项的影响范围

#### 用户培训要点
- 如何添加和管理下拉选项
- 禁用选项的效果和影响
- 系统内置选项的限制
- 修改配置后的生效时机（立即生效，缓存最多30分钟）

## 风险与应对

### 风险识别

#### 风险1：配置数据不完整导致功能异常
**风险描述：**
- 配置分组被误删除
- 所有选项被禁用
- 必要的选项编码与数据库实际值不匹配

**应对措施：**
- 实现完善的回退机制，确保配置不可用时使用硬编码选项
- 在配置管理界面添加删除确认，防止误操作
- 对系统内置选项（is_system=True）限制删除和编码修改

#### 风险2：缓存不一致导致显示延迟
**风险描述：**
- 修改配置后，部分服务器节点缓存未清除
- 用户看到的选项与配置不一致

**应对措施：**
- 确保配置修改操作调用 clear_dropdown_cache
- 缩短缓存过期时间（如有必要）
- 提供手动清除缓存的管理接口

#### 风险3：Excel解析映射失败
**风险描述：**
- 禁用某个选项后，Excel中仍使用该选项的标签
- 解析时找不到对应的编码值

**应对措施：**
- Excel解析时，对于找不到映射的值，给出明确错误提示
- 在错误信息中列出当前可用的选项
- 提供Excel模板下载功能，确保用户使用最新的选项列表

#### 风险4：模板渲染性能影响
**风险描述：**
- 每次页面加载都从数据库查询配置
- 高并发时数据库压力增大

**应对措施：**
- 依赖现有的缓存机制（30分钟）减少数据库查询
- 如性能不足，考虑引入应用层缓存（如Redis）
- 对于极高频访问的页面，考虑在视图层缓存选项数据

### 回滚预案
如改造后出现严重问题，需要快速回滚：

#### 快速回滚步骤
- 恢复 forms.py 中的硬编码 CHOICES 赋值逻辑
- 恢复模板中的硬编码 option 标签
- 恢复视图函数中的硬编码映射字典
- 重启应用服务

#### 保留措施
- 改造前对所有涉及文件进行版本备份
- 改造过程中保留硬编码常量，不删除
- 使用特性开关控制是否启用动态配置（可选）

## 后续优化方向

### 优化方向1：配置版本控制
- 记录配置修改历史
- 支持配置的回滚到历史版本
- 审计配置变更记录

### 优化方向2：配置验证增强
- 新增选项时校验编码的唯一性和合法性
- 验证必要选项是否存在（如空选项、默认选项）
- 提供配置完整性检查工具

### 优化方向3：性能优化
- 引入分布式缓存（Redis）替代 Django 内置缓存
- 实现配置的预加载机制
- 支持配置的批量更新和发布

### 优化方向4：配置导入导出
- 支持配置的导出为JSON或Excel
- 支持配置的批量导入
- 便于环境间配置迁移

### 优化方向5：国际化支持
- 支持选项标签的多语言
- 根据用户语言偏好显示对应标签
- 保持编码值不变，仅标签国际化

## 附录

### 涉及文件清单

| 文件路径 | 文件类型 | 改造内容 |
|---------|---------|---------|
| work_tools/forms.py | Python | 改造表单类的 __init__ 方法 |
| work_tools/views/appr_state.py | Python | 改造视图函数和Excel解析函数 |
| work_tools/views/contract_terminate.py | Python | 改造视图函数和Excel解析函数 |
| work_tools/views/sourcing_terminate.py | Python | 改造视图函数和Excel解析函数 |
| work_tools/views/gov_report.py | Python | 改造视图函数（如存在） |
| work_tools/views/importance.py | Python | 改造视图函数（如存在） |
| work_tools/templates/appr_state_change.html | HTML | 改造 select 标签的 option 生成逻辑 |
| work_tools/templates/contract_terminate.html | HTML | 改造 select 标签的 option 生成逻辑 |
| work_tools/templates/sourcing_terminate.html | HTML | 改造 select 标签的 option 生成逻辑 |

### 配置分组与字段映射表

| 配置分组编码 | 表单类 | 字段名 | 控件类型 | 空选项 |
|-------------|-------|-------|---------|-------|
| contract_status | ApprStateChangeForm | new_appr_state | Select | 是 |
| contract_status | ApprStateChangeForm | orig_appr_state | Select | 是 |
| bid_status | ContractTerminateForm | orig_bid_status | Select | 是 |
| bid_status | SourcingTerminateForm | orig_bid_status | Select | 是 |
| report_choice | GovReportForm | report_choice | RadioSelect | 否 |
| report_choice | GovReportForm | orig_report_choice | RadioSelect | 否 |
| importance_level | ImportanceForm | importance_choice | Select | 否 |
| importance_level | ImportanceForm | orig_importance_choice | Select | 否 |

### 关键API说明

#### get_dropdown_options 函数
**函数签名：**
```
get_dropdown_options(group_code, include_empty=True, empty_label='请选择')
```

**参数说明：**
- group_code：配置分组编码（字符串）
- include_empty：是否包含空选项（布尔值，默认True）
- empty_label：空选项的显示文本（字符串，默认'请选择'）

**返回值：**
- 元组列表，格式为 [(option_code, option_label), ...]
- 仅返回启用的选项（is_active=True）
- 按 sort_order 和 option_code 排序

**使用示例：**
```
# 加载合同状态选项（包含空选项）
options = get_dropdown_options('contract_status', include_empty=True, empty_label='请选择合同状态')

# 加载重要性选项（不包含空选项）
options = get_dropdown_options('importance_level', include_empty=False)
```

#### clear_dropdown_cache 函数
**函数签名：**
```
clear_dropdown_cache(group_code=None)
```

**参数说明：**
- group_code：配置分组编码（字符串），为None时清除所有缓存

**使用场景：**
- 配置管理界面修改选项后调用
- 数据迁移或批量更新后调用
- 手动刷新配置时调用

### 模板循环示例

**Select控件的option循环生成：**
```
<select name="field_name" id="id_field_name" class="form-control">
  {% for code, label in dropdown_options %}
    <option value="{{ code }}">{{ label }}</option>
  {% endfor %}
</select>
```

**保持选中状态的写法：**
```
<select name="field_name" id="id_field_name" class="form-control">
  {% for code, label in dropdown_options %}
    <option value="{{ code }}" {% if code == selected_value %}selected{% endif %}>
      {{ label }}
    </option>
  {% endfor %}
</select>
```

**RadioSelect由表单渲染，无需手动循环：**
```
{{ form.field_name }}
```
