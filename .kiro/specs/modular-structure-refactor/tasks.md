# 模块化结构重构任务列表

- [x] 1. 准备工作


  - 创建所有模块目录结构
  - 创建模块的 __init__.py 文件
  - 创建模板目录结构
  - _需求: 2.1, 2.2_



- [ ] 1.1 创建 contract 模块目录结构
  - 创建 `work_tools/modules/contract/` 目录
  - 创建 `work_tools/modules/contract/__init__.py`
  - 创建 `work_tools/templates/modules/contract/` 目录


  - _需求: 2.1_

- [ ] 1.2 创建 procurement 模块目录结构
  - 创建 `work_tools/modules/procurement/` 目录

  - 创建 `work_tools/modules/procurement/__init__.py`
  - 创建 `work_tools/templates/modules/procurement/` 目录
  - _需求: 2.1_

- [x] 1.3 创建 data_import 模块目录结构

  - 创建 `work_tools/modules/data_import/` 目录
  - 创建 `work_tools/modules/data_import/__init__.py`
  - 创建 `work_tools/templates/modules/data_import/` 目录
  - _需求: 2.1_


- [ ] 1.4 创建 job_management 模块目录结构
  - 创建 `work_tools/modules/job_management/` 目录
  - 创建 `work_tools/modules/job_management/__init__.py`
  - 创建 `work_tools/templates/modules/job_management/` 目录



  - _需求: 2.1_

- [ ] 1.5 创建 configurable 模块目录结构
  - 创建 `work_tools/modules/configurable/` 目录
  - 创建 `work_tools/modules/configurable/__init__.py`
  - 创建 `work_tools/templates/modules/configurable/` 目录


  - _需求: 2.1_

- [ ] 2. 迁移 contract 模块
  - 移动视图文件到模块目录


  - 移动模板文件到模块模板目录
  - 更新模板路径引用
  - 更新导入语句
  - _需求: 3.1, 4.1, 6.1_



- [ ] 2.1 移动 contract_price 视图和模板
  - 移动 `work_tools/views/contract_price.py` 到 `work_tools/modules/contract/`
  - 移动 `work_tools/templates/contract_price_form.html` 到 `work_tools/templates/modules/contract/`

  - 更新视图中的模板路径为 `modules/contract/contract_price_form.html`
  - _需求: 3.1, 6.1_

- [ ] 2.2 移动 contract_item 视图和模板
  - 移动 `work_tools/views/contract_item.py` 到 `work_tools/modules/contract/`

  - 移动 `work_tools/templates/contract_item_form.html` 到 `work_tools/templates/modules/contract/`
  - 更新视图中的模板路径为 `modules/contract/contract_item_form.html`
  - _需求: 3.1, 6.1_

- [x] 2.3 移动 contract_budget 视图和模板

  - 移动 `work_tools/views/contract_budget.py` 到 `work_tools/modules/contract/`
  - 移动 `work_tools/templates/contract_budget_form.html` 到 `work_tools/templates/modules/contract/`
  - 更新视图中的模板路径为 `modules/contract/contract_budget_form.html`
  - _需求: 3.1, 6.1_


- [ ] 2.4 移动 enddate 视图和模板
  - 移动 `work_tools/views/enddate.py` 到 `work_tools/modules/contract/`
  - 移动 `work_tools/templates/end_date_form.html` 到 `work_tools/templates/modules/contract/`
  - 更新视图中的模板路径为 `modules/contract/end_date_form.html`
  - _需求: 3.1, 6.1_


- [ ] 2.5 移动 use_list 视图和模板
  - 移动 `work_tools/views/use_list.py` 到 `work_tools/modules/contract/`
  - 移动 `work_tools/templates/use_list_update_form.html` 到 `work_tools/templates/modules/contract/`
  - 更新视图中的模板路径为 `modules/contract/use_list_update_form.html`

  - _需求: 3.1, 6.1_

- [ ] 2.6 移动 appr_state 视图和模板
  - 移动 `work_tools/views/appr_state.py` 到 `work_tools/modules/contract/`
  - 移动 `work_tools/templates/appr_state_change.html` 到 `work_tools/templates/modules/contract/`


  - 更新视图中的模板路径为 `modules/contract/appr_state_change.html`
  - _需求: 3.1, 6.1_



