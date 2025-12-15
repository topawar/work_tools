# 页面样式与功能一致性校验设计文档

## 1. 需求背景

为确保系统中所有功能页面的用户体验一致性和配置持久化的正确性,需要对项目进行全面的标准化校验和修复。

## 2. 校验范围

本次校验覆盖以下四个维度:

### 2.1 样式统一性校验

**目标**: 确保所有页面的清除和生成 SQL 按钮样式完全一致

**涉及页面范围**:

- 合同相关: contract_price_form.html、contract_item_form.html、contract_budget_form.html、end_date_form.html、use_list_update_form.html、contract_terminate.html、contract_creator_form.html
- 计划寻源相关: unit_change_form.html、gov_report_form.html、importance_form.html、floating_price_type_form.html、erp_terminate_form.html、plan_date_form.html、order_executor_form.html、project_round.html、appr_state_change.html、sourcing_terminate.html
- 可配置数据: configurable_data.html

### 2.2 表单值保留行为校验

**目标**: 确保点击生成 SQL 后,页面除清除按钮外的所有输入值保持不变

**涉及页面范围**: 同 2.1 节所有页面

### 2.3 成功提示完整性校验

**目标**: 确保所有生成 SQL 完成后页面下方都显示成功提示

**涉及页面范围**: 同 2.1 节所有页面

### 2.4 配置持久化校验

**目标**: 确保 SQL 文件保存路径配置能够持久化存储,下次启动时不会恢复为默认值

**涉及模块**:

- 配置管理: config.py
- 视图处理: views/system_config.py
- 配置文件: config/app_config.json
- 启动流程: run_app.py、app.py

## 3. 校验标准定义

### 3.1 按钮样式标准

#### 3.1.1 生成 SQL 按钮标准样式

**HTML 结构**:

```
<button type="submit" class="submit-btn">生成 SQL</button>
```

**CSS 样式**:

```
.submit-btn {
  width: 100%;
  padding: 8px;
  background-color: #2563eb;
  border: none;
  color: white;
  border-radius: 6px;
  font-weight: 600;
  margin-top: 10px;
}
```

**视觉规范**:

- 按钮文本: "生成 SQL"(注意空格)
- 背景色: #2563eb(蓝色)
- 文字颜色: white
- 圆角: 6px
- 字重: 600
- 内边距: 8px
- 宽度: 100%

#### 3.1.2 清除按钮标准样式

**HTML 结构**:

```
<a href="?clear=1" class="clear-btn">清除</a>
```

**CSS 样式**:

```
.clear-btn {
  display: inline-block;
  width: 100%;
  padding: 8px;
  background-color: #dc3545;
  color: white;
  border-radius: 4px;
  font-weight: 600;
  text-align: center;
  margin-top: 10px;
  text-decoration: none;
}
```

**视觉规范**:

- 按钮文本: "清除"
- 背景色: #dc3545(红色)
- 文字颜色: white
- 圆角: 4px
- 字重: 600
- 内边距: 8px
- 宽度: 100%

#### 3.1.3 按钮布局标准

**容器结构**:

```
<div class="form-row" style="gap: 10px">
  <div class="form-col">
    <button type="submit" class="submit-btn">生成 SQL</button>
  </div>
  <div class="form-col">
    <a href="?clear=1" class="clear-btn">清除</a>
  </div>
</div>
```

**布局规范**:

- 两个按钮使用 flex 布局水平排列
- 按钮间距: 10px
- 每个按钮占据等宽列(.form-col 设置 flex: 1)

#### 3.1.4 特殊页面的按钮样式

部分页面(如 plan_date_form.html、contract_creator_form.html、order_executor_form.html)使用不同的按钮实现方式:

**HTML 结构**:

```
<div style="display: flex; gap: 10px">
  <button type="submit" class="submit-btn" style="flex: 1">生成SQL</button>
  <button type="button" class="submit-btn" style="flex: 1; background-color: #6c757d" onclick="clearForm()">清除</button>
</div>
```

**统一要求**:

- 这些页面需要统一为标准样式
- 清除按钮应改为使用链接形式: `<a href="?clear=1" class="clear-btn">清除</a>`
- 移除 JavaScript 的 clearForm()函数,改用 URL 参数方式清除

### 3.2 表单值保留行为标准

#### 3.2.1 基本原则

**值保留规则**:

- 点击"生成 SQL"按钮提交表单后,页面应重新加载并保留用户填写的所有输入值
- 清除按钮(通过?clear=1 参数)应清空所有表单字段
- 动态编号、操作备注、单条记录字段、批量导入文件选择等所有输入项均需保留

**实现机制**:

- 视图函数在处理 POST 请求后,需要重新渲染模板并传递表单实例
- 表单实例应包含用户提交的原始数据
- 模板中使用 form 字段自动渲染时会填充值

#### 3.2.2 当前实现分析

**标准实现页面**:

- contract_price_form.html、importance_form.html 等大部分页面已正确实现
- 这些页面的视图在 POST 处理后返回 render,并传递包含数据的 form 实例

**需要修复的实现**:
部分页面在成功生成 SQL 后可能未正确保留表单值,需要检查:

- 视图函数是否在 POST 后重新渲染表单并传递 form 实例
- 是否存在重定向导致表单数据丢失
- 清除功能是否通过 GET 参数?clear=1 正确实现

#### 3.2.3 清除功能实现标准

**视图层处理逻辑**:

```
视图函数应检测GET参数clear:
- 如果request.GET.get('clear') == '1',则实例化空表单
- 否则正常处理POST请求或显示带数据的表单
```

**模板层处理逻辑**:

```
清除按钮使用链接:
<a href="?clear=1" class="clear-btn">清除</a>
点击后刷新页面,视图检测到clear参数后返回空表单
```

### 3.3 成功提示标准

#### 3.3.1 提示组件标准结构

**HTML 结构**:

```
{% if saved_file %}
<div style="margin-top: 20px; padding: 15px; background: #d4edda; border-radius: 8px; border: 1px solid #c3e6cb">
  <strong style="color: #155724">✅ SQL文件已生成</strong>
  <div style="margin-top: 8px; color: #155724; font-size: 13px">保存位置: {{ saved_file }}</div>
</div>
{% endif %}
```

**视觉规范**:

- 背景色: #d4edda(绿色)
- 边框: 1px solid #c3e6cb
- 圆角: 8px
- 内边距: 15px
- 上边距: 20px
- 文字颜色: #155724(深绿色)
- 图标: ✅
- 文件路径字体大小: 13px

#### 3.3.2 视图返回数据要求

**视图函数返回值要求**:

- 视图函数在成功生成 SQL 文件后,必须在 render 的 context 中包含 saved_file 变量
- saved_file 应包含完整的文件路径字符串
- 如果使用 success_message 变量(如 plan_date_form.html),需同时提供

**特殊页面处理**:
部分页面使用 success_message 而非 saved_file:

```
{% if success_message %}
<div class="alert alert-success">{{ success_message|safe }}</div>
{% endif %}
```

**统一要求**:

- 统一使用 saved_file 变量
- 使用标准的成功提示组件结构
- 移除旧的 alert 样式提示

#### 3.3.3 缺失提示的页面识别方法

**校验步骤**:

1. 检查模板中是否存在 saved_file 或 success_message 条件判断
2. 检查视图函数是否在成功生成 SQL 后传递 saved_file 或 success_message 变量
3. 验证提示组件的样式是否符合标准

### 3.4 配置持久化标准

#### 3.4.1 配置文件结构要求

**配置文件路径**:

- 配置文件位置: config/app_config.json
- 配置文件必须在项目启动时自动创建 config 目录
- 配置文件必须使用 UTF-8 编码

**配置文件内容结构**:

```
{
  "MERGE_MAX_IN_SIZE": 500,
  "MERGE_MODULES": {
    "price": true,
    "item": true,
    ...
  },
  "SQL_OUTPUT_BASE_PATH": "用户配置的路径",
  "SQL_OUTPUT_MODE": "hierarchical",
  "SQL_OUTPUT_DATE_FORMAT": "%Y%m/%d",
  "TEMP_FILE_CLEANUP_ENABLED": true,
  "TEMP_FILE_RETENTION_HOURS": 24
}
```

**持久化字段要求**:

- SQL_OUTPUT_BASE_PATH: 必须持久化用户配置的路径
- SQL_OUTPUT_MODE: 路径组织模式(flat/hierarchical)
- SQL_OUTPUT_DATE_FORMAT: 日期格式
- 所有配置项在应用重启后必须保持不变

#### 3.4.2 配置加载机制要求

**配置加载流程**:

1. 应用启动时调用 get_config()函数
2. 检查 config/app_config.json 是否存在
3. 如果存在,读取 JSON 文件并与 DEFAULT 配置合并
4. 如果不存在,使用 DEFAULT 配置并创建文件
5. 路径类配置需要处理相对路径和绝对路径

**路径解析规则**:

- 如果 SQL_OUTPUT_BASE_PATH 是绝对路径,直接使用
- 如果是相对路径,基于运行时基础目录解析
- 运行时基础目录:
  - 源码运行: settings.BASE_DIR
  - 打包后运行: sys.executable 所在目录

#### 3.4.3 配置保存机制要求

**配置保存流程**:

1. 用户在页面提交配置
2. 视图函数调用 set_config()保存配置
3. 使用原子性写入(先写临时文件,后重命名)
4. 保存后验证配置是否正确写入
5. 记录日志

**原子性写入实现**:

- 先写入临时文件 app_config.json.tmp
- 写入成功后重命名为 app_config.json
- 如果失败,清理临时文件
- 确保不会因为写入失败导致配置损坏

#### 3.4.4 配置验证要求

**保存时验证**:

- 检查所有必需配置项是否存在
- 检查 MERGE_MODULES 是否包含所有模块
- 检查路径配置的有效性
- 如有缺失,自动补全 DEFAULT 值

**加载时验证**:

- 读取配置后验证 JSON 格式正确性
- 检查配置完整性
- 如有问题,记录警告日志并使用默认值

#### 3.4.5 默认值处理

**默认配置策略**:

- DEFAULT 配置定义在 config.py 中
- SQL_OUTPUT_BASE_PATH 默认值: ./temp_files/sql_output(相对路径)
- 首次运行时,如果用户未配置,使用默认路径
- 用户配置后,永久使用用户配置的路径

**配置合并策略**:

- 读取的配置与 DEFAULT 合并
- 用户配置的值覆盖 DEFAULT
- 缺失的配置项使用 DEFAULT 补全
- MERGE_MODULES 需要深度合并,确保所有模块都有配置

## 4. 校验清单

### 4.1 样式统一性校验清单

| 页面文件                      | 生成 SQL 按钮样式 | 清除按钮样式 | 按钮布局       | 状态   |
| ----------------------------- | ----------------- | ------------ | -------------- | ------ |
| contract_price_form.html      | .submit-btn       | .clear-btn   | 标准 flex 布局 | 待验证 |
| contract_item_form.html       | .submit-btn       | .clear-btn   | 标准 flex 布局 | 待验证 |
| contract_budget_form.html     | .submit-btn       | .clear-btn   | 标准 flex 布局 | 待验证 |
| end_date_form.html            | .submit-btn       | .clear-btn   | 标准 flex 布局 | 待验证 |
| use_list_update_form.html     | .submit-btn       | .clear-btn   | 标准 flex 布局 | 待验证 |
| contract_terminate.html       | .submit-btn       | .clear-btn   | 标准 flex 布局 | 待验证 |
| contract_creator_form.html    | .submit-btn       | button 清除  | flex 布局      | 需修复 |
| unit_change_form.html         | 未知              | 未知         | 未知           | 待验证 |
| gov_report_form.html          | 未知              | 未知         | 未知           | 待验证 |
| importance_form.html          | .submit-btn       | .clear-btn   | 标准 flex 布局 | 待验证 |
| floating_price_type_form.html | .submit-btn       | .clear-btn   | 标准 flex 布局 | 待验证 |
| erp_terminate_form.html       | 未知              | 未知         | 未知           | 待验证 |
| plan_date_form.html           | .submit-btn       | button 清除  | flex 布局      | 需修复 |
| order_executor_form.html      | .submit-btn       | button 清除  | flex 布局      | 需修复 |
| project_round.html            | .submit-btn       | .clear-btn   | 标准 flex 布局 | 待验证 |
| appr_state_change.html        | .submit-btn       | .clear-btn   | 标准 flex 布局 | 待验证 |
| sourcing_terminate.html       | .submit-btn       | .clear-btn   | 标准 flex 布局 | 待验证 |
| configurable_data.html        | .submit-btn       | .clear-btn   | 标准 flex 布局 | 待验证 |

**已识别需修复的页面**:

- contract_creator_form.html
- plan_date_form.html
- order_executor_form.html

**修复要求**:

- 清除按钮从 button 元素改为 a 链接
- 移除 onclick="clearForm()"
- 改用 href="?clear=1"
- 移除 JavaScript 的 clearForm 函数

### 4.2 表单值保留行为校验清单

