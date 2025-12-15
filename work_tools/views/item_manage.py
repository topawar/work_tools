"""物资数据管理模块"""
import os
import io
import tempfile
import threading
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.conf import settings
from django.db.models import Q
from django.db import close_old_connections

from ..models import ItemDetail, ImportJob
from ..forms import ItemImportForm
from ..navigation import get_sidebar_groups
from .base import normalize_item_id

# 导入锁
IMPORT_LOCK = threading.Lock()
# 进度步长
PROGRESS_STEP = 100000


def item_import_view(request):
    """物资数据导入视图"""
    if request.method == 'POST':
        form = ItemImportForm(request.POST, request.FILES)
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
                job_type='item', status='pending', filename=tmp.name)

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
                        required = {'item_id', 'item_name',
                                    'category', 'item_uom', 'purc_type'}
                        if not required.issubset(set(fieldnames_lower.keys())):
                            raise ValueError(
                                'CSV列需包含（忽略大小写）：item_id, item_name, category, item_uom, purc_type')
                        buffer = []
                        created = 0
                        updated = 0
                        done = 0
                        ItemDetail.objects.all().delete()
                        for row in reader:
                            # 使用忽略大小写的方式获取列值
                            def get_value(row, key):
                                """忽略大小写获取列值"""
                                original_key = fieldnames_lower.get(key.lower())
                                return (row.get(original_key) or '').strip() if original_key else ''
                            
                            rid = get_value(row, 'item_id')
                            if not rid:
                                continue
                            buffer.append({
                                'item_id': rid,
                                'item_name': get_value(row, 'item_name'),
                                'category': get_value(row, 'category'),
                                'item_uom': get_value(row, 'item_uom'),
                                'purc_type': get_value(row, 'purc_type'),
                            })
                            if len(buffer) >= batch_size:
                                ids = [b['item_id'] for b in buffer]
                                uniq = {}
                                for b in buffer:
                                    uniq[b['item_id']] = b
                                to_create = [ItemDetail(**v)
                                             for v in uniq.values()]
                                if to_create:
                                    with transaction.atomic():
                                        ItemDetail.objects.bulk_create(
                                            to_create)
                                    created += len(to_create)
                                done += len(buffer)
                                if done % PROGRESS_STEP == 0:
                                    j.done = done
                                    j.save(update_fields=[
                                           'done', 'updated_at'])
                                buffer = []
                        if buffer:
                            ids = [b['item_id'] for b in buffer]
                            uniq = {}
                            for b in buffer:
                                uniq[b['item_id']] = b
                            to_create = [ItemDetail(**v)
                                         for v in uniq.values()]
                            if to_create:
                                with transaction.atomic():
                                    ItemDetail.objects.bulk_create(to_create)
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
        return render(request, 'item_import.html', {
            'form': form,
            'active_menu': 'item_import',
            'sidebar_groups': get_sidebar_groups(),
        })
    else:
        form = ItemImportForm()
        return render(request, 'item_import.html', {
            'form': form,
            'active_menu': 'item_import',
            'sidebar_groups': get_sidebar_groups(),
        })


def item_search_api(request):
    """物资搜索API"""
    q = request.GET.get('q', '').strip()
    if not q:
        return JsonResponse([], safe=False)
    qs = ItemDetail.objects.filter(
        Q(item_id__icontains=q) | Q(item_name__icontains=q))[:10]
    data = []
    for o in qs:
        label = f"{o.item_id}-{o.item_name}"
        data.append({'label': label, 'id': o.item_id, 'name': o.item_name,
                    'uom': o.item_uom, 'category': o.category})
    return JsonResponse(data, safe=False)


def item_detail_api(request):
    """物资详情API"""
    iid = request.GET.get('id', '').strip()
    if not iid:
        return JsonResponse({'found': False})
    o = ItemDetail.objects.filter(item_id=normalize_item_id(iid)).first()
    if not o:
        return JsonResponse({'found': False})
    return JsonResponse({'found': True, 'id': o.item_id, 'name': o.item_name, 'uom': o.item_uom, 'category': o.category})


__all__ = ['item_import_view', 'item_search_api', 'item_detail_api']