- [x] 2.7 移动 contract_creator 视图和模板


  - 移动 `work_tools/views/contract_creator.py` 到 `work_tools/modules/contract/`
  - 移动 `work_tools/templates/contract_creator_form.html` 到 `work_tools/templates/modules/contract/`
  - 更新视图中的模板路径为 `modules/contract/contract_creator_form.html`
  - _需求: 3.1, 6.1_

- [x] 2.8 移动 contract_terminate 视图和模板

  - 移动 `work_tools/views/contract_terminate.py` 到 `work_tools/modules/contract/`
  - 移动 `work_tools/templates/contract_terminate.html` 到 `work_tools/templates/modules/contract/`
  - 更新视图中的模板路径为 `modules/contract/contract_terminate.html`
  - _需求: 3.1, 6.1_


- [ ] 2.9 移动 sourcing_terminate 视图和模板
  - 移动 `work_tools/views/sourcing_terminate.py` 到 `work_tools/modules/contract/`
  - 移动 `work_tools/templates/sourcing_terminate.html` 到 `work_tools/templates/modules/contract/`
  - 更新视图中的模板路径为 `modules/contract/sourcing_terminate.html`
  - _需求: 3.1, 6.1_


- [ ] 2.10 更新 contract 模块的 __init__.py
  - 在 `work_tools/modules/contract/__init__.py` 中导入所有视图函数
  - 使用 `from .contract_price import *` 等语句
  - _需求: 4.1_


- [ ] 2.11 更新 work_tools/views/__init__.py 中的 contract 导入
  - 将 contract 相关的导入改为从 `work_tools.modules.contract` 导入
  - 保持 __all__ 列表不变
  - _需求: 4.1, 10.2_


- [ ] 3. 迁移 procurement 模块
  - 移动视图文件到模块目录
  - 移动模板文件到模块模板目录
  - 更新模板路径引用

  - 更新导入语句
  - _需求: 3.1, 4.1, 6.1_

- [ ] 3.1 移动 contract_unit 视图和模板
  - 移动 `work_tools/views/contract_unit.py` 到 `work_tools/modules/procurement/`

  - 移动 `work_tools/templates/unit_change_form.html` 到 `work_tools/templates/modules/procurement/`
  - 更新视图中的模板路径为 `modules/procurement/unit_change_form.html`
  - _需求: 3.1, 6.1_

- [x] 3.2 移动 gov_report 视图和模板

  - 移动 `work_tools/views/gov_report.py` 到 `work_tools/modules/procurement/`
  - 移动 `work_tools/templates/gov_report_form.html` 到 `work_tools/templates/modules/procurement/`
  - 更新视图中的模板路径为 `modules/procurement/gov_report_form.html`
  - _需求: 3.1, 6.1_


- [ ] 3.3 移动 importance 视图和模板
  - 移动 `work_tools/views/importance.py` 到 `work_tools/modules/procurement/`
  - 移动 `work_tools/templates/importance_form.html` 到 `work_tools/templates/modules/procurement/`

  - 更新视图中的模板路径为 `modules/procurement/importance_form.html`
  - _需求: 3.1, 6.1_


- [ ] 3.4 移动 price_type 视图和模板
  - 移动 `work_tools/views/price_type.py` 到 `work_tools/modules/procurement/`
  - 移动 `work_tools/templates/floating_price_type_form.html` 到 `work_tools/templates/modules/procurement/`
  - 更新视图中的模板路径为 `modules/procurement/floating_price_type_form.html`
  - _需求: 3.1, 6.1_


- [ ] 3.5 移动 erp_terminate 视图和模板
  - 移动 `work_tools/views/erp_terminate.py` 到 `work_tools/modules/procurement/`
  - 移动 `work_tools/templates/erp_terminate_form.html` 到 `work_tools/templates/modules/procurement/`
  - 更新视图中的模板路径为 `modules/procurement/erp_terminate_form.html`

  - _需求: 3.1, 6.1_

- [ ] 3.6 移动 project_round 视图和模板
  - 移动 `work_tools/views/project_round.py` 到 `work_tools/modules/procurement/`
  - 移动 `work_tools/templates/project_round.html` 到 `work_tools/templates/modules/procurement/`
  - 更新视图中的模板路径为 `modules/procurement/project_round.html`
  - _需求: 3.1, 6.1_

