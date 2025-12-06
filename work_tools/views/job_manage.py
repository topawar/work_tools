"""任务管理模块"""
import os
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.utils import timezone

from ..models import ImportJob
from ..navigation import SIDEBAR_GROUPS


def job_list_view(request):
    """任务列表视图"""
    jobs = ImportJob.objects.order_by('-id')[:100]
    return render(request, 'jobs.html', {
        'jobs': jobs,
        'active_menu': 'job_list',
        'sidebar_groups': SIDEBAR_GROUPS,
    })


def job_detail_view(request, job_id):
    """任务详情视图"""
    job = ImportJob.objects.get(id=job_id)
    return render(request, 'job_detail.html', {
        'job': job,
        'active_menu': 'job_list',
        'sidebar_groups': SIDEBAR_GROUPS,
    })


def job_status_api(request, job_id):
    """任务状态API"""
    job = ImportJob.objects.get(id=job_id)
    if job.status == 'running':
        if (timezone.now() - job.updated_at).total_seconds() > 900:
            job.status = 'failed'
            job.error = 'timeout'
            job.save(update_fields=['status', 'error', 'updated_at'])
    return JsonResponse({
        'id': job.id,
        'type': job.job_type,
        'status': job.status,
        'total': job.total,
        'done': job.done,
        'message': job.message,
        'error': job.error,
        'updated_at': job.updated_at.isoformat(),
    })


def job_delete_view(request, job_id):
    """删除任务"""
    job = ImportJob.objects.get(id=job_id)
    if request.method != 'POST':
        return redirect('job_detail', job_id=job_id)
    if job.status == 'running':
        return redirect('job_detail', job_id=job_id)
    try:
        if job.filename and os.path.exists(job.filename):
            os.remove(job.filename)
    except Exception:
        pass
    job.delete()
    return redirect('job_list')


def job_fail_view(request, job_id):
    """标记任务失败"""
    job = ImportJob.objects.get(id=job_id)
    if request.method != 'POST':
        return redirect('job_detail', job_id=job_id)
    if job.status == 'running':
        job.status = 'failed'
        job.error = 'manually failed'
        job.save(update_fields=['status', 'error', 'updated_at'])
    return redirect('job_detail', job_id=job_id)


__all__ = [
    'job_list_view',
    'job_detail_view',
    'job_status_api',
    'job_delete_view',
    'job_fail_view',
]
