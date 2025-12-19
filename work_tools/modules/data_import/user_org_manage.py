"""用户组织机构数据管理模块"""
import os
import io
import tempfile
import threading
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.conf import settings
from django.db.models import Q
from django.db import close_old_connections

from work_tools.models import UserOrgDetail, ImportJob
from work_tools.forms import UserOrgImportForm
from work_tools.navigation import get_sidebar_groups

# 导入锁
IMPORT_LOCK = threading.Lock()
# 进度步长
PROGRESS_STEP = 100000


def user_org_import_view(request):
    """用户组织机构数据导入视图"""
    if request.method == 'POST':
        form = UserOrgImportForm(request.POST, request.FILES)
        if form.is_valid():
            f = form.cleaned_data['csv_file']
            batch_size = form.cleaned_data.get('batch_size') or 5000
            temp_dir = os.path.join(settings.BASE_DIR, 'temp_uploads')
            os.makedirs(temp_dir, exist_ok=True)
            tmp = tempfile.NamedTemporaryFile(
                delete=False, dir=temp_dir, suffix='.csv')
            tmp.write(f.read())
            tmp.close()
            job = ImportJob.objects.create(
                job_type='user_org', status='pending', filename=tmp.name)

            def worker(job_id, batch_size):
                close_old_connections()
                with IMPORT_LOCK:
                    from django.db import transaction
                    j = ImportJob.objects.get(id=job_id)
                    j.status = 'running'
                    j.save(update_fields=['status', 'updated_at'])
                    try:
                        total = 0
                        with open(j.filename, 'rb') as rf:
                            for _ in rf:
                                total += 1
                        total = max(0, total-1)
                        j.total = total
                        j.done = 0
                        j.save(update_fields=['total', 'done', 'updated_at'])
                        with open(j.filename, 'rb') as rf:
                            text = rf.read().decode('utf-8-sig')
                        import csv
                        reader = csv.DictReader(io.StringIO(text))
                        # 将列名转换为小写以忽略大小写
                        fieldnames_lower = {h.strip().lower(): h.strip() for h in reader.fieldnames or []}
                        required = {'login_name', 'user_name', 'dept_code',
                                    'dept_name', 'company_code', 'company_name',
                                    'plate_code', 'plate_name'}
                        if not required.issubset(set(fieldnames_lower.keys())):
                            raise ValueError(
                                'CSV列需包含（忽略大小写）：login_name, user_name, dept_code, dept_name, company_code, company_name, plate_code, plate_name')
                        buffer = []
                        created = 0
                        updated = 0
                        done = 0
                        UserOrgDetail.objects.all().delete()
                        for row in reader:
                            # 使用忽略大小写的方式获取列值
                            def get_value(row, key):
                                """忽略大小写获取列值"""
                                original_key = fieldnames_lower.get(key.lower())
                                return (row.get(original_key) or '').strip() if original_key else ''
                            
                            login_name = get_value(row, 'login_name')
                            if not login_name:
                                continue
                            buffer.append({
                                'login_name': login_name,
                                'user_name': get_value(row, 'user_name'),
                                'dept_code': get_value(row, 'dept_code'),
                                'dept_name': get_value(row, 'dept_name'),
                                'company_code': get_value(row, 'company_code'),
                                'company_name': get_value(row, 'company_name'),
                                'plate_code': get_value(row, 'plate_code'),
                                'plate_name': get_value(row, 'plate_name'),
                            })
                            if len(buffer) >= batch_size:
                                # 直接创建所有记录，不去重
                                to_create = [UserOrgDetail(**b) for b in buffer]
                                if to_create:
                                    with transaction.atomic():
                                        UserOrgDetail.objects.bulk_create(
                                            to_create)
                                    created += len(to_create)
                                done += len(buffer)
                                if done % PROGRESS_STEP == 0:
                                    j.done = done
                                    j.save(update_fields=[
                                           'done', 'updated_at'])
                                buffer = []
                        if buffer:
                            # 直接创建所有记录，不去重
                            to_create = [UserOrgDetail(**b) for b in buffer]
                            if to_create:
                                with transaction.atomic():
                                    UserOrgDetail.objects.bulk_create(to_create)
                                created += len(to_create)
                            done += len(buffer)
                            j.done = done
                            j.save(update_fields=['done', 'updated_at'])
                        j.status = 'success'
                        j.message = f'新建 {created} 条，更新 {updated} 条'
                        j.save(update_fields=[
                               'status', 'message', 'updated_at'])
                    except Exception as e:
                        j.status = 'failed'
                        j.error = str(e)
                        j.save(update_fields=['status', 'error', 'updated_at'])
            t = threading.Thread(target=worker, args=(
                job.id, batch_size), daemon=True)
            t.start()
            return redirect('job_detail', job_id=job.id)
        return render(request, 'modules/data_import/user_org_import.html', {
            'form': form,
            'active_menu': 'user_org_import',
            'sidebar_groups': get_sidebar_groups(),
        })
    else:
        form = UserOrgImportForm()
        return render(request, 'modules/data_import/user_org_import.html', {
            'form': form,
            'active_menu': 'user_org_import',
            'sidebar_groups': get_sidebar_groups(),
        })


__all__ = ['user_org_import_view']