- [ ] 3.7 移动 plan_date 视图和模板
  - 移动 `work_tools/views/plan_date.py` 到 `work_tools/modules/procurement/`
  - 移动 `work_tools/templates/plan_date_form.html` 到 `work_tools/templates/modules/procurement/`
  - 更新视图中的模板路径为 `modules/procurement/plan_date_form.html`
  - _需求: 3.1, 6.1_

- [ ] 3.8 移动 order_executor 视图和模板
  - 移动 `work_tools/views/order_executor.py` 到 `work_tools/modules/procurement/`
  - 移动 `work_tools/templates/order_executor_form.html` 到 `work_tools/templates/modules/procurement/`
  - 更新视图中的模板路径为 `modules/procurement/order_executor_form.html`
  - _需求: 3.1, 6.1_

- [ ] 3.9 更新 procurement 模块的 __init__.py
  - 在 `work_tools/modules/procurement/__init__.py` 中导入所有视图函数
  - _需求: 4.1_

- [ ] 3.10 更新 work_tools/views/__init__.py 中的 procurement 导入
  - 将 procurement 相关的导入改为从 `work_tools.modules.procurement` 导入
  - _需求: 4.1, 10.2_

- [ ] 4. 迁移 data_import 模块
  - 移动视图文件到模块目录
  - 移动模板文件到模块模板目录
  - 更新模板路径引用
  - 更新导入语句
  - _需求: 3.1, 4.1, 6.1_

- [ ] 4.1 移动 org_api 视图和模板
  - 移动 `work_tools/views/org_api.py` 到 `work_tools/modules/data_import/`
  - 移动 `work_tools/templates/org_import.html` 到 `work_tools/templates/modules/data_import/`
  - 更新视图中的模板路径为 `modules/data_import/org_import.html`
  - _需求: 3.1, 6.1_

- [ ] 4.2 移动 user_org_manage 视图和模板
  - 移动 `work_tools/views/user_org_manage.py` 到 `work_tools/modules/data_import/`
  - 移动 `work_tools/templates/user_org_import.html` 到 `work_tools/templates/modules/data_import/`
  - 更新视图中的模板路径为 `modules/data_import/user_org_import.html`
  - _需求: 3.1, 6.1_

- [x] 4.3 移动 item_manage 视图和模板

  - 移动 `work_tools/views/item_manage.py` 到 `work_tools/modules/data_import/`
  - 移动 `work_tools/templates/item_import.html` 到 `work_tools/templates/modules/data_import/`
  - 更新视图中的模板路径为 `modules/data_import/item_import.html`
  - _需求: 3.1, 6.1_

- [x] 4.4 更新 data_import 模块的 __init__.py

  - 在 `work_tools/modules/data_import/__init__.py` 中导入所有视图函数
  - _需求: 4.1_

- [x] 4.5 更新 work_tools/views/__init__.py 中的 data_import 导入


  - 将 data_import 相关的导入改为从 `work_tools.modules.data_import` 导入
  - _需求: 4.1, 10.2_

- [ ] 5. 迁移 job_management 模块
  - 移动视图文件到模块目录
  - 移动模板文件到模块模板目录
  - 更新模板路径引用
  - 更新导入语句
  - _需求: 3.1, 4.1, 6.1_

- [ ] 5.1 移动 job_manage 视图和模板
  - 移动 `work_tools/views/job_manage.py` 到 `work_tools/modules/job_management/`
  - 移动 `work_tools/templates/jobs.html` 到 `work_tools/templates/modules/job_management/`
  - 移动 `work_tools/templates/job_detail.html` 到 `work_tools/templates/modules/job_management/`
  - 更新视图中的模板路径为 `modules/job_management/jobs.html` 和 `modules/job_management/job_detail.html`
  - _需求: 3.1, 6.1_

- [ ] 5.2 更新 job_management 模块的 __init__.py
  - 在 `work_tools/modules/job_management/__init__.py` 中导入所有视图函数
  - _需求: 4.1_

- [ ] 5.3 更新 work_tools/views/__init__.py 中的 job_management 导入
  - 将 job_management 相关的导入改为从 `work_tools.modules.job_management` 导入
  - _需求: 4.1, 10.2_

