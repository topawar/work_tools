"""组织机构API模块"""
import os
import io
import tempfile
import threading
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.conf import settings
from django.db.models import Q
from django.db import close_old_connections

from ..models import OrgDetail, ImportJob
from ..forms import OrgImportForm
from ..navigation import SIDEBAR_GROUPS

# 导入锁
IMPORT_LOCK = threading.Lock()
# 进度步长
PROGRESS_STEP = 100000


def org_import_view(request):
    """组织机构数据导入视图"""
    if request.method == 'POST':
        form = OrgImportForm(request.POST, request.FILES)
        if form.is_valid():
            f = form.cleaned_data['csv_file']
            temp_dir = os.path.join(settings.BASE_DIR, 'temp_uploads')
            os.makedirs(temp_dir, exist_ok=True)
            tmp = tempfile.NamedTemporaryFile(
                delete=False, dir=temp_dir, suffix='.csv')
            for chunk in f.chunks():
                tmp.write(chunk)
            tmp.close()
            job = ImportJob.objects.create(
                job_type='org', status='pending', filename=tmp.name)

            def worker(job_id):
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
                        required = {'company_code', 'company_name',
                                    'plate_code', 'plate_name'}
                        if not required.issubset(set([h.strip() for h in reader.fieldnames or []])):
                            raise ValueError(
                                'CSV列需包含：company_code, company_name, plate_code, plate_name')
                        done = 0
                        OrgDetail.objects.all().delete()
                        for row in reader:
                            cc = (row.get('company_code') or '').strip()
                            cn = (row.get('company_name') or '').strip()
                            pc = (row.get('plate_code') or '').strip()
                            pn = (row.get('plate_name') or '').strip()
                            if not any([cc, cn, pc, pn]):
                                continue
                            if cc:
                                OrgDetail.objects.update_or_create(company_code=cc, defaults={
                                                                   'company_name': cn, 'plate_code': pc, 'plate_name': pn})
                            else:
                                OrgDetail.objects.create(
                                    company_code=None, company_name=cn, plate_code=pc, plate_name=pn)
                            done += 1
                            if done % PROGRESS_STEP == 0:
                                j.done = done
                                j.save(update_fields=['done', 'updated_at'])
                        j.done = done
                        j.status = 'success'
                        j.message = f'共处理 {done} 行'
                        j.save(update_fields=[
                               'done', 'status', 'message', 'updated_at'])
                    except Exception as e:
                        j.status = 'failed'
                        j.error = str(e)
                        j.save(update_fields=['status', 'error', 'updated_at'])
            t = threading.Thread(target=worker, args=(job.id,), daemon=True)
            t.start()
            return redirect('job_detail', job_id=job.id)
        return render(request, 'org_import.html', {
            'form': form,
            'active_menu': 'org_import',
            'sidebar_groups': SIDEBAR_GROUPS,
        })
    else:
        form = OrgImportForm()
        return render(request, 'org_import.html', {
            'form': form,
            'active_menu': 'org_import',
            'sidebar_groups': SIDEBAR_GROUPS,
        })


def org_search_api(request):
    """组织机构搜索API"""
    q = request.GET.get('q', '').strip()
    if not q:
        return JsonResponse([], safe=False)
    qs = OrgDetail.objects.filter(
        Q(company_name__icontains=q) | Q(company_code__icontains=q))[:10]
    data = []
    for o in qs:
        label = f"{o.company_name}-{o.company_code}" if o.company_code else f"{o.company_name}"
        data.append({
            'label': label,
            'name': o.company_name,
            'code': o.company_code or '',
            'plate': o.plate_name or ''
        })
    return JsonResponse(data, safe=False)


__all__ = ['org_import_view', 'org_search_api']