| 页面文件                      | POST 后保留值 | 清除功能    | 视图实现 | 状态   |
| ----------------------------- | ------------- | ----------- | -------- | ------ |
| contract_price_form.html      | 支持          | ?clear=1    | 标准实现 | 待验证 |
| contract_item_form.html       | 支持          | ?clear=1    | 标准实现 | 待验证 |
| contract_budget_form.html     | 支持          | ?clear=1    | 标准实现 | 待验证 |
| end_date_form.html            | 支持          | ?clear=1    | 标准实现 | 待验证 |
| use_list_update_form.html     | 支持          | ?clear=1    | 标准实现 | 待验证 |
| contract_terminate.html       | 支持          | ?clear=1    | 标准实现 | 待验证 |
| contract_creator_form.html    | 支持          | clearForm() | 需修复   | 需修复 |
| importance_form.html          | 支持          | ?clear=1    | 标准实现 | 待验证 |
| floating_price_type_form.html | 支持          | ?clear=1    | 标准实现 | 待验证 |
| plan_date_form.html           | 支持          | clearForm() | 需修复   | 需修复 |
| order_executor_form.html      | 支持          | clearForm() | 需修复   | 需修复 |
| project_round.html            | 支持          | ?clear=1    | 标准实现 | 待验证 |
| appr_state_change.html        | 支持          | ?clear=1    | 标准实现 | 待验证 |
| sourcing_terminate.html       | 支持          | ?clear=1    | 标准实现 | 待验证 |
| configurable_data.html        | 支持          | ?clear=1    | 标准实现 | 待验证 |

**视图层修复要求**:

- contract_creator.py、plan_date.py、order_executor.py 视图需要添加 clear 参数检测
- 检测到 clear=1 时,返回空表单实例

### 4.3 成功提示完整性校验清单

| 页面文件                      | saved_file 提示 | success_message 提示 | 标准组件 | 状态   |
| ----------------------------- | --------------- | -------------------- | -------- | ------ |
| contract_price_form.html      | ✓               | -                    | ✓        | 待验证 |
| contract_item_form.html       | ✓               | -                    | ✓        | 待验证 |
| contract_budget_form.html     | ✓               | -                    | ✓        | 待验证 |
| end_date_form.html            | ✓               | -                    | ✓        | 待验证 |
| use_list_update_form.html     | ✓               | -                    | ✓        | 待验证 |
| contract_terminate.html       | ✓               | -                    | ✓        | 待验证 |
| contract_creator_form.html    | -               | ✓                    | -        | 需修复 |
| importance_form.html          | ✓               | -                    | ✓        | 待验证 |
| floating_price_type_form.html | ✓               | -                    | ✓        | 待验证 |
| plan_date_form.html           | -               | ✓                    | -        | 需修复 |
| order_executor_form.html      | -               | ✓                    | -        | 需修复 |
| project_round.html            | ✓               | -                    | ✓        | 待验证 |
| appr_state_change.html        | ✓               | -                    | ✓        | 待验证 |
| sourcing_terminate.html       | ✓               | -                    | ✓        | 待验证 |
| configurable_data.html        | ✓               | -                    | ✓        | 待验证 |

**修复要求**:

- 将 success_message 统一改为 saved_file
- 使用标准成功提示组件结构
- 移除 alert 样式的提示

### 4.4 配置持久化校验清单

| 检查项                        | 要求                   | 当前实现 | 状态   |
| ----------------------------- | ---------------------- | -------- | ------ |
| 配置文件路径                  | config/app_config.json | ✓        | 正常   |
| 配置文件编码                  | UTF-8                  | ✓        | 正常   |
| 目录自动创建                  | 启动时创建 config 目录 | ✓        | 正常   |
| SQL_OUTPUT_BASE_PATH 持久化   | 保存用户配置           | ✓        | 待验证 |
| SQL_OUTPUT_MODE 持久化        | 保存用户配置           | ✓        | 待验证 |
| SQL_OUTPUT_DATE_FORMAT 持久化 | 保存用户配置           | ✓        | 待验证 |
| 配置加载                      | 启动时读取             | ✓        | 待验证 |
| 配置合并                      | 与 DEFAULT 合并        | ✓        | 正常   |
| 路径解析                      | 相对/绝对路径处理      | ✓        | 正常   |
| 原子性写入                    | 临时文件+重命名        | ✓        | 正常   |
| 配置验证                      | 保存后验证             | ✓        | 正常   |
| 日志记录                      | 记录配置变更           | ✓        | 正常   |