- [ ] 6. 完善 system_config 模块
  - 移动剩余的配置管理视图到模块目录
  - 移动剩余的模板文件到模块模板目录
  - 更新模板路径引用
  - 更新导入语句
  - _需求: 3.1, 4.1, 6.1_

- [ ] 6.1 移动 dropdown_config 视图和模板
  - 移动 `work_tools/views/dropdown_config.py` 到 `work_tools/modules/system_config/`
  - 移动 `work_tools/templates/dropdown_config.html` 到 `work_tools/templates/modules/system_config/`
  - 更新视图中的模板路径为 `modules/system_config/dropdown_config.html`
  - _需求: 3.1, 6.1_

- [ ] 6.2 移动 configurable_config 视图和模板
  - 移动 `work_tools/views/configurable_config.py` 到 `work_tools/modules/system_config/`
  - 移动 `work_tools/templates/configurable_config.html` 到 `work_tools/templates/modules/system_config/`
  - 更新视图中的模板路径为 `modules/system_config/configurable_config.html`
  - _需求: 3.1, 6.1_

- [ ] 6.3 移动 database_config 视图和模板
  - 移动 `work_tools/views/database_config.py` 到 `work_tools/modules/system_config/`
  - 移动 `work_tools/templates/database_config.html` 到 `work_tools/templates/modules/system_config/`
  - 更新视图中的模板路径为 `modules/system_config/database_config.html`
  - _需求: 3.1, 6.1_

- [ ] 6.4 更新 system_config 模块的 __init__.py
  - 在 `work_tools/modules/system_config/__init__.py` 中添加新迁移视图的导入
  - _需求: 4.1_

- [ ] 6.5 更新 work_tools/views/__init__.py 中的 system_config 导入
  - 确保所有 system_config 相关的导入都从 `work_tools.modules.system_config` 导入
  - _需求: 4.1, 10.2_

- [ ] 7. 迁移 configurable 模块
  - 移动视图文件到模块目录
  - 移动模板文件到模块模板目录
  - 更新模板路径引用
  - 更新导入语句
  - _需求: 3.1, 4.1, 6.1_

- [ ] 7.1 移动 configurable_data 视图和模板
  - 移动 `work_tools/views/configurable_data.py` 到 `work_tools/modules/configurable/`
  - 移动 `work_tools/templates/configurable_data.html` 到 `work_tools/templates/modules/configurable/`
  - 更新视图中的模板路径为 `modules/configurable/configurable_data.html`
  - _需求: 3.1, 6.1_

- [ ] 7.2 更新 configurable 模块的 __init__.py
  - 在 `work_tools/modules/configurable/__init__.py` 中导入所有视图函数
  - _需求: 4.1_

- [ ] 7.3 更新 work_tools/views/__init__.py 中的 configurable 导入
  - 将 configurable 相关的导入改为从 `work_tools.modules.configurable` 导入
  - _需求: 4.1, 10.2_

- [ ] 8. 清理和验证
  - 删除旧的视图文件
  - 删除旧的模板文件
  - 运行测试验证功能
  - _需求: 8.1, 8.2, 8.3_

- [ ] 8.1 删除 work_tools/views/ 中已迁移的视图文件
  - 保留 `base.py` 和 `__init__.py`
  - 删除所有已迁移到模块的视图文件
  - _需求: 3.2_

- [ ] 8.2 删除 work_tools/templates/ 中已迁移的模板文件
  - 保留共享模板（base_config.html, sidebar.html, success.html, errors/, tags/）
  - 删除所有已迁移到模块的模板文件
  - _需求: 3.2_

- [ ] 8.3 运行现有测试套件
  - 运行所有单元测试
  - 确保所有测试通过
  - _需求: 8.1_

- [ ] 8.4 手动测试每个导航菜单项
  - 测试合同模块的所有页面
  - 测试计划-寻源模块的所有页面
  - 测试数据导入模块的所有页面
  - 测试任务管理模块的所有页面
  - 测试系统配置模块的所有页面
  - 测试特殊模板的动态页面
  - _需求: 8.2_

- [ ] 8.5 验证打包功能
  - 运行 collectstatic 命令
  - 确保所有静态资源被正确收集
  - 测试打包后的应用能否正常运行
  - _需求: 7.3, 8.4_


