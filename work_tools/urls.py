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
from . import view

urlpatterns = [
    path("admin/", admin.site.urls),
    path('', view.unit_change_view, name='unit_change'),
    path('price/', view.contract_detail_price_view, name='contract_price'),
    path('price/template/', view.download_price_template, name='download_price_template'),
    path('unit/template/', view.download_unit_template, name='download_unit_template'),
    path('item/', view.contract_item_update_view, name='contract_item'),
    path('item/template/', view.download_item_template, name='download_item_template'),
    path('budget/', view.contract_budget_update_view, name='contract_budget'),
    path('budget/template/', view.download_budget_template, name='download_budget_template'),
    path('gov/', view.gov_report_view, name='gov_report'),
    path('gov/template/', view.download_gov_template, name='download_gov_template'),
    path('importance/', view.importance_update_view, name='importance'),
    path('importance/template/', view.download_importance_template, name='download_importance_template'),
    path('enddate/', view.enddate_update_view, name='enddate'),
    path('enddate/template/', view.download_enddate_template, name='download_enddate_template'),
    path('erp/terminate/', view.erp_terminate_view, name='erp_terminate'),
    path('erp/terminate/template/', view.download_erp_terminate_template, name='download_erp_terminate_template'),
    path('price-type/update/', view.floating_price_type_view, name='price_type_update'),
    path('price-type/template/', view.download_price_type_template, name='download_price_type_template'),
    path('download/<str:filename>/', view.download_sql, name='download_sql'),
    path('org/import/', view.org_import_view, name='org_import'),
    path('org/search/', view.org_search_api, name='org_search'),
    path('item/search/', view.item_search_api, name='item_search'),
    path('item/by-id/', view.item_detail_api, name='item_by_id'),
    path('item/import/', view.item_import_view, name='item_import'),
    path('jobs/', view.job_list_view, name='job_list'),
    path('jobs/<int:job_id>/', view.job_detail_view, name='job_detail'),
    path('jobs/<int:job_id>/status/', view.job_status_api, name='job_status'),
    path('jobs/<int:job_id>/delete/', view.job_delete_view, name='job_delete'),
    path('jobs/<int:job_id>/fail/', view.job_fail_view, name='job_fail'),
    path('system/config/', view.system_config_view, name='system_config'),
]