**验证方法**:

1. 启动应用,检查 config/app_config.json 是否存在
2. 在文件路径配置页面修改 SQL_OUTPUT_BASE_PATH
3. 保存配置后,检查 app_config.json 文件内容
4. 重启应用,检查配置是否保留
5. 生成 SQL 文件,验证是否保存到配置的路径

## 5. 实施计划

### 5.1 第一阶段: 样式统一修复

**目标**: 修复所有页面的按钮样式不一致问题

**任务列表**:

1. 修复 contract_creator_form.html 清除按钮
2. 修复 plan_date_form.html 清除按钮
3. 修复 order_executor_form.html 清除按钮
4. 验证其他页面的按钮样式
5. 更新模板文档中的按钮规范

**预期结果**:

- 所有页面的生成 SQL 按钮使用统一的.submit-btn 样式
- 所有页面的清除按钮使用统一的.clear-btn 样式和?clear=1 参数
- 移除所有 JavaScript 的 clearForm 函数

### 5.2 第二阶段: 表单值保留修复

**目标**: 确保所有页面点击生成 SQL 后保留用户输入值

**任务列表**:

1. 修复 contract_creator.py 视图的清除逻辑
2. 修复 plan_date.py 视图的清除逻辑
3. 修复 order_executor.py 视图的清除逻辑
4. 验证其他视图的表单值保留行为
5. 测试清除功能是否正常工作

**预期结果**:

- 所有视图在 GET 请求带 clear=1 时返回空表单
- 所有视图在 POST 请求后保留表单数据
- 清除按钮点击后正确清空所有字段

### 5.3 第三阶段: 成功提示统一

**目标**: 统一所有页面的 SQL 生成成功提示样式

**任务列表**:

1. 修复 contract_creator_form.html 的提示组件
2. 修复 plan_date_form.html 的提示组件
3. 修复 order_executor_form.html 的提示组件
4. 修改对应视图函数,返回 saved_file 而非 success_message
5. 验证所有页面的成功提示显示

**预期结果**:

- 所有页面使用统一的成功提示组件结构
- 所有视图返回 saved_file 变量
- 成功提示的样式、颜色、布局完全一致

### 5.4 第四阶段: 配置持久化验证

**目标**: 验证配置持久化功能正常工作

**任务列表**:

1. 测试 SQL 文件路径配置的保存
2. 测试应用重启后配置是否保留
3. 测试路径模式配置的保存
4. 测试日期格式配置的保存
5. 验证 SQL 文件确实保存到配置的路径
6. 检查配置文件的完整性和格式

**预期结果**:

- 用户配置的 SQL 输出路径在重启后保持不变
- 路径模式和日期格式配置正确保存
- 配置文件格式正确,无损坏
- 日志正确记录配置变更

## 6. 验收标准

### 6.1 样式验收标准

**验收方法**:

- 打开每个功能页面,检查按钮样式
- 对比按钮的颜色、大小、圆角、文字
- 验证按钮布局是否水平对齐
- 检查按钮间距是否一致

**通过条件**:

- 所有生成 SQL 按钮背景色为#2563eb
- 所有清除按钮背景色为#dc3545
- 所有清除按钮为链接形式,使用?clear=1
- 按钮间距统一为 10px
- 按钮圆角、内边距、字重符合标准

### 6.2 功能验收标准

**验收方法**:

- 在每个页面填写表单数据
- 点击生成 SQL 按钮
- 检查页面是否保留所有输入值
- 点击清除按钮
- 检查页面是否清空所有字段

**通过条件**:

- 点击生成 SQL 后,动态编号保留
- 点击生成 SQL 后,操作备注保留
- 点击生成 SQL 后,所有单条记录字段保留
- 点击生成 SQL 后,批量导入文件名显示(如果选择了文件)
- 点击清除按钮后,所有字段清空

### 6.3 提示验收标准

**验收方法**:

- 在每个页面提交表单生成 SQL
- 等待 SQL 生成完成
- 检查页面下方是否显示成功提示
- 检查提示的样式和内容

**通过条件**:

- 成功提示显示在页面下方
- 提示背景色为#d4edda
- 提示包含"✅ SQL 文件已生成"文字
- 提示包含完整的文件保存路径
- 提示样式符合标准结构

### 6.4 持久化验收标准

**验收方法**:

1. 打开文件路径配置页面
2. 修改 SQL 输出路径为自定义路径
3. 保存配置
4. 检查 config/app_config.json 文件内容
5. 关闭应用
6. 重新启动应用
7. 打开文件路径配置页面
8. 检查路径是否保持为自定义路径
9. 生成 SQL 文件
10. 检查文件是否保存到自定义路径

**通过条件**:

- 保存配置后,app_config.json 文件更新
- 文件中 SQL_OUTPUT_BASE_PATH 为自定义路径
- 重启应用后,路径配置保持不变
- SQL 文件正确保存到配置的路径
- 配置文件格式正确,无错误

## 7. 风险评估

### 7.1 样式修复风险

**风险**: 修改按钮样式可能影响页面布局

**缓解措施**:

- 修改前备份原始模板文件
- 逐个页面修改和测试
- 使用浏览器开发者工具验证样式
- 在多个浏览器中测试

**影响范围**: 低 - 仅影响视觉效果,不影响功能

### 7.2 表单值保留修复风险

**风险**: 修改视图逻辑可能影响数据处理流程

**缓解措施**:

- 仔细 review 视图代码
- 测试 POST 请求的数据处理
- 测试清除功能是否正常
- 测试边界情况(空表单、部分填写等)

**影响范围**: 中 - 可能影响表单提交和数据保留

### 7.3 成功提示修复风险

**风险**: 修改变量名可能导致提示不显示

**缓解措施**:

- 同步修改模板和视图
- 测试 SQL 生成后提示显示
- 检查变量名拼写
- 测试文件路径是否正确传递

**影响范围**: 低 - 仅影响用户反馈,不影响 SQL 生成

### 7.4 配置持久化风险

**风险**: 配置文件损坏可能导致应用无法启动

**缓解措施**:

- 使用原子性写入
- 保存前验证配置格式
- 读取时处理异常
- 配置损坏时自动恢复默认值
- 记录详细日志

**影响范围**: 中 - 可能影响应用启动,但有容错机制

## 8. 测试计划

### 8.1 单元测试

**测试对象**: 配置管理模块

**测试用例**:

1. 测试 get_config()函数读取配置
2. 测试 set_config()函数保存配置
3. 测试配置验证函数
4. 测试路径解析函数
5. 测试配置合并逻辑

**期望结果**:

- 配置读取正确
- 配置保存成功
- 验证功能正常
- 路径解析准确
- 合并逻辑正确

### 8.2 集成测试

**测试对象**: 页面表单提交流程

**测试用例**:

1. 填写表单并提交
2. 检查 SQL 生成
3. 检查表单值保留
4. 点击清除按钮
5. 检查字段清空
6. 检查成功提示显示

**测试页面**:

- contract_price_form.html
- contract_creator_form.html
- plan_date_form.html
- order_executor_form.html
- importance_form.html

**期望结果**:

- SQL 正确生成
- 表单值正确保留
- 清除功能正常
- 提示正确显示

### 8.3 端到端测试

**测试场景**: 配置持久化完整流程

**测试步骤**:

1. 启动应用
2. 打开文件路径配置页面
3. 修改 SQL 输出路径
4. 保存配置
5. 打开某个 SQL 生成页面
6. 生成 SQL 文件
7. 检查文件位置
8. 关闭应用
9. 重新启动应用
10. 检查配置是否保留
11. 再次生成 SQL 文件
12. 检查文件位置

**期望结果**:

- 配置修改成功
- SQL 文件保存到正确路径
- 应用重启后配置保留
- 后续生成的文件仍保存到配置路径

## 9. 文档更新

### 9.1 需要更新的文档

**模板和公用组件设计文档**:

- 更新按钮组件规范
- 更新成功提示组件规范
- 更新表单值保留机制说明
- 添加清除功能实现规范

**README 文档**:

- 更新配置管理说明
- 更新 SQL 文件输出路径配置说明
- 添加配置持久化说明

### 9.2 文档更新要点

**按钮规范**:

- 明确生成 SQL 按钮和清除按钮的标准样式
- 说明清除按钮使用链接而非 button 元素
- 说明清除功能通过 URL 参数实现

**成功提示规范**:

- 明确成功提示组件的标准结构
- 说明使用 saved_file 变量而非 success_message
- 提供完整的代码示例

**配置持久化规范**:

- 说明配置文件的位置和格式
- 说明配置的加载和保存机制
- 说明路径配置的持久化保证
