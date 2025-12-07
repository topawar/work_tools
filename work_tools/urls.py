"""
URL configuration for work_tools project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path
# 使用新的模块化views
from . import views as view

urlpatterns = [
    path("admin/", admin.site.urls),
    path('', view.unit_change_view, name='unit_change'),
    path('price/', view.contract_detail_price_view, name='contract_price'),
    path('price/template/', view.download_price_template,
         name='download_price_template'),
    path('unit/template/', view.download_unit_template,
         name='download_unit_template'),
    path('item/', view.contract_item_update_view, name='contract_item'),
    path('item/template/', view.download_item_template,
         name='download_item_template'),
    path('budget/', view.contract_budget_update_view, name='contract_budget'),
    path('budget/template/', view.download_budget_template,
         name='download_budget_template'),
    path('gov/', view.gov_report_view, name='gov_report'),
    path('gov/template/', view.download_gov_template,
         name='download_gov_template'),
    path('importance/', view.importance_update_view, name='importance'),
    path('importance/template/', view.download_importance_template,
         name='download_importance_template'),
    path('enddate/', view.enddate_update_view, name='enddate'),
    path('enddate/template/', view.download_enddate_template,
         name='download_enddate_template'),
    path('erp/terminate/', view.erp_terminate_view, name='erp_terminate'),
    path('erp/terminate/template/', view.download_erp_terminate_template,
         name='download_erp_terminate_template'),
    path('price-type/update/', view.floating_price_type_view,
         name='price_type_update'),
    path('price-type/template/', view.download_price_type_template,
         name='download_price_type_template'),
    path('download/<str:filename>/', view.download_sql, name='download_sql'),
    path('org/import/', view.org_import_view, name='org_import'),
    path('org/search/', view.org_search_api, name='org_search'),
    path('item/search/', view.item_search_api, name='item_search'),
    path('item/by-id/', view.item_detail_api, name='item_by_id'),
    path('item/import/', view.item_import_view, name='item_import'),
    path('use-list/update/', view.use_list_update_view, name='use_list_update'),
    path('use-list/template/', view.download_use_list_template,
         name='download_use_list_template'),
    path('jobs/', view.job_list_view, name='job_list'),
    path('jobs/<int:job_id>/', view.job_detail_view, name='job_detail'),
    path('jobs/<int:job_id>/status/', view.job_status_api, name='job_status'),
    path('jobs/<int:job_id>/delete/', view.job_delete_view, name='job_delete'),
    path('jobs/<int:job_id>/fail/', view.job_fail_view, name='job_fail'),
    path('system/config/', view.system_config_view, name='system_config'),
    path('system/file-path/', view.file_path_config_view, name='file_path_config'),
    path('system/cleanup/', view.cleanup_config_view, name='cleanup_config'),
    path('system/select-folder/', view.select_folder_api, name='select_folder'),
    path('system/cleanup-now/', view.cleanup_now_view, name='cleanup_now'),
    path('appr-state/change/', view.appr_state_change_view,
         name='appr_state_change'),
    path('appr-state/template/', view.download_appr_state_template,
         name='download_appr_state_template'),
    path('contract/terminate/', view.contract_terminate_view,
         name='contract_terminate'),
    path('contract/terminate/template/', view.download_terminate_template,
         name='download_terminate_template'),
    path('sourcing/terminate/', view.sourcing_terminate_view,
         name='sourcing_terminate'),
    path('sourcing/terminate/template/', view.download_sourcing_terminate_template,
         name='download_sourcing_terminate_template'),
    path('project/round/', view.project_round_view,
         name='project_round'),
    path('project/round/template/', view.download_project_round_template,
         name='download_project_round_template'),
    
    # 校验失败文件下载
    path('download_validation_failure/', view.download_validation_failure_view,
         name='download_validation_failure'),
    
    # 下拉框配置管理
    path('dropdown-config/', view.dropdown_config_view, name='dropdown_config'),
    path('dropdown-config/group/add/', view.dropdown_group_add, name='dropdown_group_add'),
    path('dropdown-config/group/edit/', view.dropdown_group_edit, name='dropdown_group_edit'),
    path('dropdown-config/group/toggle/', view.dropdown_group_toggle, name='dropdown_group_toggle'),
    path('dropdown-config/item/add/', view.dropdown_item_add, name='dropdown_item_add'),
    path('dropdown-config/item/edit/', view.dropdown_item_edit, name='dropdown_item_edit'),
    path('dropdown-config/item/delete/', view.dropdown_item_delete, name='dropdown_item_delete'),
    path('dropdown-config/item/toggle/', view.dropdown_item_toggle, name='dropdown_item_toggle'),
]
