import re
import os
import tempfile
import io
from datetime import datetime
from django.shortcuts import render, redirect
from django.http import FileResponse, HttpResponse, JsonResponse
from django.conf import settings
from .forms import UnitChangeForm, ContractDetailPriceForm, ContractItemUpdateForm, ContractBudgetUpdateForm, ErpTerminateForm, FloatingPriceTypeForm
from .forms import GovReportForm, ImportanceForm, EndDateUpdateForm
from .forms import OrgImportForm, ItemImportForm
from .navigation import SIDEBAR_GROUPS
from .config import get_config, set_config
from .sql_merge import chunk_list, format_in, merge_by_key, compose_or
from .models import OrgDetail, ItemDetail
from django.db.models import Q
import threading
from django.db import close_old_connections
from django.utils import timezone
import logging
import json
from .logger_utils import (
    log_form_data, log_records_processed, log_name_to_code_conversion,
    log_sql_generation, log_file_saved, log_view_input
)

# 创建日志记录器
logger = logging.getLogger('work_tools.view')
sql_logger = logging.getLogger('work_tools.sql')
try:
    import openpyxl
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False


PROGRESS_STEP = 100000


def parse_ops_remark(remark):
    if not isinstance(remark, str):
        return ''
    remark = remark.strip()
    if not remark:
        return ''
    m = re.search(r'#(\d+)\s+(.+?)(?:\s+`?https?://\S+`?)', remark)
    if m:
        desc = m.group(2).replace('`', '').strip()
        return f"{m.group(1)} {desc}".strip()
    ones_m = re.search(
        r'https://ones\.cnsc-sh\.com/project/#/team/[^/]+/task/([^\s`]+)', remark)
    if ones_m:
        tid = ones_m.group(1)
        num_m = re.search(r'\d+', tid)
        num = num_m.group() if num_m else tid
        desc = remark.replace(ones_m.group(0), '').replace('`', '').strip()
        return f"{num} {desc}".strip()
    return remark


def extract_company_code(value):
    if not isinstance(value, str):
        return None
    s = value.strip()
    m = re.match(r"^(.*?)-(\w+)$", s)
    if m:
        return m.group(2)
    return None


def extract_company_name(value):
    if not isinstance(value, str):
        return None
    s = value.strip()
    m = re.match(r"^(.*?)-(\w+)$", s)
    if m:
        return m.group(1)
    return s


def _unique_code_by_name(name: str):
    qs = OrgDetail.objects.filter(company_name__iexact=str(name).strip())
    if qs.count() == 1:
        obj = qs.first()
        return obj.company_code if obj and obj.company_code else None
    return None


def generate_sql(records, **kwargs):
    cfg = get_config()
    update_drafting = kwargs.get('update_drafting', False)
    update_contract_party = kwargs.get('update_contract_party', False)
    old_drafting_id = kwargs.get('old_drafting_id')
    old_drafting_name = kwargs.get('old_drafting_name')
    old_party_id = kwargs.get('old_party_id')
    old_party_name = kwargs.get('old_party_name')

    # 获取并解析ops_remark
    ops_remark = parse_ops_remark(kwargs.get('ops_remark', ''))

    sql = []
    sql.append("1、执行语句")
    if cfg.get('MERGE_MODULES', {}).get('unit', True):
        def set_parts_from(r):
            parts = []
            if update_drafting:
                ndid = r.get('new_drafting_id', kwargs.get('new_drafting_id'))
                ndnm = r.get('new_drafting_name',
                             kwargs.get('new_drafting_name'))
                if not ndid and ndnm:
                    code = extract_company_code(ndnm)
                    if code:
                        ndid = code
                if ndid:
                    parts.append(f"PRIMARY_CONTRACT_DRAFTING_UNIT='{ndid}'")
                if ndnm:
                    parts.append(
                        f"PRIMARY_CONTRACT_DRAFTING_UNIT_NAME='{extract_company_name(ndnm)}'")
            if update_contract_party:
                npid = r.get('new_party_id', kwargs.get('new_party_id'))
                npnm = r.get('new_party_name', kwargs.get('new_party_name'))
                if not npid and npnm:
                    code = extract_company_code(npnm)
                    if code:
                        npid = code
                if npid:
                    parts.append(f"CONTRACT_PARTY_ID='{npid}'")
                if npnm:
                    parts.append(
                        f"CONTRACT_PARTY_NAME='{extract_company_name(npnm)}'")
            return ', '.join(parts)

        def key_fn(r):
            return set_parts_from(r)
        groups = merge_by_key(records, key_fn)
        for set_clause, recs in groups.items():
            if not set_clause:
                continue
            schemes = [r['scheme'] for r in recs if r.get('scheme')]
            for chunk in chunk_list(schemes, int(cfg.get('MERGE_MAX_IN_SIZE', 500))):
                sql.append(
                    f"update tprfa03 set {set_clause}, OPS_REMARK='{ops_remark}' where PURCHASE_SCHEME_NO IN ({format_in(chunk)});")
            conds_xj = [{'PURCHASE_SCHEME_NO': r.get(
                'scheme'), 'INQ_ID': r.get('inquiry')} for r in recs]
            conds_xj = [
                c for c in conds_xj if c['PURCHASE_SCHEME_NO'] and c['INQ_ID']]
            if conds_xj:
                where_or = compose_or(
                    conds_xj, ['PURCHASE_SCHEME_NO', 'INQ_ID'])
                sql.append(
                    f"update tprxj05 set {set_clause}, OPS_REMARK='{ops_remark}' where {where_or};")
            conds_nq = [{'PURCHASE_SCHEME_NO': r.get('scheme'), 'INQ_ID': r.get(
                'inquiry'), 'sign_id': r.get('result')} for r in recs]
            conds_nq = [c for c in conds_nq if c['PURCHASE_SCHEME_NO']
                        and c['INQ_ID'] and c['sign_id']]
            if conds_nq:
                where_or = compose_or(
                    conds_nq, ['PURCHASE_SCHEME_NO', 'INQ_ID', 'sign_id'])
                sql.append(
                    f"update tprnq03 set {set_clause}, OPS_REMARK='{ops_remark}' where {where_or};")
    else:
        for r in records:
            parts = []
            if update_drafting:
                ndid = r.get('new_drafting_id', kwargs.get('new_drafting_id'))
                ndnm = r.get('new_drafting_name',
                             kwargs.get('new_drafting_name'))
                if not ndid and ndnm:
                    code = extract_company_code(ndnm)
                    if code:
                        ndid = code
                if ndid:
                    parts.append(f"PRIMARY_CONTRACT_DRAFTING_UNIT='{ndid}'")
                if ndnm:
                    parts.append(
                        f"PRIMARY_CONTRACT_DRAFTING_UNIT_NAME='{extract_company_name(ndnm)}'")
            if update_contract_party:
                npid = r.get('new_party_id', kwargs.get('new_party_id'))
                npnm = r.get('new_party_name', kwargs.get('new_party_name'))
                if not npid and npnm:
                    code = extract_company_code(npnm)
                    if code:
                        npid = code
                if npid:
                    parts.append(f"CONTRACT_PARTY_ID='{npid}'")
                if npnm:
                    parts.append(
                        f"CONTRACT_PARTY_NAME='{extract_company_name(npnm)}'")
            if parts:
                set_clause = ', '.join(parts)
                sql.append(
                    f"update tprfa03 set {set_clause}, OPS_REMARK='{ops_remark}' where PURCHASE_SCHEME_NO='{r['scheme']}';")
                sql.append(
                    f"update tprxj05 set {set_clause}, OPS_REMARK='{ops_remark}' where PURCHASE_SCHEME_NO='{r['scheme']}' AND INQ_ID='{r['inquiry']}';")
                sql.append(
                    f"update tprnq03 set {set_clause}, OPS_REMARK='{ops_remark}' where PURCHASE_SCHEME_NO='{r['scheme']}' AND INQ_ID='{r['inquiry']}' AND sign_id='{r['result']}';")

    sql.append("2.回退语句")
    if cfg.get('MERGE_MODULES', {}).get('unit', True):
        def rb_parts_from(r):
            rb = []
            if update_drafting:
                odid = r.get('orig_drafting_id', old_drafting_id)
                odnm = r.get('orig_drafting_name', old_drafting_name)
                if not odid and odnm:
                    code = extract_company_code(odnm)
                    if code:
                        odid = code
                if odid:
                    rb.append(f"PRIMARY_CONTRACT_DRAFTING_UNIT='{odid}'")
                if odnm:
                    rb.append(
                        f"PRIMARY_CONTRACT_DRAFTING_UNIT_NAME='{extract_company_name(odnm)}'")
            if update_contract_party:
                opid = r.get('orig_party_id', old_party_id)
                opnm = r.get('orig_party_name', old_party_name)
                if not opid and opnm:
                    code = extract_company_code(opnm)
                    if code:
                        opid = code
                if opid:
                    rb.append(f"CONTRACT_PARTY_ID='{opid}'")
                if opnm:
                    rb.append(
                        f"CONTRACT_PARTY_NAME='{extract_company_name(opnm)}'")
            return ', '.join(rb)
        groups_rb = merge_by_key(records, rb_parts_from)
        for rb_clause, recs in groups_rb.items():
            if not rb_clause:
                continue
            schemes = [r['scheme'] for r in recs if r.get('scheme')]
            for chunk in chunk_list(schemes, int(cfg.get('MERGE_MAX_IN_SIZE', 500))):
                sql.append(
                    f"update tprfa03 set {rb_clause}, OPS_REMARK='' where PURCHASE_SCHEME_NO IN ({format_in(chunk)});")
            conds_xj = [{'PURCHASE_SCHEME_NO': r.get(
                'scheme'), 'INQ_ID': r.get('inquiry')} for r in recs]
            conds_xj = [
                c for c in conds_xj if c['PURCHASE_SCHEME_NO'] and c['INQ_ID']]
            if conds_xj:
                where_or = compose_or(
                    conds_xj, ['PURCHASE_SCHEME_NO', 'INQ_ID'])
                sql.append(
                    f"update tprxj05 set {rb_clause}, OPS_REMARK='' where {where_or};")
            conds_nq = [{'PURCHASE_SCHEME_NO': r.get('scheme'), 'INQ_ID': r.get(
                'inquiry'), 'sign_id': r.get('result')} for r in recs]
            conds_nq = [c for c in conds_nq if c['PURCHASE_SCHEME_NO']
                        and c['INQ_ID'] and c['sign_id']]
            if conds_nq:
                where_or = compose_or(
                    conds_nq, ['PURCHASE_SCHEME_NO', 'INQ_ID', 'sign_id'])
                sql.append(
                    f"update tprnq03 set {rb_clause}, OPS_REMARK='' where {where_or};")
    else:
        for r in records:
            rb_parts = []
            if update_drafting:
                odid = r.get('orig_drafting_id', old_drafting_id)
                odnm = r.get('orig_drafting_name', old_drafting_name)
                if not odid and odnm:
                    code = extract_company_code(odnm)
                    if code:
                        odid = code
                if odid:
                    rb_parts.append(f"PRIMARY_CONTRACT_DRAFTING_UNIT='{odid}'")
                if odnm:
                    rb_parts.append(
                        f"PRIMARY_CONTRACT_DRAFTING_UNIT_NAME='{extract_company_name(odnm)}'")
            if update_contract_party:
                opid = r.get('orig_party_id', old_party_id)
                opnm = r.get('orig_party_name', old_party_name)
                if not opid and opnm:
                    code = extract_company_code(opnm)
                    if code:
                        opid = code
                if opid:
                    rb_parts.append(f"CONTRACT_PARTY_ID='{opid}'")
                if opnm:
                    rb_parts.append(
                        f"CONTRACT_PARTY_NAME='{extract_company_name(opnm)}'")
            if rb_parts:
                rb_clause = ', '.join(rb_parts)
                sql.append(
                    f"update tprfa03 set {rb_clause}, OPS_REMARK='' where PURCHASE_SCHEME_NO='{r['scheme']}';")
                sql.append(
                    f"update tprxj05 set {rb_clause}, OPS_REMARK='' where PURCHASE_SCHEME_NO='{r['scheme']}' AND INQ_ID='{r['inquiry']}';")
                sql.append(
                    f"update tprnq03 set {rb_clause}, OPS_REMARK='' where PURCHASE_SCHEME_NO='{r['scheme']}' AND INQ_ID='{r['inquiry']}' AND sign_id='{r['result']}';")

    sql.append("3.数据库")
    sql.append("ip：192.168.11.76")
    sql.append("库名：cnnc_ph")
    return "\n".join(sql)


def parse_excel(file):
    wb = openpyxl.load_workbook(file)
    ws = wb.active
    records = []
    headers = [cell.value for cell in ws[1]]
    hset = {str(h) if h is not None else '' for h in headers}
    idx = {str(h): i for i, h in enumerate(headers)}
    scheme_alts = ['scheme_no', 'PURCHASE_SCHEME_NO',
                   'purchase_scheme_no', '采购方案编号']
    inquiry_alts = ['inquiry_no', 'inq_id', 'INQ_ID', '询价单编号']
    result_alts = ['result_no', 'sign_id', 'SIGN_ID', '定标结果编号']
    nd_code_alts = ['new_drafting_code', '新起草单位编码',
                    'new_drafting_id', '新起草单位ID', '组织机构编码', 'company_code']
    nd_plate_alts = ['new_drafting_plate_code', '新起草单位板块编码', 'plate_code']
    np_code_alts = ['new_party_code', '新签约主体编码',
                    'new_party_id', '新签约主体ID', 'company_code']
    np_plate_alts = ['new_party_plate_code', '新签约主体板块编码', 'plate_code']
    od_code_alts = ['orig_drafting_code', '原起草单位编码',
                    'orig_drafting_id', '原起草单位ID', '组织机构编码']
    od_plate_alts = ['orig_drafting_plate_code', '原起草单位板块编码']
    op_code_alts = ['orig_party_code', '原签约主体编码', 'orig_party_id', '原签约主体ID']
    op_plate_alts = ['orig_party_plate_code', '原签约主体板块编码']

    def pick(alts):
        for a in alts:
            if a in idx:
                return idx[a]
        return None
    s_idx = pick(scheme_alts)
    i_idx = pick(inquiry_alts)
    r_idx = pick(result_alts)
    if s_idx is None or i_idx is None or r_idx is None:
        raise ValueError("Excel 缺少必要列：方案、询价、定标")
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not any(row):
            continue
        rec = {
            'scheme': row[s_idx],
            'inquiry': row[i_idx],
            'result': row[r_idx]
        }
        if not all(rec.values()):
            continue
        ndid = None
        ndnm = None
        npid = None
        npnm = None
        odid = None
        odnm = None
        opid = None
        opnm = None
        for k in ['new_drafting_id', '新起草单位ID']:
            if k in idx:
                ndid = row[idx[k]]
                break
        nd_code_idx = pick(nd_code_alts)
        if nd_code_idx is not None:
            ndid = row[nd_code_idx]
        for k in ['new_drafting_name', '新起草单位名称', '组织机构名称']:
            if k in idx:
                ndnm = row[idx[k]]
                break
        nd_plate_idx = pick(nd_plate_alts)
        if nd_plate_idx is not None:
            rec['new_drafting_plate_code'] = row[nd_plate_idx]
        for k in ['new_party_id', '新签约主体ID']:
            if k in idx:
                npid = row[idx[k]]
                break
        np_code_idx = pick(np_code_alts)
        if np_code_idx is not None:
            npid = row[np_code_idx]
        for k in ['new_party_name', '新签约主体名称']:
            if k in idx:
                npnm = row[idx[k]]
                break
        np_plate_idx = pick(np_plate_alts)
        if np_plate_idx is not None:
            rec['new_party_plate_code'] = row[np_plate_idx]
        for k in ['orig_drafting_id', '原起草单位ID']:
            if k in idx:
                odid = row[idx[k]]
                break
        od_code_idx = pick(od_code_alts)
        if od_code_idx is not None:
            odid = row[od_code_idx]
        for k in ['orig_drafting_name', '原起草单位名称', '组织机构名称']:
            if k in idx:
                odnm = row[idx[k]]
                break
        od_plate_idx = pick(od_plate_alts)
        if od_plate_idx is not None:
            rec['orig_drafting_plate_code'] = row[od_plate_idx]
        for k in ['orig_party_id', '原签约主体ID']:
            if k in idx:
                opid = row[idx[k]]
                break
        op_code_idx = pick(op_code_alts)
        if op_code_idx is not None:
            opid = row[op_code_idx]
        for k in ['orig_party_name', '原签约主体名称']:
            if k in idx:
                opnm = row[idx[k]]
                break
        op_plate_idx = pick(op_plate_alts)
        if op_plate_idx is not None:
            rec['orig_party_plate_code'] = row[op_plate_idx]
        if ndid is not None:
            rec['new_drafting_id'] = ndid
        if ndnm is not None:
            rec['new_drafting_name'] = ndnm
        if npid is not None:
            rec['new_party_id'] = npid
        if npnm is not None:
            rec['new_party_name'] = npnm
        if odid is not None:
            rec['orig_drafting_id'] = odid
        if odnm is not None:
            rec['orig_drafting_name'] = odnm
        if opid is not None:
            rec['orig_party_id'] = opid
        if opnm is not None:
            rec['orig_party_name'] = opnm
        records.append(rec)
    return records


def unit_change_view(request):
    logger.info(
        f"============ unit_change_view called: method={request.method} ============")

    if request.method == 'POST':
        logger.info("Processing POST request")
        form = UnitChangeForm(request.POST, request.FILES)

        if form.is_valid():
            logger.info("Form is valid, processing data")
            cd = form.cleaned_data

            # 记录请求输入
            log_view_input("合同起草、签约单位修改", cd)

            if cd.get('excel_file'):
                records = parse_excel(cd['excel_file'])
                will_update_drafting = any(r.get('new_drafting_id') or r.get(
                    'new_drafting_name') for r in records)
                will_update_party = any(r.get('new_party_id') or r.get(
                    'new_party_name') for r in records)

                # 统一处理名称到编号的转换
                enriched = []
                fail_rows = []

                # 记录Excel解析结果
                logger.info(f"Excel解析完成: 总记录数={len(records)}")

                for r in records:
                    # 尝试从名称中提取编号或查询数据库
                    for k_name, k_id in [
                        ('new_drafting_name', 'new_drafting_id'),
                        ('orig_drafting_name', 'orig_drafting_id'),
                        ('new_party_name', 'new_party_id'),
                        ('orig_party_name', 'orig_party_id')
                    ]:
                        if r.get(k_name) and not r.get(k_id):
                            # 先尝试从"名称-编号"格式提取
                            code = extract_company_code(str(r[k_name]))
                            if code:
                                r[k_id] = code
                            else:
                                # 如果不是"名称-编号"格式，尝试通过名称查询数据库
                                uc = _unique_code_by_name(str(r[k_name]))
                                if uc:
                                    r[k_id] = uc

                    # 验证是否有可更新的字段
                    parts = []
                    if will_update_drafting:
                        if r.get('new_drafting_id'):
                            parts.append('PRIMARY_CONTRACT_DRAFTING_UNIT')
                        if r.get('new_drafting_name'):
                            parts.append('PRIMARY_CONTRACT_DRAFTING_UNIT_NAME')
                    if will_update_party:
                        if r.get('new_party_id'):
                            parts.append('CONTRACT_PARTY_ID')
                        if r.get('new_party_name'):
                            parts.append('CONTRACT_PARTY_NAME')

                    # 检查是否缺少必要字段
                    desc = []
                    if not parts:
                        desc.append('未提供可更新字段')
                    if will_update_drafting and not (r.get('orig_drafting_id') or r.get('orig_drafting_name')):
                        desc.append('缺少起草单位回退字段')
                    if will_update_party and not (r.get('orig_party_id') or r.get('orig_party_name')):
                        desc.append('缺少签约主体回退字段')

                    if desc:
                        fail_rows.append({
                            'scheme': r.get('scheme'),
                            'inquiry': r.get('inquiry'),
                            'result': r.get('result'),
                            'new_drafting_name': r.get('new_drafting_name'),
                            'new_drafting_id': r.get('new_drafting_id'),
                            'orig_drafting_name': r.get('orig_drafting_name'),
                            'orig_drafting_id': r.get('orig_drafting_id'),
                            'new_party_name': r.get('new_party_name'),
                            'new_party_id': r.get('new_party_id'),
                            'orig_party_name': r.get('orig_party_name'),
                            'orig_party_id': r.get('orig_party_id'),
                            'desc': '; '.join(desc)
                        })
                    enriched.append(r)
                records = enriched
            else:
                records = [{
                    'scheme': cd['scheme_no'],
                    'inquiry': cd['inquiry_no'],
                    'result': cd['result_no']
                }]

            if cd.get('excel_file'):
                will_update_drafting = any(
                    r.get('new_drafting_id') or r.get('new_drafting_name') for r in records
                )
                will_update_party = any(
                    r.get('new_party_id') or r.get('new_party_name') for r in records
                )
            else:
                will_update_drafting = bool(
                    cd.get('new_drafting_id') or cd.get('new_drafting_name'))
                will_update_party = bool(
                    cd.get('new_party_id') or cd.get('new_party_name'))
            update_drafting = will_update_drafting
            update_contract_party = will_update_party

            missing_names = []
            # 单条记录的名称到编号转换
            if not cd.get('excel_file'):
                for k_name, k_id in [
                    ('new_drafting_name', 'new_drafting_id'),
                    ('old_drafting_name', 'old_drafting_id'),
                    ('new_party_name', 'new_party_id'),
                    ('old_party_name', 'old_party_id')
                ]:
                    if cd.get(k_name) and not cd.get(k_id):
                        code = extract_company_code(cd[k_name])
                        if code:
                            cd[k_id] = code
                        else:
                            uc = _unique_code_by_name(cd[k_name])
                            if uc:
                                cd[k_id] = uc
                            else:
                                missing_names.append(cd[k_name])

            if missing_names:
                logger.warning(f"以下单位名称未能找到编号: {missing_names}")

            # 解析OPS_REMARK
            ops_remark = parse_ops_remark(cd.get('ops_remark', ''))

            sql_content = generate_sql(
                records,
                update_drafting=update_drafting,
                update_contract_party=update_contract_party,
                old_drafting_id=cd.get('old_drafting_id'),
                old_drafting_name=cd.get('old_drafting_name'),
                new_drafting_id=cd.get('new_drafting_id'),
                new_drafting_name=cd.get('new_drafting_name'),
                old_party_id=cd.get('old_party_id'),
                old_party_name=cd.get('old_party_name'),
                new_party_id=cd.get('new_party_id'),
                new_party_name=cd.get('new_party_name'),
                ops_remark=ops_remark
            )

            # 记录SQL生成结果
            logger.info(
                f"SQL生成完成: 更新起草单位={update_drafting}, 更新签约主体={update_contract_party}, SQL长度={len(sql_content)}")

            now = datetime.now()
            year_month = now.strftime("%Y%m")
            day = now.strftime("%d")
            if will_update_drafting and will_update_party:
                suffix = "修改起草单位和签约主体"
            elif will_update_drafting:
                suffix = "修改起草单位"
            elif will_update_party:
                suffix = "修改签约主体"
            else:
                suffix = "修改单位信息"
            filename = f"{cd['dynamic_id']}_{suffix}.sql"

            base_dir = r"D:\临时文件"
            target_dir = os.path.join(base_dir, year_month, day)
            os.makedirs(target_dir, exist_ok=True)
            filepath = os.path.join(target_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(sql_content)

            # 记录文件保存
            logger.info(f"SQL文件已保存: {filepath}")

            temp_dir = os.path.join(settings.BASE_DIR, 'temp_downloads')
            os.makedirs(temp_dir, exist_ok=True)
            download_path = os.path.join(temp_dir, filename)
            with open(download_path, 'w', encoding='utf-8') as f:
                f.write(sql_content)
            supplement_download_url = None
            if cd.get('excel_file'):
                wb_src = openpyxl.load_workbook(cd['excel_file'])
                ws_src = wb_src.active
                headers = [cell.value for cell in ws_src[1]]
                wb_sup = openpyxl.Workbook()
                ws_sup = wb_sup.active
                ws_sup.title = '补充模板'
                sup_cols = ['新起草单位ID(补充)', '新起草单位名称(补充)', '原起草单位ID(补充)', '原起草单位名称(补充)',
                            '新签约主体ID(补充)', '新签约主体名称(补充)', '原签约主体ID(补充)', '原签约主体名称(补充)', '校验结果']
                ws_sup.append(headers + sup_cols)
                row_index = 0
                for row in ws_src.iter_rows(min_row=2, values_only=True):
                    if row is None:
                        continue
                    r = records[row_index] if row_index < len(records) else {}
                    sup_vals = [
                        r.get('new_drafting_id'), r.get('new_drafting_name'),
                        r.get('orig_drafting_id'), r.get('orig_drafting_name'),
                        r.get('new_party_id'), r.get('new_party_name'),
                        r.get('orig_party_id'), r.get('orig_party_name'),
                    ]
                    descs = []

                    def check_pair(nm, cid):
                        if nm and cid:
                            obj = OrgDetail.objects.filter(
                                company_code=str(cid).strip()).first()
                            if obj and str(obj.company_name).strip() != extract_company_name(str(nm)):
                                return '名称编码不匹配'
                        return None
                    d1 = check_pair(r.get('new_drafting_name'),
                                    r.get('new_drafting_id'))
                    d2 = check_pair(r.get('orig_drafting_name'),
                                    r.get('orig_drafting_id'))
                    d3 = check_pair(r.get('new_party_name'),
                                    r.get('new_party_id'))
                    d4 = check_pair(r.get('orig_party_name'),
                                    r.get('orig_party_id'))
                    for d in [d1, d2, d3, d4]:
                        if d:
                            descs.append(d)
                    ws_sup.append(list(row) + sup_vals +
                                  ['; '.join(descs) if descs else '补充成功'])
                    row_index += 1
                sup_name = f"{cd['dynamic_id']}_单位信息修改_补充模板.xlsx"
                sup_path = os.path.join(temp_dir, sup_name)
                wb_sup.save(sup_path)
                supplement_download_url = f"/download/{sup_name}"
            supplement_download_url = None
            if cd.get('excel_file'):
                wb_src = openpyxl.load_workbook(cd['excel_file'])
                ws_src = wb_src.active
                headers = [cell.value for cell in ws_src[1]]
                wb_sup = openpyxl.Workbook()
                ws_sup = wb_sup.active
                ws_sup.title = '补充模板'
                sup_cols = ['新起草单位ID(补充)', '新起草单位名称(补充)', '原起草单位ID(补充)', '原起草单位名称(补充)',
                            '新签约主体ID(补充)', '新签约主体名称(补充)', '原签约主体ID(补充)', '原签约主体名称(补充)', '校验结果']
                ws_sup.append(headers + sup_cols)
                row_index = 0
                for row in ws_src.iter_rows(min_row=2, values_only=True):
                    if row is None:
                        continue
                    r = records[row_index] if row_index < len(records) else {}
                    sup_vals = [
                        r.get('new_drafting_id'), r.get('new_drafting_name'),
                        r.get('orig_drafting_id'), r.get('orig_drafting_name'),
                        r.get('new_party_id'), r.get('new_party_name'),
                        r.get('orig_party_id'), r.get('orig_party_name'),
                    ]
                    descs = []

                    def check_pair(nm, cid):
                        if nm and cid:
                            obj = OrgDetail.objects.filter(
                                company_code=str(cid).strip()).first()
                            if obj and str(obj.company_name).strip() != extract_company_name(str(nm)):
                                return '名称编码不匹配'
                        return None
                    d1 = check_pair(r.get('new_drafting_name'),
                                    r.get('new_drafting_id'))
                    d2 = check_pair(r.get('orig_drafting_name'),
                                    r.get('orig_drafting_id'))
                    d3 = check_pair(r.get('new_party_name'),
                                    r.get('new_party_id'))
                    d4 = check_pair(r.get('orig_party_name'),
                                    r.get('orig_party_id'))
                    for d in [d1, d2, d3, d4]:
                        if d:
                            descs.append(d)
                    ws_sup.append(list(row) + sup_vals +
                                  ['; '.join(descs) if descs else '补充成功'])
                    row_index += 1
                sup_name = f"{cd['dynamic_id']}_单位信息修改_补充模板.xlsx"
                sup_path = os.path.join(temp_dir, sup_name)
                wb_sup.save(sup_path)
                supplement_download_url = f"/download/{sup_name}"
            supplement_download_url = None
            if cd.get('excel_file'):
                wb_src = openpyxl.load_workbook(cd['excel_file'])
                ws_src = wb_src.active
                headers = [cell.value for cell in ws_src[1]]
                wb_sup = openpyxl.Workbook()
                ws_sup = wb_sup.active
                ws_sup.title = '补充模板'
                sup_cols = ['新起草单位ID(补充)', '新起草单位名称(补充)', '原起草单位ID(补充)', '原起草单位名称(补充)',
                            '新签约主体ID(补充)', '新签约主体名称(补充)', '原签约主体ID(补充)', '原签约主体名称(补充)', '校验结果']
                ws_sup.append(headers + sup_cols)
                row_index = 0
                for row in ws_src.iter_rows(min_row=2, values_only=True):
                    if row is None:
                        continue
                    r = records[row_index] if row_index < len(records) else {}
                    sup_vals = [
                        r.get('new_drafting_id'), r.get('new_drafting_name'),
                        r.get('orig_drafting_id'), r.get('orig_drafting_name'),
                        r.get('new_party_id'), r.get('new_party_name'),
                        r.get('orig_party_id'), r.get('orig_party_name'),
                    ]
                    descs = []
                    # 校验名称与编码对应性

                    def check_pair(nm, cid):
                        if nm and cid:
                            obj = OrgDetail.objects.filter(
                                company_code=str(cid).strip()).first()
                            if obj and str(obj.company_name).strip() != extract_company_name(str(nm)):
                                return '名称编码不匹配'
                        return None
                    d1 = check_pair(r.get('new_drafting_name'),
                                    r.get('new_drafting_id'))
                    d2 = check_pair(r.get('orig_drafting_name'),
                                    r.get('orig_drafting_id'))
                    d3 = check_pair(r.get('new_party_name'),
                                    r.get('new_party_id'))
                    d4 = check_pair(r.get('orig_party_name'),
                                    r.get('orig_party_id'))
                    for d in [d1, d2, d3, d4]:
                        if d:
                            descs.append(d)
                    ws_sup.append(list(row) + sup_vals +
                                  ['; '.join(descs) if descs else '补充成功'])
                    row_index += 1
                sup_name = f"{cd['dynamic_id']}_单位信息修改_补充模板.xlsx"
                sup_path = os.path.join(temp_dir, sup_name)
                wb_sup.save(sup_path)
                supplement_download_url = f"/download/{sup_name}"
            fail_download_url = None
            if cd.get('excel_file') and 'fail_rows' in locals() and fail_rows:
                wb = openpyxl.Workbook()
                ws = wb.active
                ws.title = '失败明细'
                ws.append(['采购方案编号', '询价单编号', '定标结果编号', '新起草单位名称', '新起草单位ID', '原起草单位名称',
                          '原起草单位ID', '新签约主体名称', '新签约主体ID', '原签约主体名称', '原签约主体ID', '描述'])
                for r in fail_rows:
                    ws.append([
                        r.get('scheme'), r.get('inquiry'), r.get('result'),
                        r.get('new_drafting_name'), r.get('new_drafting_id'),
                        r.get('orig_drafting_name'), r.get('orig_drafting_id'),
                        r.get('new_party_name'), r.get('new_party_id'),
                        r.get('orig_party_name'), r.get('orig_party_id'),
                        r.get('desc')
                    ])
                fail_name = f"{cd['dynamic_id']}_单位信息修改_失败.xlsx"
                fail_path = os.path.join(temp_dir, fail_name)
                wb.save(fail_path)
                fail_download_url = f"/download/{fail_name}"

            # 将Decimal类型转换为字符串以支持JSON序列化
            session_data = {}
            for k, v in cd.items():
                if k != 'excel_file':
                    # 处理Decimal类型
                    if hasattr(v, 'to_eng_string'):
                        session_data[k] = v.to_eng_string()
                    else:
                        session_data[k] = v
            request.session['unit_change_last'] = session_data
            return render(request, 'success.html', {
                'filepath': filepath,
                'download_url': f'/download/{filename}',
                'fail_download_url': fail_download_url,
                'supplement_download_url': supplement_download_url
            })
        else:
            # 表单验证失败
            logger.error(f"Form validation failed: {form.errors}")
    else:
        logger.info("Processing GET request")
        if request.GET.get('clear'):
            request.session.pop('unit_change_last', None)
            form = UnitChangeForm()
        else:
            initial = request.session.get('unit_change_last')
            form = UnitChangeForm(initial=initial)

    return render(request, 'unit_change_form.html', {'form': form})


def download_sql(request, filename):
    file_path = os.path.join(settings.BASE_DIR, 'temp_downloads', filename)
    if os.path.exists(file_path):
        response = FileResponse(open(file_path, 'rb'),
                                as_attachment=True, filename=filename)
        return response
    else:
        return HttpResponse("文件不存在", status=404)


def generate_price_sql(line_ids, new_quantity, new_price, orig_quantity=None, orig_price=None, ops_remark=''):
    line_id_str = "', '".join(line_ids)
    line_id_in = f"'{line_id_str}'"
    sql = []
    sql.append("1、执行语句")

    # 解析操作备注
    ops_remark = parse_ops_remark(ops_remark)
    if new_quantity is not None:
        stmt = (
            "UPDATE tphct02 SET "
            f"BPO_QTY={new_quantity}, "
            f"BPO_PRICE={new_price}, "
            f"BPO_AMT={new_price}*{new_quantity}, "
            f"BPO_NOTAX_PRICE={new_price}/(1+TAX_RATE), "
            f"BPO_NOTAX_AMT=({new_price}*{new_quantity})/(1+TAX_RATE), "
            f"OPS_REMARK='{ops_remark}' "
            f"WHERE BPO_LINE_ID IN ({line_id_in}) AND ALIVE_FLAG='1';"
        )
    else:
        stmt = (
            "UPDATE tphct02 SET "
            f"BPO_PRICE={new_price}, "
            f"BPO_AMT={new_price}*BPO_QTY, "
            f"BPO_NOTAX_PRICE={new_price}/(1+TAX_RATE), "
            f"BPO_NOTAX_AMT=({new_price}*BPO_QTY)/(1+TAX_RATE), "
            f"OPS_REMARK='{ops_remark}' "
            f"WHERE BPO_LINE_ID IN ({line_id_in}) AND ALIVE_FLAG='1';"
        )
    sql.append(stmt)

    # 获取唯一的BPO_ID列表
    bpo_ids = []
    for line_id in line_ids:
        # 从line_id中提取BPO_ID（假设格式为 BPO_ID-000001）
        bpo_id_parts = line_id.split('-')
        if len(bpo_id_parts) > 4:  # 处理包含多个连字符的情况
            bpo_id = '-'.join(bpo_id_parts[:-1])
        else:
            bpo_id = '-'.join(bpo_id_parts[:-1]
                              ) if len(bpo_id_parts) > 1 else line_id
        if bpo_id not in bpo_ids:
            bpo_ids.append(bpo_id)

    # 批量更新合同主表汇总金额
    sql.append("-- 批量更新合同的主表汇总金额")
    for i, bpo_id in enumerate(bpo_ids, 1):
        main_stmt = (
            f"UPDATE tphct01 SET "
            f"BPO_AMT=(SELECT SUM(BPO_AMT) FROM tphct02 WHERE BPO_ID='{bpo_id}' AND ALIVE_FLAG='1'), "
            f"TARGET_AMT=(SELECT SUM(BPO_AMT) FROM tphct02 WHERE BPO_ID='{bpo_id}' AND ALIVE_FLAG='1'), "
            f"BPO_NOTAX_AMT=(SELECT SUM(BPO_NOTAX_AMT) FROM tphct02 WHERE BPO_ID='{bpo_id}' AND ALIVE_FLAG='1'), "
            f"OPS_REMARK='{ops_remark}' "
            f"WHERE BPO_ID='{bpo_id}' AND ALIVE_FLAG='1';"
        )
        sql.append(main_stmt)

    # 回退语句部分
    sql.append("2、回退语句")
    if orig_price is not None and orig_quantity is not None:
        rollback_stmt = (
            "UPDATE tphct02 SET "
            f"BPO_QTY={orig_quantity}, "
            f"BPO_PRICE={orig_price}, "
            f"BPO_AMT={orig_price}*{orig_quantity}, "
            f"BPO_NOTAX_PRICE={orig_price}/(1+TAX_RATE), "
            f"BPO_NOTAX_AMT=({orig_price}*{orig_quantity})/(1+TAX_RATE), "
            f"OPS_REMARK='' "
            f"WHERE BPO_LINE_ID IN ({line_id_in}) AND ALIVE_FLAG='1';"
        )
        sql.append(rollback_stmt)
    elif orig_price is not None and orig_quantity is None:
        rollback_stmt = (
            "UPDATE tphct02 SET "
            f"BPO_PRICE={orig_price}, "
            f"BPO_AMT={orig_price}*BPO_QTY, "
            f"BPO_NOTAX_PRICE={orig_price}/(1+TAX_RATE), "
            f"BPO_NOTAX_AMT=({orig_price}*BPO_QTY)/(1+TAX_RATE), "
            f"OPS_REMARK='' "
            f"WHERE BPO_LINE_ID IN ({line_id_in}) AND ALIVE_FLAG='1';"
        )
        sql.append(rollback_stmt)
    elif orig_price is None and orig_quantity is not None:
        rollback_stmt = (
            "UPDATE tphct02 SET "
            f"BPO_QTY={orig_quantity}, "
            f"BPO_AMT=BPO_PRICE*{orig_quantity}, "
            f"BPO_NOTAX_AMT=(BPO_PRICE*{orig_quantity})/(1+TAX_RATE), "
            f"OPS_REMARK='' "
            f"WHERE BPO_LINE_ID IN ({line_id_in}) AND ALIVE_FLAG='1';"
        )
        sql.append(rollback_stmt)

    # 回退合同主表
    sql.append("-- 回退合同主表")
    for i, bpo_id in enumerate(bpo_ids, 1):
        main_rollback_stmt = (
            f"UPDATE tphct01 SET "
            f"BPO_AMT=(SELECT SUM(BPO_AMT) FROM tphct02 WHERE BPO_ID='{bpo_id}' AND ALIVE_FLAG='1'), "
            f"TARGET_AMT=(SELECT SUM(BPO_AMT) FROM tphct02 WHERE BPO_ID='{bpo_id}' AND ALIVE_FLAG='1'), "
            f"BPO_NOTAX_AMT=(SELECT SUM(BPO_NOTAX_AMT) FROM tphct02 WHERE BPO_ID='{bpo_id}' AND ALIVE_FLAG='1'), "
            f"OPS_REMARK='' "
            f"WHERE BPO_ID='{bpo_id}' AND ALIVE_FLAG='1';"
        )
        sql.append(main_rollback_stmt)

    # 数据库信息
    sql.append("3.数据库")
    sql.append("ip：192.168.11.71")
    sql.append("库名：cnnc_ph")

    return "\n".join(sql)


def parse_price_excel(file):
    wb = openpyxl.load_workbook(file)
    ws = wb.active
    headers = [cell.value for cell in ws[1]]
    idx = {str(h): i for i, h in enumerate(headers)}

    def pick(alts):
        for a in alts:
            if a in idx:
                return idx[a]
        return None
    lid_idx = pick(['line_id', 'BPO_LINE_ID', '明细行ID'])
    price_idx = pick(['price', 'BPO_PRICE', '单价'])
    qty_idx = pick(['quantity', 'BPO_QTY', '数量'])
    orig_qty_idx = pick(['orig_quantity', '原数量'])
    orig_price_idx = pick(['orig_price', '原单价'])
    if lid_idx is None or price_idx is None:
        raise ValueError("Excel 缺少必要列：明细行ID/单价")
    records = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row:
            continue
        lid = row[lid_idx]
        prc = row[price_idx]
        qty = row[qty_idx] if qty_idx is not None else None
        if lid is None or prc is None:
            continue
        rec = {
            'line_id': str(lid).strip(),
            'price': prc,
            'quantity': qty,
        }
        if orig_qty_idx is not None:
            rec['orig_quantity'] = row[orig_qty_idx]
        if orig_price_idx is not None:
            rec['orig_price'] = row[orig_price_idx]
        records.append(rec)
    if not records:
        raise ValueError("Excel 中没有有效的行数据")
    return records


def generate_price_sql_bulk(records, ops_remark=None):
    cfg = get_config()
    sql = []
    sql.append("1、执行语句")
    if cfg.get('MERGE_MODULES', {}).get('price', True):
        def key_fn(r):
            return (r.get('price'), r.get('quantity'))
        groups = merge_by_key(records, key_fn)
        for k, recs in groups.items():
            p, q = k
            ids = [r['line_id'] for r in recs if r.get('line_id')]
            for chunk in chunk_list(ids, int(cfg.get('MERGE_MAX_IN_SIZE', 500))):
                inlist = format_in(chunk)
                if q is not None:
                    stmt = (
                        f"UPDATE tphct02 SET "
                        f"BPO_QTY={q}, "
                        f"BPO_PRICE={p}, "
                        f"BPO_AMT={p}*{q}, "
                        f"BPO_NOTAX_PRICE={p}/(1+TAX_RATE), "
                        f"BPO_NOTAX_AMT=({p}*{q})/(1+TAX_RATE), "
                        f"OPS_REMARK='{ops_remark or ''}' "
                        f"WHERE BPO_LINE_ID IN ({inlist}) AND ALIVE_FLAG='1';"
                    )
                else:
                    stmt = (
                        f"UPDATE tphct02 SET "
                        f"BPO_PRICE={p}, "
                        f"BPO_AMT={p}*BPO_QTY, "
                        f"BPO_NOTAX_PRICE={p}/(1+TAX_RATE), "
                        f"BPO_NOTAX_AMT=({p}*BPO_QTY)/(1+TAX_RATE), "
                        f"OPS_REMARK='{ops_remark or ''}' "
                        f"WHERE BPO_LINE_ID IN ({inlist}) AND ALIVE_FLAG='1';"
                    )
                sql.append(stmt)
    else:
        for r in records:
            q = r.get('quantity')
            if q is not None:
                exec_stmt = (
                    f"UPDATE tphct02 SET "
                    f"BPO_QTY={q}, "
                    f"BPO_PRICE={r['price']}, "
                    f"BPO_AMT={r['price']}*{q}, "
                    f"BPO_NOTAX_PRICE={r['price']}/(1+TAX_RATE), "
                    f"BPO_NOTAX_AMT=({r['price']}*{q})/(1+TAX_RATE), "
                    f"OPS_REMARK='{ops_remark or ''}' "
                    f"WHERE BPO_LINE_ID='{r['line_id']}' AND ALIVE_FLAG='1';"
                )
            else:
                exec_stmt = (
                    f"UPDATE tphct02 SET "
                    f"BPO_PRICE={r['price']}, "
                    f"BPO_AMT={r['price']}*BPO_QTY, "
                    f"BPO_NOTAX_PRICE={r['price']}/(1+TAX_RATE), "
                    f"BPO_NOTAX_AMT=({r['price']}*BPO_QTY)/(1+TAX_RATE), "
                    f"OPS_REMARK='{ops_remark or ''}' "
                    f"WHERE BPO_LINE_ID='{r['line_id']}' AND ALIVE_FLAG='1';"
                )
            sql.append(exec_stmt)
    bpo_ids = []
    for r in records:
        parts = r['line_id'].split('-')
        if len(parts) > 4:
            bpo_id = '-'.join(parts[:-1])
        else:
            bpo_id = '-'.join(parts[:-1]) if len(parts) > 1 else r['line_id']
        if bpo_id not in bpo_ids:
            bpo_ids.append(bpo_id)
    sql.append("-- 批量更新合同的主表汇总金额")
    for bpo_id in bpo_ids:
        main_stmt = (
            f"UPDATE tphct01 SET "
            f"BPO_AMT=(SELECT SUM(BPO_AMT) FROM tphct02 WHERE BPO_ID='{bpo_id}' AND ALIVE_FLAG='1'), "
            f"TARGET_AMT=(SELECT SUM(BPO_AMT) FROM tphct02 WHERE BPO_ID='{bpo_id}' AND ALIVE_FLAG='1'), "
            f"BPO_NOTAX_AMT=(SELECT SUM(BPO_NOTAX_AMT) FROM tphct02 WHERE BPO_ID='{bpo_id}' AND ALIVE_FLAG='1'), "
            f"OPS_REMARK='{ops_remark or ''}' "
            f"WHERE BPO_ID='{bpo_id}' AND ALIVE_FLAG='1';"
        )
        sql.append(main_stmt)
    sql.append("2、回退语句")
    if cfg.get('MERGE_MODULES', {}).get('price', True):
        def rb_key(r):
            return (r.get('orig_price'), r.get('orig_quantity'))
        groups = merge_by_key(records, rb_key)
        for k, recs in groups.items():
            rp, rq = k
            if rp is None and rq is None:
                continue
            ids = [r['line_id'] for r in recs if r.get('line_id')]
            for chunk in chunk_list(ids, int(cfg.get('MERGE_MAX_IN_SIZE', 500))):
                inlist = format_in(chunk)
                if rq is not None and rp is not None:
                    rollback_stmt = (
                        f"UPDATE tphct02 SET "
                        f"BPO_QTY={rq}, "
                        f"BPO_PRICE={rp}, "
                        f"BPO_AMT={rp}*{rq}, "
                        f"BPO_NOTAX_PRICE={rp}/(1+TAX_RATE), "
                        f"BPO_NOTAX_AMT=({rp}*{rq})/(1+TAX_RATE), "
                        f"OPS_REMARK='' "
                        f"WHERE BPO_LINE_ID IN ({inlist}) AND ALIVE_FLAG='1';"
                    )
                elif rp is not None and rq is None:
                    rollback_stmt = (
                        f"UPDATE tphct02 SET "
                        f"BPO_PRICE={rp}, "
                        f"BPO_AMT={rp}*BPO_QTY, "
                        f"BPO_NOTAX_PRICE={rp}/(1+TAX_RATE), "
                        f"BPO_NOTAX_AMT=({rp}*BPO_QTY)/(1+TAX_RATE), "
                        f"OPS_REMARK='' "
                        f"WHERE BPO_LINE_ID IN ({inlist}) AND ALIVE_FLAG='1';"
                    )
                elif rp is None and rq is not None:
                    rollback_stmt = (
                        f"UPDATE tphct02 SET "
                        f"BPO_QTY={rq}, "
                        f"BPO_AMT=BPO_PRICE*{rq}, "
                        f"BPO_NOTAX_AMT=(BPO_PRICE*{rq})/(1+TAX_RATE), "
                        f"OPS_REMARK='' "
                        f"WHERE BPO_LINE_ID IN ({inlist}) AND ALIVE_FLAG='1';"
                    )
                else:
                    rollback_stmt = None
                if rollback_stmt:
                    sql.append(rollback_stmt)
    else:
        for r in records:
            rq = r.get('orig_quantity')
            rp = r.get('orig_price')
            if rq is not None and rp is not None:
                rollback_stmt = (
                    f"UPDATE tphct02 SET "
                    f"BPO_QTY={rq}, "
                    f"BPO_PRICE={rp}, "
                    f"BPO_AMT={rp}*{rq}, "
                    f"BPO_NOTAX_PRICE={rp}/(1+TAX_RATE), "
                    f"BPO_NOTAX_AMT=({rp}*{rq})/(1+TAX_RATE), "
                    f"OPS_REMARK='' "
                    f"WHERE BPO_LINE_ID='{r['line_id']}' AND ALIVE_FLAG='1';"
                )
                sql.append(rollback_stmt)
            elif rp is not None and rq is None:
                rollback_stmt = (
                    f"UPDATE tphct02 SET "
                    f"BPO_PRICE={rp}, "
                    f"BPO_AMT={rp}*BPO_QTY, "
                    f"BPO_NOTAX_PRICE={rp}/(1+TAX_RATE), "
                    f"BPO_NOTAX_AMT=({rp}*BPO_QTY)/(1+TAX_RATE), "
                    f"OPS_REMARK='' "
                    f"WHERE BPO_LINE_ID='{r['line_id']}' AND ALIVE_FLAG='1';"
                )
                sql.append(rollback_stmt)
            elif rp is None and rq is not None:
                rollback_stmt = (
                    f"UPDATE tphct02 SET "
                    f"BPO_QTY={rq}, "
                    f"BPO_AMT=BPO_PRICE*{rq}, "
                    f"BPO_NOTAX_AMT=(BPO_PRICE*{rq})/(1+TAX_RATE), "
                    f"OPS_REMARK='' "
                    f"WHERE BPO_LINE_ID='{r['line_id']}' AND ALIVE_FLAG='1';"
                )
                sql.append(rollback_stmt)
    sql.append("-- 回退合同主表")
    for bpo_id in bpo_ids:
        main_rollback_stmt = (
            f"UPDATE tphct01 SET "
            f"BPO_AMT=(SELECT SUM(BPO_AMT) FROM tphct02 WHERE BPO_ID='{bpo_id}' AND ALIVE_FLAG='1'), "
            f"TARGET_AMT=(SELECT SUM(BPO_AMT) FROM tphct02 WHERE BPO_ID='{bpo_id}' AND ALIVE_FLAG='1'), "
            f"BPO_NOTAX_AMT=(SELECT SUM(BPO_NOTAX_AMT) FROM tphct02 WHERE BPO_ID='{bpo_id}' AND ALIVE_FLAG='1'), "
            f"OPS_REMARK='' "
            f"WHERE BPO_ID='{bpo_id}' AND ALIVE_FLAG='1';"
        )
        sql.append(main_rollback_stmt)
    sql.append("3.数据库")
    sql.append("ip：192.168.11.71")
    sql.append("库名：cnnc_ph")
    return "\n".join(sql)


def normalize_item_id(v):
    if v is None:
        return None
    s = str(v).strip()
    if s.isdigit() and len(s) < 8:
        s = s.zfill(8)
    return s


def parse_item_excel(file):
    wb = openpyxl.load_workbook(file)
    ws = wb.active
    headers = [cell.value for cell in ws[1]]
    idx = {str(h): i for i, h in enumerate(headers)}

    def pick(alts):
        for a in alts:
            if a in idx:
                return idx[a]
        return None
    lid_idx = pick(['line_id', 'BPO_LINE_ID', '明细行ID'])
    new_id_idx = pick(['ITEM_ID', 'item_id', '物资编码'])
    new_name_idx = pick(['ITEM_NAME', 'item_name', '物资名称'])
    new_uom_idx = pick(['ITEM_UOM', 'item_uom', '计量单位'])
    new_cat_idx = pick(['CATEGORY', 'category', '物资分类编码'])
    orig_id_idx = pick(['orig_item_id', '原物资编码'])
    orig_name_idx = pick(['orig_item_name', '原物资名称'])
    orig_uom_idx = pick(['orig_item_uom', '原计量单位'])
    orig_cat_idx = pick(['orig_category', '原物资分类编码'])
    desc_idx = pick(['描述', 'desc', '错误'])
    desc_idx = pick(['描述', 'desc', '错误'])
    desc_idx = pick(['描述', 'desc', '错误'])
    desc_idx = pick(['描述', 'desc', '错误'])
    desc_idx = pick(['描述', 'desc', '错误'])
    desc_idx = pick(['描述', 'desc', '错误'])
    desc_idx = pick(['描述', 'desc', '错误'])
    desc_idx = pick(['描述', 'desc', '错误'])
    desc_idx = pick(['描述', 'desc', '错误'])
    desc_idx = pick(['描述', 'desc', '错误'])
    desc_idx = pick(['描述', 'desc', '错误'])
    desc_idx = pick(['描述', 'desc', '错误'])
    if lid_idx is None:
        raise ValueError("Excel 缺少必要列：明细行ID")
    records = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row:
            continue
        lid = row[lid_idx]
        if lid is None:
            continue
        rec = {'line_id': str(lid).strip()}
        if new_id_idx is not None:
            rec['new_item_id'] = normalize_item_id(row[new_id_idx])
        if new_name_idx is not None:
            rec['new_item_name'] = row[new_name_idx]
        if new_uom_idx is not None:
            rec['new_item_uom'] = row[new_uom_idx]
        if new_cat_idx is not None:
            rec['new_category'] = row[new_cat_idx]
        if orig_id_idx is not None:
            rec['orig_item_id'] = normalize_item_id(row[orig_id_idx])
        if orig_name_idx is not None:
            rec['orig_item_name'] = row[orig_name_idx]
        if orig_uom_idx is not None:
            rec['orig_item_uom'] = row[orig_uom_idx]
        if orig_cat_idx is not None:
            rec['orig_category'] = row[orig_cat_idx]
        if desc_idx is not None:
            rec['desc'] = row[desc_idx]
        records.append(rec)
    if not records:
        raise ValueError("Excel 中没有有效的行数据")
    return records


def generate_item_sql_bulk(records, ops_remark=None):
    cfg = get_config()
    sql = []
    sql.append("1、执行语句")
    if cfg.get('MERGE_MODULES', {}).get('item', True):
        def key_fn(r):
            return (
                str(r.get('new_item_id') or '').strip(),
                str(r.get('new_item_name') or '').strip(),
                str(r.get('new_item_uom') or '').strip(),
                str(r.get('new_category') or '').strip(),
            )
        groups = merge_by_key(records, key_fn)
        for k, recs in groups.items():
            if not any(k):
                continue
            set_parts = []
            if k[0]:
                set_parts.append(f"ITEM_ID = '{k[0]}'")
            if k[1]:
                set_parts.append(f"ITEM_NAME = '{k[1]}'")
            if k[2]:
                set_parts.append(f"ITEM_UOM = '{k[2]}'")
            if k[3]:
                set_parts.append(f"CATEGORY = '{k[3]}'")
            ids = [r['line_id'] for r in recs if r.get('line_id')]
            for chunk in chunk_list(ids, int(cfg.get('MERGE_MAX_IN_SIZE', 500))):
                inlist = format_in(chunk)
                stmt = (
                    "UPDATE TPHCT02 SET " + ", ".join(set_parts) + ", "
                    f"OPS_REMARK = '{ops_remark or ''}' WHERE BPO_LINE_ID IN (" +
                    inlist + ") AND ALIVE_FLAG = '1';"
                )
                sql.append(stmt)
    else:
        for r in records:
            parts = []
            if r.get('new_item_id'):
                parts.append(f"ITEM_ID = '{str(r['new_item_id']).strip()}'")
            if r.get('new_item_name'):
                parts.append(
                    f"ITEM_NAME = '{str(r['new_item_name']).strip()}'")
            if r.get('new_item_uom'):
                parts.append(f"ITEM_UOM = '{str(r['new_item_uom']).strip()}'")
            if r.get('new_category'):
                parts.append(f"CATEGORY = '{str(r['new_category']).strip()}'")
            if parts:
                stmt = (
                    "UPDATE TPHCT02 SET " + ", ".join(parts) + ", "
                    f"OPS_REMARK = '{ops_remark or ''}' WHERE BPO_LINE_ID = '{r['line_id']}' AND ALIVE_FLAG = '1';"
                )
                sql.append(stmt)


def org_import_view(request):
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
            from .models import ImportJob
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


def item_import_view(request):
    if request.method == 'POST':
        form = ItemImportForm(request.POST, request.FILES)
        if form.is_valid():
            f = form.cleaned_data['csv_file']
            batch_size = form.cleaned_data.get('batch_size') or 2000
            temp_dir = os.path.join(settings.BASE_DIR, 'temp_uploads')
            os.makedirs(temp_dir, exist_ok=True)
            tmp = tempfile.NamedTemporaryFile(
                delete=False, dir=temp_dir, suffix='.csv')
            tmp.write(f.read())
            tmp.close()
            from .models import ImportJob
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
                        required = {'item_id', 'item_name',
                                    'category', 'item_uom', 'purc_type'}
                        if not required.issubset(set([h.strip() for h in reader.fieldnames or []])):
                            raise ValueError(
                                'CSV列需包含：item_id, item_name, category, item_uom, purc_type')
                        buffer = []
                        created = 0
                        updated = 0
                        done = 0
                        ItemDetail.objects.all().delete()
                        for row in reader:
                            rid = (row.get('item_id') or '').strip()
                            if not rid:
                                continue
                            buffer.append({
                                'item_id': rid,
                                'item_name': (row.get('item_name') or '').strip(),
                                'category': (row.get('category') or '').strip(),
                                'item_uom': (row.get('item_uom') or '').strip(),
                                'purc_type': (row.get('purc_type') or '').strip(),
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
            'sidebar_groups': SIDEBAR_GROUPS,
        })
    else:
        form = ItemImportForm()
        return render(request, 'item_import.html', {
            'form': form,
            'active_menu': 'item_import',
            'sidebar_groups': SIDEBAR_GROUPS,
        })
    sql.append("")
    sql.append("2、回退语句")
    if cfg.get('MERGE_MODULES', {}).get('item', True):
        def rb_key(r):
            return (
                str(r.get('orig_item_id') or '').strip(),
                str(r.get('orig_item_name') or '').strip(),
                str(r.get('orig_item_uom') or '').strip(),
                str(r.get('orig_category') or '').strip(),
            )
        groups = merge_by_key(records, rb_key)
        for k, recs in groups.items():
            if not any(k):
                continue
            rb = []
            if k[0]:
                rb.append(f"ITEM_ID = '{k[0]}'")
            if k[1]:
                rb.append(f"ITEM_NAME = '{k[1]}'")
            if k[2]:
                rb.append(f"ITEM_UOM = '{k[2]}'")
            if k[3]:
                rb.append(f"CATEGORY = '{k[3]}'")
            ids = [r['line_id'] for r in recs if r.get('line_id')]
            for chunk in chunk_list(ids, int(cfg.get('MERGE_MAX_IN_SIZE', 500))):
                inlist = format_in(chunk)
                stmt = (
                    "UPDATE TPHCT02 SET " + ", ".join(rb) + ", "
                    f"OPS_REMARK = '' WHERE BPO_LINE_ID IN (" +
                                                            inlist + ") AND ALIVE_FLAG = '1';"
                )
                sql.append(stmt)
    else:
        for r in records:
            rb = []
            if r.get('orig_item_id'):
                rb.append(f"ITEM_ID = '{str(r['orig_item_id']).strip()}'")
            if r.get('orig_item_name'):
                rb.append(f"ITEM_NAME = '{str(r['orig_item_name']).strip()}'")
            if r.get('orig_item_uom'):
                rb.append(f"ITEM_UOM = '{str(r['orig_item_uom']).strip()}'")
            if r.get('orig_category'):
                rb.append(f"CATEGORY = '{str(r['orig_category']).strip()}'")
            if rb:
                stmt = (
                    "UPDATE TPHCT02 SET " + ", ".join(rb) + ", "
                    f"OPS_REMARK = '' WHERE BPO_LINE_ID = '{r['line_id']}' AND ALIVE_FLAG = '1';"
                )
                sql.append(stmt)
    sql.append("")
    sql.append("3、数据库")
    sql.append("ip：192.168.11.71")
    sql.append("库名：cnnc_ph")
    return "\n".join(sql)


def parse_erp_excel(file):
    wb = openpyxl.load_workbook(file)
    ws = wb.active
    headers = [cell.value for cell in ws[1]]
    idx = {str(h): i for i, h in enumerate(headers)}

    def pick(alts):
        for a in alts:
            if a in idx:
                return idx[a]
        return None
    inq_idx = pick(['INQ_ID', 'inq_id'])
    sch_idx = pick(['PURCHASE_SCHEME_NO', 'purchase_scheme_no'])
    pkg_idx = pick(['PURCHASE_PACKAGE_NO', 'purchase_package_no'])
    if inq_idx is None and sch_idx is None and pkg_idx is None:
        raise ValueError(
            "Excel 缺少必要列：INQ_ID或PURCHASE_SCHEME_NO或PURCHASE_PACKAGE_NO")
    records = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row:
            continue
        rec = {}
        if inq_idx is not None:
            v = row[inq_idx]
            rec['inq_id'] = v and str(v).strip() or None
        if sch_idx is not None:
            v = row[sch_idx]
            rec['purchase_scheme_no'] = v and str(v).strip() or None
        if pkg_idx is not None:
            v = row[pkg_idx]
            rec['purchase_package_no'] = v and str(v).strip() or None
        if rec.get('inq_id') or rec.get('purchase_scheme_no') or rec.get('purchase_package_no'):
            records.append(rec)
    if not records:
        raise ValueError("Excel 中没有有效的行数据")
    return records


def generate_erp_terminate_sql(records, ops_remark=None):
    cfg = get_config()
    sql = []
    sql.append("1、执行语句")
    remark = ops_remark or ''
    if cfg.get('MERGE_MODULES', {}).get('erp', True):
        inqs = [r.get('inq_id') for r in records if r.get('inq_id')]
        schs = [r.get('purchase_scheme_no')
                for r in records if r.get('purchase_scheme_no')]
        pkgs = [r.get('purchase_package_no')
                for r in records if r.get('purchase_package_no')]
        for chunk in chunk_list(inqs, int(cfg.get('MERGE_MAX_IN_SIZE', 500))):
            inlist = format_in(chunk)
            sql.append(
                f"update tprxj01 set INQ_STATUS='70', OPS_REMARK='{remark}' where INQ_ID in ({inlist});")
            sql.append(
                f"update tprxj06 set ALIVE_FLAG='0', OPS_REMARK='{remark}' where INQ_ID in ({inlist});")
        for chunk in chunk_list(schs, int(cfg.get('MERGE_MAX_IN_SIZE', 500))):
            sql.append(
                f"update tprfa01 set PURCHASE_SCHEME_STATUS='95', OPS_REMARK='{remark}' where PURCHASE_SCHEME_NO IN ({format_in(chunk)});")
        for chunk in chunk_list(pkgs, int(cfg.get('MERGE_MAX_IN_SIZE', 500))):
            inlist = format_in(chunk)
            sql.append(
                f"update tprly01 set status='60', OPS_REMARK='{remark}' where PURCHASE_PACKAGE_NO IN ({inlist});")
            sql.append(
                f"update tprly02 set status='60', OPS_REMARK='{remark}' where PURCHASE_PACKAGE_NO IN ({inlist});")
    else:
        for r in records:
            inq = r.get('inq_id')
            sch = r.get('purchase_scheme_no')
            pkg = r.get('purchase_package_no')
            if inq:
                sql.append(
                    f"update tprxj01 set INQ_STATUS='70', OPS_REMARK='{remark}' where INQ_ID in ('{inq}');")
                sql.append(
                    f"update tprxj06 set ALIVE_FLAG='0', OPS_REMARK='{remark}' where INQ_ID  in ('{inq}');")
            if sch:
                sql.append(
                    f"update tprfa01 set PURCHASE_SCHEME_STATUS='95', OPS_REMARK='{remark}' where PURCHASE_SCHEME_NO IN ('{sch}');")
            if pkg:
                sql.append(
                    f"update tprly01 set status='60', OPS_REMARK='{remark}' where PURCHASE_PACKAGE_NO IN ('{pkg}');")
                sql.append(
                    f"update tprly02 set status='60', OPS_REMARK='{remark}' where PURCHASE_PACKAGE_NO IN ('{pkg}');")
    sql.append("")
    sql.append("2、回退语句")
    if cfg.get('MERGE_MODULES', {}).get('erp', True):
        inqs = [r.get('inq_id') for r in records if r.get('inq_id')]
        schs = [r.get('purchase_scheme_no')
                for r in records if r.get('purchase_scheme_no')]
        pkgs = [r.get('purchase_package_no')
                for r in records if r.get('purchase_package_no')]
        for chunk in chunk_list(inqs, int(cfg.get('MERGE_MAX_IN_SIZE', 500))):
            inlist = format_in(chunk)
            sql.append(
                f"update tprxj01 set INQ_STATUS='55', OPS_REMARK='' where INQ_ID in ({inlist});")
            sql.append(
                f"update tprxj06 set ALIVE_FLAG='1', OPS_REMARK='' where INQ_ID in ({inlist});")
        for chunk in chunk_list(schs, int(cfg.get('MERGE_MAX_IN_SIZE', 500))):
            sql.append(
                f"update tprfa01 set PURCHASE_SCHEME_STATUS='55', OPS_REMARK='' where PURCHASE_SCHEME_NO IN ({format_in(chunk)});")
        for chunk in chunk_list(pkgs, int(cfg.get('MERGE_MAX_IN_SIZE', 500))):
            inlist = format_in(chunk)
            sql.append(
                f"update tprly01 set status='75', OPS_REMARK='' where PURCHASE_PACKAGE_NO IN ({inlist});")
            sql.append(
                f"update tprly02 set status='75', OPS_REMARK='' where PURCHASE_PACKAGE_NO IN ({inlist});")
    else:
        for r in records:
            inq = r.get('inq_id')
            sch = r.get('purchase_scheme_no')
            pkg = r.get('purchase_package_no')
            if inq:
                sql.append(
                    f"update tprxj01 set INQ_STATUS='55', OPS_REMARK='' where INQ_ID in ('{inq}');")
                sql.append(
                    f"update tprxj06 set ALIVE_FLAG='1', OPS_REMARK='' where INQ_ID in ('{inq}');")
            if sch:
                sql.append(
                    f"update tprfa01 set PURCHASE_SCHEME_STATUS='55', OPS_REMARK='' where PURCHASE_SCHEME_NO IN ('{sch}');")
            if pkg:
                sql.append(
                    f"update tprly01 set status='75', OPS_REMARK='' where PURCHASE_PACKAGE_NO IN ('{pkg}');")
                sql.append(
                    f"update tprly02 set status='75', OPS_REMARK='' where PURCHASE_PACKAGE_NO IN ('{pkg}');")
    sql.append("")
    sql.append("ip：192.168.11.69")
    sql.append("库名：cnnc_pr")
    return "\n".join(sql)


def erp_terminate_view(request):
    if request.method == 'POST':
        form = ErpTerminateForm(request.POST, request.FILES)
        if form.is_valid():
            cd = form.cleaned_data
            ops_remark = parse_ops_remark(cd.get('ops_remark', ''))
            if cd.get('excel_file'):
                records = parse_erp_excel(cd['excel_file'])
            else:
                rec = {
                    'inq_id': (cd.get('inq_id') or '').strip() or None,
                    'purchase_scheme_no': (cd.get('purchase_scheme_no') or '').strip() or None,
                    'purchase_package_no': (cd.get('purchase_package_no') or '').strip() or None,
                }
                records = [rec]
            sql_content = generate_erp_terminate_sql(records, ops_remark)
            now = datetime.now()
            year_month = now.strftime("%Y%m")
            day = now.strftime("%d")
            filename = f"{cd['dynamic_id']}_核电ERP终止.sql"
            base_dir = r"D:\临时文件"
            target_dir = os.path.join(base_dir, year_month, day)
            os.makedirs(target_dir, exist_ok=True)
            filepath = os.path.join(target_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(sql_content)

            # 记录文件保存
            logger.info(f"SQL文件已保存: {filepath}")
            temp_dir = os.path.join(settings.BASE_DIR, 'temp_downloads')
            os.makedirs(temp_dir, exist_ok=True)
            download_path = os.path.join(temp_dir, filename)
            with open(download_path, 'w', encoding='utf-8') as f:
                f.write(sql_content)
            session_data = {}
            for k, v in cd.items():
                if k != 'excel_file':
                    if hasattr(v, 'to_eng_string'):
                        session_data[k] = v.to_eng_string()
                    else:
                        session_data[k] = v
            request.session['erp_terminate_last'] = session_data
            return render(request, 'success.html', {
                'filepath': filepath,
                'download_url': f"/download/{filename}",
                'active_menu': 'erp_terminate',
                'sidebar_groups': SIDEBAR_GROUPS,
            })
    else:
        if request.GET.get('clear'):
            request.session.pop('erp_terminate_last', None)
            form = ErpTerminateForm()
        else:
            initial = request.session.get('erp_terminate_last')
            form = ErpTerminateForm(initial=initial)
    return render(request, 'erp_terminate_form.html', {
        'form': form,
        'active_menu': 'erp_terminate',
        'sidebar_groups': SIDEBAR_GROUPS,
    })


def download_erp_terminate_template(request):
    if not OPENPYXL_AVAILABLE:
        return HttpResponse("缺少 openpyxl，请安装后使用模板下载：pip install openpyxl", status=500)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = '模板'
    ws.append(['INQ_ID', 'PURCHASE_SCHEME_NO', 'PURCHASE_PACKAGE_NO'])
    ws.append(['CNSC-XJD-25-03203', 'YW01-CGFA-25-02641', 'YW01-CGB-25-02749'])
    bio = io.BytesIO()
    wb.save(bio)
    bio.seek(0)
    response = FileResponse(bio, as_attachment=True,
                            filename='erp_terminate_template.xlsx')
    response['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    return response


def contract_item_update_view(request):
    if request.method == 'POST':
        form = ContractItemUpdateForm(request.POST, request.FILES)
        if form.is_valid():
            cd = form.cleaned_data
            ops_remark = parse_ops_remark(cd.get('ops_remark', ''))
            if cd.get('excel_file'):
                records = parse_item_excel(cd['excel_file'])
                success_records = []
                fail_rows = []
                for r in records:
                    nid = normalize_item_id(r.get('new_item_id'))
                    r['new_item_id'] = nid
                    if not nid:
                        fail_rows.append({**r, 'error': '物资编码为空'})
                        continue
                    obj = ItemDetail.objects.filter(item_id=nid).first()
                    if obj:
                        r['new_item_name'] = r.get(
                            'new_item_name') or obj.item_name
                        r['new_item_uom'] = r.get(
                            'new_item_uom') or obj.item_uom
                        r['new_category'] = r.get(
                            'new_category') or obj.category
                        success_records.append(r)
                    else:
                        fail_rows.append({**r, 'error': f"物资编码不存在: {nid}"})
                sql_content = generate_item_sql_bulk(
                    success_records, ops_remark)
                now = datetime.now()
                year_month = now.strftime("%Y%m")
                day = now.strftime("%d")
                filename = f"{cd['dynamic_id']}_修改合同物资编码.sql"
                base_dir = r"D:\临时文件"
                target_dir = os.path.join(base_dir, year_month, day)
                os.makedirs(target_dir, exist_ok=True)
                filepath = os.path.join(target_dir, filename)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(sql_content)
                temp_dir = os.path.join(settings.BASE_DIR, 'temp_downloads')
                os.makedirs(temp_dir, exist_ok=True)
                download_path = os.path.join(temp_dir, filename)
                with open(download_path, 'w', encoding='utf-8') as f:
                    f.write(sql_content)
                fail_download_url = None
                if fail_rows:
                    wb = openpyxl.Workbook()
                    ws = wb.active
                    ws.title = '失败明细'
                    ws.append(['明细行ID', '物资编码', '物资名称',
                              '计量单位', '物资分类编码', '描述'])
                    for r in fail_rows:
                        ws.append([
                            r.get('line_id'),
                            r.get('new_item_id'),
                            r.get('new_item_name'),
                            r.get('new_item_uom'),
                            r.get('new_category'),
                            r.get('error')
                        ])
                    fail_name = f"{cd['dynamic_id']}_修改合同物资编码_失败.xlsx"
                    fail_path = os.path.join(temp_dir, fail_name)
                    wb.save(fail_path)
                    fail_download_url = f"/download/{fail_name}"
                session_data = {}
                for k, v in cd.items():
                    if k != 'excel_file':
                        if hasattr(v, 'to_eng_string'):
                            session_data[k] = v.to_eng_string()
                        else:
                            session_data[k] = v
                request.session['contract_item_last'] = session_data
                return render(request, 'success.html', {
                    'filepath': filepath,
                    'download_url': f"/download/{filename}",
                    'fail_download_url': fail_download_url,
                    'active_menu': 'contract_item',
                    'sidebar_groups': SIDEBAR_GROUPS,
                })
            else:
                rec = {
                    'line_id': cd['single_line_id'],
                    'new_item_id': cd.get('new_item_id'),
                    'new_item_name': cd.get('new_item_name'),
                    'new_item_uom': cd.get('new_item_uom'),
                    'new_category': cd.get('new_category'),
                    'orig_item_id': cd.get('orig_item_id'),
                    'orig_item_name': cd.get('orig_item_name'),
                    'orig_item_uom': cd.get('orig_item_uom'),
                    'orig_category': cd.get('orig_category'),
                }
                records = [rec]
                sql_content = generate_item_sql_bulk(records, ops_remark)
                now = datetime.now()
                year_month = now.strftime("%Y%m")
                day = now.strftime("%d")
                filename = f"{cd['dynamic_id']}_修改合同物资编码.sql"
                base_dir = r"D:\临时文件"
                target_dir = os.path.join(base_dir, year_month, day)
                os.makedirs(target_dir, exist_ok=True)
                filepath = os.path.join(target_dir, filename)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(sql_content)
                temp_dir = os.path.join(settings.BASE_DIR, 'temp_downloads')
                os.makedirs(temp_dir, exist_ok=True)
                download_path = os.path.join(temp_dir, filename)
                with open(download_path, 'w', encoding='utf-8') as f:
                    f.write(sql_content)
                session_data = {}
                for k, v in cd.items():
                    if k != 'excel_file':
                        if hasattr(v, 'to_eng_string'):
                            session_data[k] = v.to_eng_string()
                        else:
                            session_data[k] = v
                request.session['contract_item_last'] = session_data
                return render(request, 'success.html', {
                    'filepath': filepath,
                    'download_url': f"/download/{filename}",
                    'active_menu': 'contract_item',
                    'sidebar_groups': SIDEBAR_GROUPS,
                })
    else:
        if request.GET.get('clear'):
            request.session.pop('contract_item_last', None)
            form = ContractItemUpdateForm()
        else:
            initial = request.session.get('contract_item_last')
            form = ContractItemUpdateForm(initial=initial)
    return render(request, 'contract_item_form.html', {
        'form': form,
        'active_menu': 'contract_item',
        'sidebar_groups': SIDEBAR_GROUPS,
    })


def download_item_template(request):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = '模板'
    ws.append(['明细行ID', '物资编码', '物资名称', '计量单位', '物资分类编码',
              '原物资编码', '原物资名称', '原计量单位', '原物资分类编码', '描述'])
    ws.append(['BPO-EXAMPLE-000001', '01607733', '鞋套',
              '双', '430798', None, None, None, None, None])
    bio = io.BytesIO()
    wb.save(bio)
    bio.seek(0)
    response = FileResponse(bio, as_attachment=True,
                            filename='contract_item_template.xlsx')
    response['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    return response


def parse_budget_excel(file):
    if not OPENPYXL_AVAILABLE:
        raise ValueError("缺少 openpyxl，无法解析 Excel")
    wb = openpyxl.load_workbook(file)
    ws = wb.active
    headers = [cell.value for cell in ws[1]]
    idx = {str(h): i for i, h in enumerate(headers)}

    def pick(alts):
        for a in alts:
            if a in idx:
                return idx[a]
        return None
    bpo_idx = pick(['BPO_ID', 'bpo_id', '合同号'])
    sec_idx = pick(['SECTION_NO', 'section_no', '标段编号'])
    new_idx = pick(['BUDGET_PRICE', 'new_budget', '预算单价', '新预算'])
    orig_idx = pick(['orig_budget', '原预算', '原预算单价'])
    if (sec_idx is None and bpo_idx is None) or new_idx is None:
        raise ValueError("Excel 缺少必要列：标段编号或合同号，以及新预算")
    records = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row:
            continue
        sec = row[sec_idx] if sec_idx is not None else None
        newv = row[new_idx]
        if ((sec is None) and (bpo_idx is None or row[bpo_idx] is None)) or newv is None:
            continue
        rec = {
            'new_budget': str(newv).strip(),
        }
        if sec is not None:
            rec['section_no'] = str(sec).strip()
        if bpo_idx is not None and row[bpo_idx] is not None:
            rec['contract_bpo_id'] = str(row[bpo_idx]).strip()
        if orig_idx is not None and row[orig_idx] is not None:
            rec['orig_budget'] = str(row[orig_idx]).strip()
        records.append(rec)
    if not records:
        raise ValueError("Excel 中没有有效的行数据")
    return records


def generate_budget_sql_bulk(records, ops_remark=None):
    sql = []
    sql.append("1、执行语句")
    part_exec = []
    contract_exec = []
    for r in records:
        if r.get('section_no') and r.get('new_budget') is not None:
            cond = f"SECTION_NO='{r['section_no']}' and ALIVE_FLAG='1'"
            if r.get('supplier_id'):
                cond += f" AND SUPPLIER_ID='{r['supplier_id']}'"
            part_exec.append(
                f"update tprxj07 set BUDGET_PRICE='{r['new_budget']}', OPS_REMARK='{ops_remark or ''}' where {cond};"
            )
            part_exec.append(
                f"update tprxj10 set BUDGET_PRICE='{r['new_budget']}', OPS_REMARK='{ops_remark or ''}' where {cond};"
            )
            part_exec.append(
                f"update tprnq02 set BUDGET_PRICE='{r['new_budget']}', OPS_REMARK='{ops_remark or ''}' where {cond};"
            )
        if r.get('contract_bpo_id') and r.get('new_budget') is not None:
            contract_exec.append(
                f"update TPHCT01 set BUDGETED_AMOUNT='{r['new_budget']}', OPS_REMARK='{ops_remark or ''}' WHERE bpo_id='{r['contract_bpo_id']}' and ALIVE_FLAG='1';"
            )
    if part_exec:
        sql.append("-- PR 明细：tprxj07 / tprxj10 / tprnq02")
        sql.extend(part_exec)
    if contract_exec:
        sql.append("-- PH 主表：修改合同预算 TPHCT01")
        sql.extend(contract_exec)
    sql.append("")
    sql.append("2、回退语句")
    part_rb = []
    contract_rb = []
    for r in records:
        if r.get('orig_budget') is None:
            continue
        if r.get('section_no'):
            cond_rb = f"SECTION_NO='{r['section_no']}' and ALIVE_FLAG='1'"
            if r.get('supplier_id'):
                cond_rb += f" AND SUPPLIER_ID='{r['supplier_id']}'"
            part_rb.append(
                f"update tprxj07 set BUDGET_PRICE='{r['orig_budget']}', OPS_REMARK='' where {cond_rb};"
            )
            part_rb.append(
                f"update tprxj10 set BUDGET_PRICE='{r['orig_budget']}', OPS_REMARK='' where {cond_rb};"
            )
            part_rb.append(
                f"update tprnq02 set BUDGET_PRICE='{r['orig_budget']}', OPS_REMARK='' where {cond_rb};"
            )
        if r.get('contract_bpo_id'):
            contract_rb.append(
                f"update TPHCT01 set BUDGETED_AMOUNT='{r['orig_budget']}', OPS_REMARK='' WHERE bpo_id='{r['contract_bpo_id']}' and ALIVE_FLAG='1';"
            )
    if part_rb:
        sql.append("-- PR 回退：tprxj07 / tprxj10 / tprnq02")
        sql.extend(part_rb)
    if contract_rb:
        sql.append("-- PH 回退：修改合同预算 TPHCT01")
        sql.extend(contract_rb)
    sql.append("")
    sql.append("3、数据库")
    sql.append("ip:192.168.11.69")
    sql.append("库名：cnnc_pr")
    sql.append("")
    sql.append("ip:192.168.11.71")
    sql.append("库名：cnnc_ph")
    return "\n".join(sql)


def contract_budget_update_view(request):
    if request.method == 'POST':
        form = ContractBudgetUpdateForm(request.POST, request.FILES)
        if form.is_valid():
            cd = form.cleaned_data
            ops_remark = parse_ops_remark(cd.get('ops_remark', ''))
            if cd.get('excel_file'):
                records = parse_budget_excel(cd['excel_file'])
            else:
                rec = {
                    'contract_bpo_id': cd.get('contract_bpo_id'),
                    'section_no': cd.get('section_no'),
                    'supplier_id': cd.get('supplier_id'),
                    'new_budget': cd.get('new_budget'),
                    'orig_budget': cd.get('orig_budget'),
                }
                records = [rec]
            sql_content = generate_budget_sql_bulk(records, ops_remark)
            now = datetime.now()
            year_month = now.strftime("%Y%m")
            day = now.strftime("%d")
            filename = f"{cd['dynamic_id']}_修改合同预算.sql"
            base_dir = r"D:\临时文件"
            target_dir = os.path.join(base_dir, year_month, day)
            os.makedirs(target_dir, exist_ok=True)
            filepath = os.path.join(target_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(sql_content)

            # 记录文件保存
            logger.info(f"SQL文件已保存: {filepath}")
            temp_dir = os.path.join(settings.BASE_DIR, 'temp_downloads')
            os.makedirs(temp_dir, exist_ok=True)
            download_path = os.path.join(temp_dir, filename)
            with open(download_path, 'w', encoding='utf-8') as f:
                f.write(sql_content)
            session_data = {}
            for k, v in cd.items():
                if k != 'excel_file':
                    if hasattr(v, 'to_eng_string'):
                        session_data[k] = v.to_eng_string()
                    else:
                        session_data[k] = v
            request.session['contract_budget_last'] = session_data
            return render(request, 'success.html', {
                'filepath': filepath,
                'download_url': f"/download/{filename}",
                'active_menu': 'contract_budget',
                'sidebar_groups': SIDEBAR_GROUPS,
            })
    else:
        if request.GET.get('clear'):
            request.session.pop('contract_budget_last', None)
            form = ContractBudgetUpdateForm()
        else:
            initial = request.session.get('contract_budget_last')
            form = ContractBudgetUpdateForm(initial=initial)
    return render(request, 'contract_budget_form.html', {
        'form': form,
        'active_menu': 'contract_budget',
        'sidebar_groups': SIDEBAR_GROUPS,
    })


def download_budget_template(request):
    if not OPENPYXL_AVAILABLE:
        return HttpResponse("缺少 openpyxl，请安装后使用模板下载：pip install openpyxl", status=500)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = '模板'
    ws.append(['合同号', '标段编号', '供应商ID(可选)', '新预算', '原预算'])
    ws.append(['BTRL-25-00046', 'YZN0-XJD-25-03316',
              'G00361071', '6100', '4881'])
    bio = io.BytesIO()
    wb.save(bio)
    bio.seek(0)
    response = FileResponse(bio, as_attachment=True,
                            filename='contract_budget_template.xlsx')
    response['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    return response


def download_price_template(request):
    if not OPENPYXL_AVAILABLE:
        return HttpResponse("缺少 openpyxl，请安装后使用模板下载：pip install openpyxl", status=500)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = '模板'
    ws.append(['明细行ID', '单价', '数量', '原数量', '原单价'])
    ws.append(['BPO-EXAMPLE-000001', 100, 1, None, None])
    bio = io.BytesIO()
    wb.save(bio)
    bio.seek(0)
    response = FileResponse(bio, as_attachment=True,
                            filename='contract_price_template.xlsx')
    response['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    return response


def contract_detail_price_view(request):
    """
    处理合同明细单价修改的视图函数
    """
    if request.method == 'POST':
        form = ContractDetailPriceForm(request.POST, request.FILES)
        if form.is_valid():
            cd = form.cleaned_data
            log_view_input("合同明细单价修改", cd)

            # 解析OPS_REMARK
            ops_remark = parse_ops_remark(cd.get('ops_remark', ''))

            if cd.get('excel_file'):
                records = parse_price_excel(cd['excel_file'])
                sql_content = generate_price_sql_bulk(records, ops_remark)
            else:
                new_quantity = cd.get('new_quantity')
                new_price = cd.get('new_price')
                orig_quantity = cd.get('orig_quantity')
                orig_price = cd.get('orig_price')
                if not new_price or not cd.get('single_line_id'):
                    form.add_error(None, "单条模式需填写单价和明细行ID；数量可不填")
                    return render(request, 'contract_price_form.html', {
                        'form': form,
                        'active_menu': 'contract_price',
                        'sidebar_groups': SIDEBAR_GROUPS,
                    })
                line_ids = [cd['single_line_id']]
                sql_content = generate_price_sql(
                    line_ids, new_quantity, new_price, orig_quantity, orig_price, ops_remark)

            # 生成文件名
            now = datetime.now()
            year_month = now.strftime("%Y%m")
            day = now.strftime("%d")
            filename = f"{cd['dynamic_id']}_修改合同明细单价.sql"

            # 保存到临时文件
            base_dir = r"D:\临时文件"
            target_dir = os.path.join(base_dir, year_month, day)
            os.makedirs(target_dir, exist_ok=True)
            filepath = os.path.join(target_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(sql_content)

            # 记录文件保存
            logger.info(f"SQL文件已保存: {filepath}")

            # 保存到下载目录
            temp_dir = os.path.join(settings.BASE_DIR, 'temp_downloads')
            os.makedirs(temp_dir, exist_ok=True)
            download_path = os.path.join(temp_dir, filename)
            with open(download_path, 'w', encoding='utf-8') as f:
                f.write(sql_content)

            # 将Decimal类型转换为字符串以支持JSON序列化
            session_data = {}
            for k, v in cd.items():
                if k != 'excel_file':
                    # 处理Decimal类型
                    if hasattr(v, 'to_eng_string'):
                        session_data[k] = v.to_eng_string()
                    else:
                        session_data[k] = v
            request.session['contract_price_last'] = session_data
            return render(request, 'success.html', {
                'filepath': filepath,
                'download_url': f'/download/{filename}',
                'supplement_download_url': supplement_download_url
            })
    else:
        if request.GET.get('clear'):
            request.session.pop('contract_price_last', None)
            form = ContractDetailPriceForm()
        else:
            initial = request.session.get('contract_price_last')
            form = ContractDetailPriceForm(initial=initial)

    return render(request, 'contract_price_form.html', {'form': form})


def download_unit_template(request):
    if not OPENPYXL_AVAILABLE:
        return HttpResponse("缺少 openpyxl，请安装后使用模板下载：pip install openpyxl", status=500)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = '模板'
    ws.append(['采购方案编号', '询价单编号', '定标结果编号', '新起草单位ID', '新起草单位名称',
              '新签约主体ID', '新签约主体名称', '原起草单位ID', '原起草单位名称', '原签约主体ID', '原签约主体名称'])
    ws.append(['CNEC-EXAMPLE-001', 'XJD-EXAMPLE-001', '1',
              None, None, None, None, None, None, None, None])
    bio = io.BytesIO()
    wb.save(bio)
    bio.seek(0)
    response = FileResponse(bio, as_attachment=True,
                            filename='unit_change_template.xlsx')
    response['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    return response


def generate_sql(records, **kwargs):
    update_drafting = kwargs.get('update_drafting', False)
    update_contract_party = kwargs.get('update_contract_party', False)
    old_drafting_id = kwargs.get('old_drafting_id')
    old_drafting_name = kwargs.get('old_drafting_name')
    old_party_id = kwargs.get('old_party_id')
    old_party_name = kwargs.get('old_party_name')

    # 获取并解析ops_remark
    ops_remark = parse_ops_remark(kwargs.get('ops_remark', ''))

    sql = []
    sql.append("1、执行语句")
    for r in records:
        parts = []
        if update_drafting:
            ndid = r.get('new_drafting_id', kwargs.get('new_drafting_id'))
            ndnm = r.get('new_drafting_name', kwargs.get('new_drafting_name'))
            if not ndid and ndnm:
                code = extract_company_code(ndnm)
                if code:
                    ndid = code
            if ndid:
                parts.append(f"PRIMARY_CONTRACT_DRAFTING_UNIT='{ndid}'")
            if ndnm:
                parts.append(
                    f"PRIMARY_CONTRACT_DRAFTING_UNIT_NAME='{extract_company_name(ndnm)}'")
        if update_contract_party:
            npid = r.get('new_party_id', kwargs.get('new_party_id'))
            npnm = r.get('new_party_name', kwargs.get('new_party_name'))
            if not npid and npnm:
                code = extract_company_code(npnm)
                if code:
                    npid = code
            if npid:
                parts.append(f"CONTRACT_PARTY_ID='{npid}'")
            if npnm:
                parts.append(
                    f"CONTRACT_PARTY_NAME='{extract_company_name(npnm)}'")
        if parts:
            set_clause = ', '.join(parts)
            sql.append(
                f"update tprfa03 set {set_clause}, OPS_REMARK='{ops_remark}' where PURCHASE_SCHEME_NO='{r['scheme']}';")
            sql.append(
                f"update tprxj05 set {set_clause}, OPS_REMARK='{ops_remark}' where PURCHASE_SCHEME_NO='{r['scheme']}' AND INQ_ID='{r['inquiry']}';")
            sql.append(
                f"update tprnq03 set {set_clause}, OPS_REMARK='{ops_remark}' where PURCHASE_SCHEME_NO='{r['scheme']}' AND INQ_ID='{r['inquiry']}' AND sign_id='{r['result']}';")

    sql.append("2.回退语句")
    for r in records:
        rb_parts = []
        if update_drafting:
            odid = r.get('orig_drafting_id', old_drafting_id)
            odnm = r.get('orig_drafting_name', old_drafting_name)
            if not odid and odnm:
                code = extract_company_code(odnm)
                if code:
                    odid = code
            if odid:
                rb_parts.append(f"PRIMARY_CONTRACT_DRAFTING_UNIT='{odid}'")
            if odnm:
                rb_parts.append(
                    f"PRIMARY_CONTRACT_DRAFTING_UNIT_NAME='{extract_company_name(odnm)}'")
        if update_contract_party:
            opid = r.get('orig_party_id', old_party_id)
            opnm = r.get('orig_party_name', old_party_name)
            if not opid and opnm:
                code = extract_company_code(opnm)
                if code:
                    opid = code
            if opid:
                rb_parts.append(f"CONTRACT_PARTY_ID='{opid}'")
            if opnm:
                rb_parts.append(
                    f"CONTRACT_PARTY_NAME='{extract_company_name(opnm)}'")
        if rb_parts:
            rb_clause = ', '.join(rb_parts)
            sql.append(
                f"update tprfa03 set {rb_clause}, OPS_REMARK='' where PURCHASE_SCHEME_NO='{r['scheme']}';")
            sql.append(
                f"update tprxj05 set {rb_clause}, OPS_REMARK='' where PURCHASE_SCHEME_NO='{r['scheme']}' AND INQ_ID='{r['inquiry']}';")
            sql.append(
                f"update tprnq03 set {rb_clause}, OPS_REMARK='' where PURCHASE_SCHEME_NO='{r['scheme']}' AND INQ_ID='{r['inquiry']}' AND sign_id='{r['result']}';")

    sql.append("3.数据库")
    sql.append("ip：192.168.11.76")
    sql.append("库名：cnnc_ph")
    return "\n".join(sql)


def parse_excel(file):
    wb = openpyxl.load_workbook(file)
    ws = wb.active
    records = []
    headers = [cell.value for cell in ws[1]]
    hset = {str(h) if h is not None else '' for h in headers}
    idx = {str(h): i for i, h in enumerate(headers)}
    scheme_alts = ['scheme_no', 'PURCHASE_SCHEME_NO',
                   'purchase_scheme_no', '采购方案编号']
    inquiry_alts = ['inquiry_no', 'inq_id', 'INQ_ID', '询价单编号']
    result_alts = ['result_no', 'sign_id', 'SIGN_ID', '定标结果编号']

    def pick(alts):
        for a in alts:
            if a in idx:
                return idx[a]
        return None
    s_idx = pick(scheme_alts)
    i_idx = pick(inquiry_alts)
    r_idx = pick(result_alts)
    if s_idx is None or i_idx is None or r_idx is None:
        raise ValueError("Excel 缺少必要列：方案、询价、定标")
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not any(row):
            continue
        rec = {
            'scheme': row[s_idx],
            'inquiry': row[i_idx],
            'result': row[r_idx]
        }
        if not all(rec.values()):
            continue
        ndid = None
        ndnm = None
        npid = None
        npnm = None
        odid = None
        odnm = None
        opid = None
        opnm = None
        for k in ['new_drafting_id', '新起草单位ID']:
            if k in idx:
                ndid = row[idx[k]]
                break
        for k in ['new_drafting_name', '新起草单位名称', '组织机构名称']:
            if k in idx:
                ndnm = row[idx[k]]
                break
        for k in ['new_party_id', '新签约主体ID']:
            if k in idx:
                npid = row[idx[k]]
                break
        for k in ['new_party_name', '新签约主体名称']:
            if k in idx:
                npnm = row[idx[k]]
                break
        for k in ['orig_drafting_id', '原起草单位ID']:
            if k in idx:
                odid = row[idx[k]]
                break
        for k in ['orig_drafting_name', '原起草单位名称', '组织机构名称']:
            if k in idx:
                odnm = row[idx[k]]
                break
        for k in ['orig_party_id', '原签约主体ID']:
            if k in idx:
                opid = row[idx[k]]
                break
        for k in ['orig_party_name', '原签约主体名称']:
            if k in idx:
                opnm = row[idx[k]]
                break
        if ndid is not None:
            rec['new_drafting_id'] = ndid
        if ndnm is not None:
            rec['new_drafting_name'] = ndnm
        if npid is not None:
            rec['new_party_id'] = npid
        if npnm is not None:
            rec['new_party_name'] = npnm
        if odid is not None:
            rec['orig_drafting_id'] = odid
        if odnm is not None:
            rec['orig_drafting_name'] = odnm
        if opid is not None:
            rec['orig_party_id'] = opid
        if opnm is not None:
            rec['orig_party_name'] = opnm
        records.append(rec)
    return records


def unit_change_view(request):
    if request.method == 'POST':
        form = UnitChangeForm(request.POST, request.FILES)
        if form.is_valid():
            cd = form.cleaned_data

            if cd.get('excel_file'):
                records = parse_excel(cd['excel_file'])
                will_update_drafting = any(r.get('new_drafting_id') or r.get(
                    'new_drafting_name') for r in records)
                will_update_party = any(r.get('new_party_id') or r.get(
                    'new_party_name') for r in records)
                enriched = []
                fail_rows = []
                for r in records:
                    # 通过名称补齐编码
                    for k_name, k_id in [
                        ('new_drafting_name', 'new_drafting_id'),
                        ('orig_drafting_name', 'orig_drafting_id'),
                        ('new_party_name', 'new_party_id'),
                        ('orig_party_name', 'orig_party_id')
                    ]:
                        if r.get(k_name) and not r.get(k_id):
                            code = extract_company_code(str(r[k_name]))
                            if code:
                                r[k_id] = code
                            else:
                                uc = _unique_code_by_name(str(r[k_name]))
                                if uc:
                                    r[k_id] = uc
                    # 判定本行是否能生成更新/回退
                    parts = []
                    if will_update_drafting:
                        ndid = r.get('new_drafting_id')
                        ndnm = r.get('new_drafting_name')
                        if ndid:
                            parts.append('PRIMARY_CONTRACT_DRAFTING_UNIT')
                        if ndnm:
                            parts.append('PRIMARY_CONTRACT_DRAFTING_UNIT_NAME')
                    if will_update_party:
                        npid = r.get('new_party_id')
                        npnm = r.get('new_party_name')
                        if npid:
                            parts.append('CONTRACT_PARTY_ID')
                        if npnm:
                            parts.append('CONTRACT_PARTY_NAME')
                    rb_parts = []
                    if will_update_drafting:
                        if r.get('orig_drafting_id'):
                            rb_parts.append('PRIMARY_CONTRACT_DRAFTING_UNIT')
                        if r.get('orig_drafting_name'):
                            rb_parts.append(
                                'PRIMARY_CONTRACT_DRAFTING_UNIT_NAME')
                    if will_update_party:
                        if r.get('orig_party_id'):
                            rb_parts.append('CONTRACT_PARTY_ID')
                        if r.get('orig_party_name'):
                            rb_parts.append('CONTRACT_PARTY_NAME')
                    desc = []
                    if not parts:
                        desc.append('未提供可更新字段')
                    if will_update_drafting and not (r.get('orig_drafting_id') or r.get('orig_drafting_name')):
                        desc.append('缺少起草单位回退字段')
                    if will_update_party and not (r.get('orig_party_id') or r.get('orig_party_name')):
                        desc.append('缺少签约主体回退字段')
                    if desc:
                        fail_rows.append({
                            'scheme': r.get('scheme'),
                            'inquiry': r.get('inquiry'),
                            'result': r.get('result'),
                            'new_drafting_name': r.get('new_drafting_name'),
                            'new_drafting_id': r.get('new_drafting_id'),
                            'orig_drafting_name': r.get('orig_drafting_name'),
                            'orig_drafting_id': r.get('orig_drafting_id'),
                            'new_party_name': r.get('new_party_name'),
                            'new_party_id': r.get('new_party_id'),
                            'orig_party_name': r.get('orig_party_name'),
                            'orig_party_id': r.get('orig_party_id'),
                            'desc': '; '.join(desc)
                        })
                    enriched.append(r)
                records = enriched
            else:
                records = [{
                    'scheme': cd['scheme_no'],
                    'inquiry': cd['inquiry_no'],
                    'result': cd['result_no']
                }]

            if cd.get('excel_file'):
                update_drafting = any(r.get('new_drafting_id') or r.get(
                    'new_drafting_name') for r in records)
                update_contract_party = any(r.get('new_party_id') or r.get(
                    'new_party_name') for r in records)
            else:
                update_drafting = bool(
                    cd.get('new_drafting_id') or cd.get('new_drafting_name'))
                update_contract_party = bool(
                    cd.get('new_party_id') or cd.get('new_party_name'))

            # 解析OPS_REMARK
            ops_remark = parse_ops_remark(cd.get('ops_remark', ''))

            sql_content = generate_sql(
                records,
                update_drafting=update_drafting,
                update_contract_party=update_contract_party,
                old_drafting_id=cd.get('old_drafting_id'),
                old_drafting_name=cd.get('old_drafting_name'),
                new_drafting_id=cd.get('new_drafting_id'),
                new_drafting_name=cd.get('new_drafting_name'),
                old_party_id=cd.get('old_party_id'),
                old_party_name=cd.get('old_party_name'),
                new_party_id=cd.get('new_party_id'),
                new_party_name=cd.get('new_party_name'),
                ops_remark=ops_remark
            )

            # 记录SQL生成结果
            logger.info(
                f"SQL生成完成: 更新起草单位={update_drafting}, 更新签约主体={update_contract_party}, SQL长度={len(sql_content)}")

            now = datetime.now()
            year_month = now.strftime("%Y%m")
            day = now.strftime("%d")
            if update_drafting and update_contract_party:
                suffix = "修改起草单位和签约主体"
            elif update_drafting:
                suffix = "修改起草单位"
            elif update_contract_party:
                suffix = "修改签约主体"
            else:
                suffix = "修改合同单位信息"
            filename = f"{cd['dynamic_id']}_{suffix}.sql"

            base_dir = r"D:\临时文件"
            target_dir = os.path.join(base_dir, year_month, day)
            os.makedirs(target_dir, exist_ok=True)
            filepath = os.path.join(target_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(sql_content)

            # 记录文件保存
            logger.info(f"SQL文件已保存: {filepath}")

            temp_dir = os.path.join(settings.BASE_DIR, 'temp_downloads')
            os.makedirs(temp_dir, exist_ok=True)
            download_path = os.path.join(temp_dir, filename)
            with open(download_path, 'w', encoding='utf-8') as f:
                f.write(sql_content)
            fail_download_url = None
            if cd.get('excel_file') and 'fail_rows' in locals() and fail_rows:
                wb = openpyxl.Workbook()
                ws = wb.active
                ws.title = '失败明细'
                ws.append(['采购方案编号', '询价单编号', '定标结果编号', '新起草单位名称', '新起草单位ID', '原起草单位名称',
                          '原起草单位ID', '新签约主体名称', '新签约主体ID', '原签约主体名称', '原签约主体ID', '描述'])
                for r in fail_rows:
                    ws.append([
                        r.get('scheme'), r.get('inquiry'), r.get('result'),
                        r.get('new_drafting_name'), r.get('new_drafting_id'),
                        r.get('orig_drafting_name'), r.get('orig_drafting_id'),
                        r.get('new_party_name'), r.get('new_party_id'),
                        r.get('orig_party_name'), r.get('orig_party_id'),
                        r.get('desc')
                    ])
                fail_name = f"{cd['dynamic_id']}_单位信息修改_失败.xlsx"
                fail_path = os.path.join(temp_dir, fail_name)
                wb.save(fail_path)
                fail_download_url = f"/download/{fail_name}"

            # 将Decimal类型转换为字符串以支持JSON序列化
            session_data = {}
            for k, v in cd.items():
                if k != 'excel_file':
                    # 处理Decimal类型
                    if hasattr(v, 'to_eng_string'):
                        session_data[k] = v.to_eng_string()
                    else:
                        session_data[k] = v
            request.session['unit_change_last'] = session_data
            return render(request, 'success.html', {
                'filepath': filepath,
                'download_url': f'/download/{filename}',
                'fail_download_url': fail_download_url
            })
    else:
        if request.GET.get('clear'):
            request.session.pop('unit_change_last', None)
            form = UnitChangeForm()
        else:
            initial = request.session.get('unit_change_last')
            form = UnitChangeForm(initial=initial)

    return render(request, 'unit_change_form.html', {'form': form})


def download_sql(request, filename):
    file_path = os.path.join(settings.BASE_DIR, 'temp_downloads', filename)
    if os.path.exists(file_path):
        response = FileResponse(open(file_path, 'rb'),
                                as_attachment=True, filename=filename)
        return response
    else:
        return HttpResponse("文件不存在", status=404)


def generate_price_sql(line_ids, new_quantity, new_price, orig_quantity=None, orig_price=None, ops_remark=''):
    line_id_str = "', '".join(line_ids)
    line_id_in = f"'{line_id_str}'"
    sql = []
    sql.append("1、执行语句")

    # 解析操作备注
    ops_remark = parse_ops_remark(ops_remark)
    if new_quantity is not None:
        stmt = (
            "UPDATE tphct02 SET "
            f"BPO_QTY={new_quantity}, "
            f"BPO_PRICE={new_price}, "
            f"BPO_AMT={new_price}*{new_quantity}, "
            f"BPO_NOTAX_PRICE={new_price}/(1+TAX_RATE), "
            f"BPO_NOTAX_AMT=({new_price}*{new_quantity})/(1+TAX_RATE), "
            f"OPS_REMARK='{ops_remark}' "
            f"WHERE BPO_LINE_ID IN ({line_id_in}) AND ALIVE_FLAG='1';"
        )
    else:
        stmt = (
            "UPDATE tphct02 SET "
            f"BPO_PRICE={new_price}, "
            f"BPO_AMT={new_price}*BPO_QTY, "
            f"BPO_NOTAX_PRICE={new_price}/(1+TAX_RATE), "
            f"BPO_NOTAX_AMT=({new_price}*BPO_QTY)/(1+TAX_RATE), "
            f"OPS_REMARK='{ops_remark}' "
            f"WHERE BPO_LINE_ID IN ({line_id_in}) AND ALIVE_FLAG='1';"
        )
    sql.append(stmt)

    # 获取唯一的BPO_ID列表
    bpo_ids = []
    for line_id in line_ids:
        # 从line_id中提取BPO_ID（假设格式为 BPO_ID-000001）
        bpo_id_parts = line_id.split('-')
        if len(bpo_id_parts) > 4:  # 处理包含多个连字符的情况
            bpo_id = '-'.join(bpo_id_parts[:-1])
        else:
            bpo_id = '-'.join(bpo_id_parts[:-1]
                              ) if len(bpo_id_parts) > 1 else line_id
        if bpo_id not in bpo_ids:
            bpo_ids.append(bpo_id)

    # 批量更新合同主表汇总金额
    sql.append("-- 批量更新合同的主表汇总金额")
    for i, bpo_id in enumerate(bpo_ids, 1):
        main_stmt = (
            f"UPDATE tphct01 SET "
            f"BPO_AMT=(SELECT SUM(BPO_AMT) FROM tphct02 WHERE BPO_ID='{bpo_id}' AND ALIVE_FLAG='1'), "
            f"TARGET_AMT=(SELECT SUM(BPO_AMT) FROM tphct02 WHERE BPO_ID='{bpo_id}' AND ALIVE_FLAG='1'), "
            f"BPO_NOTAX_AMT=(SELECT SUM(BPO_NOTAX_AMT) FROM tphct02 WHERE BPO_ID='{bpo_id}' AND ALIVE_FLAG='1'), "
            f"OPS_REMARK='{ops_remark}' "
            f"WHERE BPO_ID='{bpo_id}' AND ALIVE_FLAG='1';"
        )
        sql.append(main_stmt)

    # 回退语句部分
    sql.append("2、回退语句")
    if orig_price is not None and orig_quantity is not None:
        rollback_stmt = (
            "UPDATE tphct02 SET "
            f"BPO_QTY={orig_quantity}, "
            f"BPO_PRICE={orig_price}, "
            f"BPO_AMT={orig_price}*{orig_quantity}, "
            f"BPO_NOTAX_PRICE={orig_price}/(1+TAX_RATE), "
            f"BPO_NOTAX_AMT=({orig_price}*{orig_quantity})/(1+TAX_RATE), "
            f"OPS_REMARK='' "
            f"WHERE BPO_LINE_ID IN ({line_id_in}) AND ALIVE_FLAG='1';"
        )
        sql.append(rollback_stmt)
    elif orig_price is not None and orig_quantity is None:
        rollback_stmt = (
            "UPDATE tphct02 SET "
            f"BPO_PRICE={orig_price}, "
            f"BPO_AMT={orig_price}*BPO_QTY, "
            f"BPO_NOTAX_PRICE={orig_price}/(1+TAX_RATE), "
            f"BPO_NOTAX_AMT=({orig_price}*BPO_QTY)/(1+TAX_RATE), "
            f"OPS_REMARK='' "
            f"WHERE BPO_LINE_ID IN ({line_id_in}) AND ALIVE_FLAG='1';"
        )
        sql.append(rollback_stmt)
    elif orig_price is None and orig_quantity is not None:
        rollback_stmt = (
            "UPDATE tphct02 SET "
            f"BPO_QTY={orig_quantity}, "
            f"BPO_AMT=BPO_PRICE*{orig_quantity}, "
            f"BPO_NOTAX_AMT=(BPO_PRICE*{orig_quantity})/(1+TAX_RATE), "
            f"OPS_REMARK='' "
            f"WHERE BPO_LINE_ID IN ({line_id_in}) AND ALIVE_FLAG='1';"
        )
        sql.append(rollback_stmt)

    # 回退合同主表
    sql.append("-- 回退合同主表")
    for i, bpo_id in enumerate(bpo_ids, 1):
        main_rollback_stmt = (
            f"UPDATE tphct01 SET "
            f"BPO_AMT=(SELECT SUM(BPO_AMT) FROM tphct02 WHERE BPO_ID='{bpo_id}' AND ALIVE_FLAG='1'), "
            f"TARGET_AMT=(SELECT SUM(BPO_AMT) FROM tphct02 WHERE BPO_ID='{bpo_id}' AND ALIVE_FLAG='1'), "
            f"BPO_NOTAX_AMT=(SELECT SUM(BPO_NOTAX_AMT) FROM tphct02 WHERE BPO_ID='{bpo_id}' AND ALIVE_FLAG='1'), "
            f"OPS_REMARK='' "
            f"WHERE BPO_ID='{bpo_id}' AND ALIVE_FLAG='1';"
        )
        sql.append(main_rollback_stmt)

    # 数据库信息
    sql.append("3.数据库")
    sql.append("ip：192.168.11.71")
    sql.append("库名：cnnc_ph")

    return "\n".join(sql)


def parse_price_excel(file):
    if not OPENPYXL_AVAILABLE:
        raise ValueError("缺少 openpyxl，无法解析 Excel")
    wb = openpyxl.load_workbook(file)
    ws = wb.active
    headers = [cell.value for cell in ws[1]]
    idx = {str(h): i for i, h in enumerate(headers)}

    def pick(alts):
        for a in alts:
            if a in idx:
                return idx[a]
        return None
    lid_idx = pick(['line_id', 'BPO_LINE_ID', '明细行ID'])
    price_idx = pick(['price', 'BPO_PRICE', '单价'])
    qty_idx = pick(['quantity', 'BPO_QTY', '数量'])
    orig_qty_idx = pick(['orig_quantity', '原数量'])
    orig_price_idx = pick(['orig_price', '原单价'])
    if lid_idx is None or price_idx is None:
        raise ValueError("Excel 缺少必要列：明细行ID/单价")
    records = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row:
            continue
        lid = row[lid_idx]
        prc = row[price_idx]
        qty = row[qty_idx] if qty_idx is not None else None
        if lid is None or prc is None:
            continue
        rec = {
            'line_id': str(lid).strip(),
            'price': prc,
            'quantity': qty,
        }
        if orig_qty_idx is not None:
            rec['orig_quantity'] = row[orig_qty_idx]
        if orig_price_idx is not None:
            rec['orig_price'] = row[orig_price_idx]
        records.append(rec)
    if not records:
        raise ValueError("Excel 中没有有效的行数据")
    return records


def generate_price_sql_bulk(records, ops_remark=None):
    sql = []
    sql.append("1、执行语句")
    for i, r in enumerate(records, 1):
        q = r.get('quantity')
        if q is not None:
            exec_stmt = (
                f"UPDATE tphct02 SET "
                f"BPO_QTY={q}, "
                f"BPO_PRICE={r['price']}, "
                f"BPO_AMT={r['price']}*{q}, "
                f"BPO_NOTAX_PRICE={r['price']}/(1+TAX_RATE), "
                f"BPO_NOTAX_AMT=({r['price']}*{q})/(1+TAX_RATE), "
                f"OPS_REMARK='{ops_remark or ''}' "
                f"WHERE BPO_LINE_ID='{r['line_id']}' AND ALIVE_FLAG='1';"
            )
        else:
            exec_stmt = (
                f"UPDATE tphct02 SET "
                f"BPO_PRICE={r['price']}, "
                f"BPO_AMT={r['price']}*BPO_QTY, "
                f"BPO_NOTAX_PRICE={r['price']}/(1+TAX_RATE), "
                f"BPO_NOTAX_AMT=({r['price']}*BPO_QTY)/(1+TAX_RATE), "
                f"OPS_REMARK='{ops_remark or ''}' "
                f"WHERE BPO_LINE_ID='{r['line_id']}' AND ALIVE_FLAG='1';"
            )
        sql.append(exec_stmt)
    bpo_ids = []
    for r in records:
        parts = r['line_id'].split('-')
        if len(parts) > 4:
            bpo_id = '-'.join(parts[:-1])
        else:
            bpo_id = '-'.join(parts[:-1]) if len(parts) > 1 else r['line_id']
        if bpo_id not in bpo_ids:
            bpo_ids.append(bpo_id)
    sql.append("-- 批量更新合同的主表汇总金额")
    for i, bpo_id in enumerate(bpo_ids, 1):
        main_stmt = (
            f"UPDATE tphct01 SET "
            f"BPO_AMT=(SELECT SUM(BPO_AMT) FROM tphct02 WHERE BPO_ID='{bpo_id}' AND ALIVE_FLAG='1'), "
            f"TARGET_AMT=(SELECT SUM(BPO_AMT) FROM tphct02 WHERE BPO_ID='{bpo_id}' AND ALIVE_FLAG='1'), "
            f"BPO_NOTAX_AMT=(SELECT SUM(BPO_NOTAX_AMT) FROM tphct02 WHERE BPO_ID='{bpo_id}' AND ALIVE_FLAG='1'), "
            f"OPS_REMARK='{ops_remark or ''}' "
            f"WHERE BPO_ID='{bpo_id}' AND ALIVE_FLAG='1';"
        )
        sql.append(main_stmt)
    sql.append("2、回退语句")
    for i, r in enumerate(records, 1):
        rq = r.get('orig_quantity')
        rp = r.get('orig_price')
        if rq is not None and rp is not None:
            rollback_stmt = (
                f"UPDATE tphct02 SET "
                f"BPO_QTY={rq}, "
                f"BPO_PRICE={rp}, "
                f"BPO_AMT={rp}*{rq}, "
                f"BPO_NOTAX_PRICE={rp}/(1+TAX_RATE), "
                f"BPO_NOTAX_AMT=({rp}*{rq})/(1+TAX_RATE), "
                f"OPS_REMARK='' "
                f"WHERE BPO_LINE_ID='{r['line_id']}' AND ALIVE_FLAG='1';"
            )
            sql.append(rollback_stmt)
        elif rp is not None and rq is None:
            rollback_stmt = (
                f"UPDATE tphct02 SET "
                f"BPO_PRICE={rp}, "
                f"BPO_AMT={rp}*BPO_QTY, "
                f"BPO_NOTAX_PRICE={rp}/(1+TAX_RATE), "
                f"BPO_NOTAX_AMT=({rp}*BPO_QTY)/(1+TAX_RATE), "
                f"OPS_REMARK='' "
                f"WHERE BPO_LINE_ID='{r['line_id']}' AND ALIVE_FLAG='1';"
            )
            sql.append(rollback_stmt)
        elif rp is None and rq is not None:
            rollback_stmt = (
                f"UPDATE tphct02 SET "
                f"BPO_QTY={rq}, "
                f"BPO_AMT=BPO_PRICE*{rq}, "
                f"BPO_NOTAX_AMT=(BPO_PRICE*{rq})/(1+TAX_RATE), "
                f"OPS_REMARK='' "
                f"WHERE BPO_LINE_ID='{r['line_id']}' AND ALIVE_FLAG='1';"
            )
            sql.append(rollback_stmt)
    sql.append("-- 回退合同主表")
    for i, bpo_id in enumerate(bpo_ids, 1):
        main_rollback_stmt = (
            f"UPDATE tphct01 SET "
            f"BPO_AMT=(SELECT SUM(BPO_AMT) FROM tphct02 WHERE BPO_ID='{bpo_id}' AND ALIVE_FLAG='1'), "
            f"TARGET_AMT=(SELECT SUM(BPO_AMT) FROM tphct02 WHERE BPO_ID='{bpo_id}' AND ALIVE_FLAG='1'), "
            f"BPO_NOTAX_AMT=(SELECT SUM(BPO_NOTAX_AMT) FROM tphct02 WHERE BPO_ID='{bpo_id}' AND ALIVE_FLAG='1'), "
            f"OPS_REMARK='' "
            f"WHERE BPO_ID='{bpo_id}' AND ALIVE_FLAG='1';"
        )
        sql.append(main_rollback_stmt)
    sql.append("3.数据库")
    sql.append("ip：192.168.11.71")
    sql.append("库名：cnnc_ph")
    return "\n".join(sql)


def parse_item_excel(file):
    if not OPENPYXL_AVAILABLE:
        raise ValueError("缺少 openpyxl，无法解析 Excel")
    wb = openpyxl.load_workbook(file)
    ws = wb.active
    headers = [cell.value for cell in ws[1]]
    idx = {str(h): i for i, h in enumerate(headers)}

    def pick(alts):
        for a in alts:
            if a in idx:
                return idx[a]
        return None
    lid_idx = pick(['line_id', 'BPO_LINE_ID', '明细行ID'])
    new_id_idx = pick(['ITEM_ID', 'item_id', '物资编码'])
    new_name_idx = pick(['ITEM_NAME', 'item_name', '物资名称'])
    new_uom_idx = pick(['ITEM_UOM', 'item_uom', '计量单位'])
    new_cat_idx = pick(['CATEGORY', 'category', '物资分类编码'])
    orig_id_idx = pick(['orig_item_id', '原物资编码'])
    orig_name_idx = pick(['orig_item_name', '原物资名称'])
    orig_uom_idx = pick(['orig_item_uom', '原计量单位'])
    orig_cat_idx = pick(['orig_category', '原物资分类编码'])
    desc_idx = pick(['描述', 'desc', '错误'])
    if lid_idx is None:
        raise ValueError("Excel 缺少必要列：明细行ID")
    records = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row:
            continue
        lid = row[lid_idx]
        if lid is None:
            continue
        rec = {'line_id': str(lid).strip()}
        if new_id_idx is not None:
            rec['new_item_id'] = normalize_item_id(row[new_id_idx])
        if new_name_idx is not None:
            rec['new_item_name'] = row[new_name_idx]
        if new_uom_idx is not None:
            rec['new_item_uom'] = row[new_uom_idx]
        if new_cat_idx is not None:
            rec['new_category'] = row[new_cat_idx]
        if orig_id_idx is not None:
            rec['orig_item_id'] = normalize_item_id(row[orig_id_idx])
        if orig_name_idx is not None:
            rec['orig_item_name'] = row[orig_name_idx]
        if orig_uom_idx is not None:
            rec['orig_item_uom'] = row[orig_uom_idx]
        if orig_cat_idx is not None:
            rec['orig_category'] = row[orig_cat_idx]
        if desc_idx is not None:
            rec['desc'] = row[desc_idx]
        records.append(rec)
    if not records:
        raise ValueError("Excel 中没有有效的行数据")
    return records


def generate_item_sql_bulk(records, ops_remark=None):
    sql = []
    sql.append("1、执行语句")
    for r in records:
        parts = []
        if r.get('new_item_id'):
            parts.append(f"ITEM_ID = '{str(r['new_item_id']).strip()}'")
        if r.get('new_item_name'):
            parts.append(f"ITEM_NAME = '{str(r['new_item_name']).strip()}'")
        if r.get('new_item_uom'):
            parts.append(f"ITEM_UOM = '{str(r['new_item_uom']).strip()}'")
        if r.get('new_category'):
            parts.append(f"CATEGORY = '{str(r['new_category']).strip()}'")
        if parts:
            stmt = (
                "UPDATE TPHCT02 "
                "SET " + ", ".join(parts) + ", "
                f"OPS_REMARK = '{ops_remark or ''}' "
                f"WHERE BPO_LINE_ID = '{r['line_id']}' "
                "AND ALIVE_FLAG = '1';"
            )
            sql.append(stmt)
    sql.append("")
    sql.append("2、回退语句")
    for r in records:
        rb = []
        if r.get('orig_item_id'):
            rb.append(f"ITEM_ID = '{str(r['orig_item_id']).strip()}'")
        if r.get('orig_item_name'):
            rb.append(f"ITEM_NAME = '{str(r['orig_item_name']).strip()}'")
        if r.get('orig_item_uom'):
            rb.append(f"ITEM_UOM = '{str(r['orig_item_uom']).strip()}'")
        if r.get('orig_category'):
            rb.append(f"CATEGORY = '{str(r['orig_category']).strip()}'")
        if rb:
            stmt = (
                "UPDATE TPHCT02 "
                "SET " + ", ".join(rb) + ", "
                f"OPS_REMARK = '' "
                f"WHERE BPO_LINE_ID = '{r['line_id']}' "
                "AND ALIVE_FLAG = '1';"
            )
            sql.append(stmt)
    sql.append("")
    sql.append("3、数据库")
    sql.append("ip：192.168.11.71")
    sql.append("库名：cnnc_ph")
    return "\n".join(sql)


def contract_item_update_view(request):
    if request.method == 'POST':
        form = ContractItemUpdateForm(request.POST, request.FILES)
        if form.is_valid():
            cd = form.cleaned_data
            ops_remark = parse_ops_remark(cd.get('ops_remark', ''))
            if cd.get('excel_file'):
                records = parse_item_excel(cd['excel_file'])
            else:
                rec = {
                    'line_id': cd['single_line_id'],
                    'new_item_id': cd.get('new_item_id'),
                    'new_item_name': cd.get('new_item_name'),
                    'new_item_uom': cd.get('new_item_uom'),
                    'new_category': cd.get('new_category'),
                    'orig_item_id': cd.get('orig_item_id'),
                    'orig_item_name': cd.get('orig_item_name'),
                    'orig_item_uom': cd.get('orig_item_uom'),
                    'orig_category': cd.get('orig_category'),
                }
                records = [rec]

            def enrich(rec, prefix):
                iid = rec.get(f'{prefix}_item_id')
                name = rec.get(f'{prefix}_item_name')
                uom = rec.get(f'{prefix}_item_uom')
                cat = rec.get(f'{prefix}_category')
                if iid and (not name or not uom or not cat):
                    obj = ItemDetail.objects.filter(
                        item_id=str(iid).strip()).first()
                    if obj:
                        if not name:
                            rec[f'{prefix}_item_name'] = obj.item_name
                        if not uom:
                            rec[f'{prefix}_item_uom'] = obj.item_uom
                        if not cat:
                            rec[f'{prefix}_category'] = obj.category
                        return True
                    return False
                return True
            errors = []
            for r in records:
                if r.get('new_item_id'):
                    ok = enrich(r, 'new')
                    if not ok:
                        errors.append(f"新物资编码未找到: {r.get('new_item_id')}")
                if r.get('orig_item_id'):
                    ok = enrich(r, 'orig')
                    if not ok:
                        errors.append(f"原物资编码未找到: {r.get('orig_item_id')}")
                if r.get('new_item_id') and (not r.get('new_item_name') or not r.get('new_item_uom') or not r.get('new_category')):
                    if not ItemDetail.objects.filter(item_id=str(r['new_item_id']).strip()).exists():
                        errors.append("新物资编码未找到，需填写名称/计量/分类")
                if r.get('orig_item_id') and (not r.get('orig_item_name') or not r.get('orig_item_uom') or not r.get('orig_category')):
                    if not ItemDetail.objects.filter(item_id=str(r['orig_item_id']).strip()).exists():
                        errors.append("原物资编码未找到，需填写名称/计量/分类")
            if errors:
                form.add_error(None, "; ".join(errors))
                return render(request, 'contract_item_form.html', {'form': form})
            sql_content = generate_item_sql_bulk(records, ops_remark)
            now = datetime.now()
            year_month = now.strftime("%Y%m")
            day = now.strftime("%d")
            filename = f"{cd['dynamic_id']}_修改合同物资编码.sql"
            base_dir = r"D:\临时文件"
            target_dir = os.path.join(base_dir, year_month, day)
            os.makedirs(target_dir, exist_ok=True)
            filepath = os.path.join(target_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(sql_content)

            # 记录文件保存
            logger.info(f"SQL文件已保存: {filepath}")
            temp_dir = os.path.join(settings.BASE_DIR, 'temp_downloads')
            os.path.exists(temp_dir) or os.makedirs(temp_dir, exist_ok=True)
            download_path = os.path.join(temp_dir, filename)
            with open(download_path, 'w', encoding='utf-8') as f:
                f.write(sql_content)
            session_data = {}
            for k, v in cd.items():
                if k != 'excel_file':
                    if hasattr(v, 'to_eng_string'):
                        session_data[k] = v.to_eng_string()
                    else:
                        session_data[k] = v
            request.session['contract_item_last'] = session_data
            return render(request, 'success.html', {
                'filepath': filepath,
                'download_url': f"/download/{filename}",
                'active_menu': 'enddate',
                'sidebar_groups': SIDEBAR_GROUPS,
            })
    else:
        if request.GET.get('clear'):
            request.session.pop('contract_item_last', None)
            form = ContractItemUpdateForm()
        else:
            initial = request.session.get('contract_item_last')
            form = ContractItemUpdateForm(initial=initial)
    return render(request, 'contract_item_form.html', {'form': form})


def download_item_template(request):
    if not OPENPYXL_AVAILABLE:
        return HttpResponse("缺少 openpyxl，请安装后使用模板下载：pip install openpyxl", status=500)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = '模板'
    ws.append(['明细行ID', '物资编码', '物资名称', '计量单位', '物资分类编码',
              '原物资编码', '原物资名称', '原计量单位', '原物资分类编码', '描述'])
    ws.append(['BPO-EXAMPLE-000001', '01607733', '鞋套',
              '双', '430798', None, None, None, None, None])
    bio = io.BytesIO()
    wb.save(bio)
    bio.seek(0)
    response = FileResponse(bio, as_attachment=True,
                            filename='contract_item_template.xlsx')
    response['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    return response


def download_price_template(request):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = '模板'
    ws.append(['明细行ID', '单价', '数量', '原数量', '原单价'])
    ws.append(['BPO-EXAMPLE-000001', 100, 1, None, None])
    bio = io.BytesIO()
    wb.save(bio)
    bio.seek(0)
    response = FileResponse(bio, as_attachment=True,
                            filename='contract_price_template.xlsx')
    response['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    return response


def contract_detail_price_view(request):
    """
    处理合同明细单价修改的视图函数
    """
    if request.method == 'POST':
        form = ContractDetailPriceForm(request.POST, request.FILES)
        if form.is_valid():
            cd = form.cleaned_data
            log_view_input("合同明细单价修改", cd)

            # 解析OPS_REMARK
            ops_remark = parse_ops_remark(cd.get('ops_remark', ''))

            if cd.get('excel_file'):
                records = parse_price_excel(cd['excel_file'])
                sql_content = generate_price_sql_bulk(records, ops_remark)
            else:
                new_quantity = cd.get('new_quantity')
                new_price = cd.get('new_price')
                orig_quantity = cd.get('orig_quantity')
                orig_price = cd.get('orig_price')
                if not new_price or not cd.get('single_line_id'):
                    form.add_error(None, "单条模式需填写单价和明细行ID；数量可不填")
                    return render(request, 'contract_price_form.html', {'form': form})
                line_ids = [cd['single_line_id']]
                sql_content = generate_price_sql(
                    line_ids, new_quantity, new_price, orig_quantity, orig_price, ops_remark)

            # 生成文件名
            now = datetime.now()
            year_month = now.strftime("%Y%m")
            day = now.strftime("%d")
            filename = f"{cd['dynamic_id']}_修改合同明细单价.sql"

            # 保存到临时文件
            base_dir = r"D:\临时文件"
            target_dir = os.path.join(base_dir, year_month, day)
            os.makedirs(target_dir, exist_ok=True)
            filepath = os.path.join(target_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(sql_content)

            # 记录文件保存
            logger.info(f"SQL文件已保存: {filepath}")

            # 保存到下载目录
            temp_dir = os.path.join(settings.BASE_DIR, 'temp_downloads')
            os.makedirs(temp_dir, exist_ok=True)
            download_path = os.path.join(temp_dir, filename)
            with open(download_path, 'w', encoding='utf-8') as f:
                f.write(sql_content)

            # 将Decimal类型转换为字符串以支持JSON序列化
            session_data = {}
            for k, v in cd.items():
                if k != 'excel_file':
                    # 处理Decimal类型
                    if hasattr(v, 'to_eng_string'):
                        session_data[k] = v.to_eng_string()
                    else:
                        session_data[k] = v
            request.session['contract_price_last'] = session_data
            return render(request, 'success.html', {
                'filepath': filepath,
                'download_url': f'/download/{filename}',
                'active_menu': 'unit_change',
                'sidebar_groups': SIDEBAR_GROUPS,
            })
    else:
        if request.GET.get('clear'):
            request.session.pop('contract_price_last', None)
            form = ContractDetailPriceForm()
        else:
            initial = request.session.get('contract_price_last')
            form = ContractDetailPriceForm(initial=initial)

    return render(request, 'contract_price_form.html', {'form': form})


def generate_sql(records, **kwargs):
    update_drafting = kwargs.get('update_drafting', False)
    update_contract_party = kwargs.get('update_contract_party', False)
    old_drafting_id = kwargs.get('old_drafting_id')
    old_drafting_name = kwargs.get('old_drafting_name')
    old_party_id = kwargs.get('old_party_id')
    old_party_name = kwargs.get('old_party_name')

    # 获取并解析ops_remark
    ops_remark = parse_ops_remark(kwargs.get('ops_remark', ''))

    sql = []
    sql.append("1、执行语句")
    for r in records:
        parts = []
        if update_drafting:
            ndid = r.get('new_drafting_id', kwargs.get('new_drafting_id'))
            ndnm = r.get('new_drafting_name', kwargs.get('new_drafting_name'))
            if not ndid and ndnm:
                code = extract_company_code(ndnm)
                if code:
                    ndid = code
            if ndid:
                parts.append(f"PRIMARY_CONTRACT_DRAFTING_UNIT='{ndid}'")
            if ndnm:
                parts.append(
                    f"PRIMARY_CONTRACT_DRAFTING_UNIT_NAME='{extract_company_name(ndnm)}'")
        if update_contract_party:
            npid = r.get('new_party_id', kwargs.get('new_party_id'))
            npnm = r.get('new_party_name', kwargs.get('new_party_name'))
            if not npid and npnm:
                code = extract_company_code(npnm)
                if code:
                    npid = code
            if npid:
                parts.append(f"CONTRACT_PARTY_ID='{npid}'")
            if npnm:
                parts.append(
                    f"CONTRACT_PARTY_NAME='{extract_company_name(npnm)}'")
        if parts:
            set_clause = ', '.join(parts)
            sql.append(
                f"update tprfa03 set {set_clause}, OPS_REMARK='{ops_remark}' where PURCHASE_SCHEME_NO='{r['scheme']}';")
            sql.append(
                f"update tprxj05 set {set_clause}, OPS_REMARK='{ops_remark}' where PURCHASE_SCHEME_NO='{r['scheme']}' AND INQ_ID='{r['inquiry']}';")
            sql.append(
                f"update tprnq03 set {set_clause}, OPS_REMARK='{ops_remark}' where PURCHASE_SCHEME_NO='{r['scheme']}' AND INQ_ID='{r['inquiry']}' AND sign_id='{r['result']}';")

    sql.append("2.回退语句")
    for r in records:
        rb_parts = []
        if update_drafting:
            odid = r.get('orig_drafting_id', old_drafting_id)
            odnm = r.get('orig_drafting_name', old_drafting_name)
            if not odid and odnm:
                code = extract_company_code(odnm)
                if code:
                    odid = code
            if odid:
                rb_parts.append(f"PRIMARY_CONTRACT_DRAFTING_UNIT='{odid}'")
            if odnm:
                rb_parts.append(
                    f"PRIMARY_CONTRACT_DRAFTING_UNIT_NAME='{extract_company_name(odnm)}'")
        if update_contract_party:
            opid = r.get('orig_party_id', old_party_id)
            opnm = r.get('orig_party_name', old_party_name)
            if not opid and opnm:
                code = extract_company_code(opnm)
                if code:
                    opid = code
            if opid:
                rb_parts.append(f"CONTRACT_PARTY_ID='{opid}'")
            if opnm:
                rb_parts.append(
                    f"CONTRACT_PARTY_NAME='{extract_company_name(opnm)}'")
        if rb_parts:
            rb_clause = ', '.join(rb_parts)
            sql.append(
                f"update tprfa03 set {rb_clause}, OPS_REMARK='' where PURCHASE_SCHEME_NO='{r['scheme']}';")
            sql.append(
                f"update tprxj05 set {rb_clause}, OPS_REMARK='' where PURCHASE_SCHEME_NO='{r['scheme']}' AND INQ_ID='{r['inquiry']}';")
            sql.append(
                f"update tprnq03 set {rb_clause}, OPS_REMARK='' where PURCHASE_SCHEME_NO='{r['scheme']}' AND INQ_ID='{r['inquiry']}' AND sign_id='{r['result']}';")

    sql.append("3.数据库")
    sql.append("ip：192.168.11.76")
    sql.append("库名：cnnc_ph")
    return "\n".join(sql)


def parse_excel(file):
    wb = openpyxl.load_workbook(file)
    ws = wb.active
    records = []
    headers = [cell.value for cell in ws[1]]
    hset = {str(h) if h is not None else '' for h in headers}
    idx = {str(h): i for i, h in enumerate(headers)}
    scheme_alts = ['scheme_no', 'PURCHASE_SCHEME_NO',
                   'purchase_scheme_no', '采购方案编号']
    inquiry_alts = ['inquiry_no', 'inq_id', 'INQ_ID', '询价单编号']
    result_alts = ['result_no', 'sign_id', 'SIGN_ID', '定标结果编号']

    def pick(alts):
        for a in alts:
            if a in idx:
                return idx[a]
        return None
    s_idx = pick(scheme_alts)
    i_idx = pick(inquiry_alts)
    r_idx = pick(result_alts)
    if s_idx is None or i_idx is None or r_idx is None:
        raise ValueError("Excel 缺少必要列：方案、询价、定标")
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not any(row):
            continue
        rec = {
            'scheme': row[s_idx],
            'inquiry': row[i_idx],
            'result': row[r_idx]
        }
        if not all(rec.values()):
            continue
        ndid = None
        ndnm = None
        npid = None
        npnm = None
        odid = None
        odnm = None
        opid = None
        opnm = None
        for k in ['new_drafting_id', '新起草单位ID']:
            if k in idx:
                ndid = row[idx[k]]
                break
        for k in ['new_drafting_name', '新起草单位名称', '组织机构名称']:
            if k in idx:
                ndnm = row[idx[k]]
                break
        for k in ['new_party_id', '新签约主体ID']:
            if k in idx:
                npid = row[idx[k]]
                break
        for k in ['new_party_name', '新签约主体名称']:
            if k in idx:
                npnm = row[idx[k]]
                break
        for k in ['orig_drafting_id', '原起草单位ID']:
            if k in idx:
                odid = row[idx[k]]
                break
        for k in ['orig_drafting_name', '原起草单位名称', '组织机构名称']:
            if k in idx:
                odnm = row[idx[k]]
                break
        for k in ['orig_party_id', '原签约主体ID']:
            if k in idx:
                opid = row[idx[k]]
                break
        for k in ['orig_party_name', '原签约主体名称']:
            if k in idx:
                opnm = row[idx[k]]
                break
        if ndid is not None:
            rec['new_drafting_id'] = ndid
        if ndnm is not None:
            rec['new_drafting_name'] = ndnm
        if npid is not None:
            rec['new_party_id'] = npid
        if npnm is not None:
            rec['new_party_name'] = npnm
        if odid is not None:
            rec['orig_drafting_id'] = odid
        if odnm is not None:
            rec['orig_drafting_name'] = odnm
        if opid is not None:
            rec['orig_party_id'] = opid
        if opnm is not None:
            rec['orig_party_name'] = opnm
        records.append(rec)
    return records


def unit_change_view(request):
    if request.method == 'POST':
        form = UnitChangeForm(request.POST, request.FILES)
        if form.is_valid():
            cd = form.cleaned_data

            if cd.get('excel_file'):
                records = parse_excel(cd['excel_file'])
            else:
                records = [{
                    'scheme': cd['scheme_no'],
                    'inquiry': cd['inquiry_no'],
                    'result': cd['result_no']
                }]

            update_drafting = bool(
                cd.get('new_drafting_id') or cd.get('new_drafting_name'))
            update_contract_party = bool(
                cd.get('new_party_id') or cd.get('new_party_name'))

            # 解析OPS_REMARK
            ops_remark = parse_ops_remark(cd.get('ops_remark', ''))

            sql_content = generate_sql(
                records,
                update_drafting=update_drafting,
                update_contract_party=update_contract_party,
                old_drafting_id=cd.get('old_drafting_id'),
                old_drafting_name=cd.get('old_drafting_name'),
                new_drafting_id=cd.get('new_drafting_id'),
                new_drafting_name=cd.get('new_drafting_name'),
                old_party_id=cd.get('old_party_id'),
                old_party_name=cd.get('old_party_name'),
                new_party_id=cd.get('new_party_id'),
                new_party_name=cd.get('new_party_name'),
                ops_remark=ops_remark
            )

            # 记录SQL生成结果
            logger.info(
                f"SQL生成完成: 更新起草单位={update_drafting}, 更新签约主体={update_contract_party}, SQL长度={len(sql_content)}")

            now = datetime.now()
            year_month = now.strftime("%Y%m")
            day = now.strftime("%d")
            if update_drafting and update_contract_party:
                suffix = "修改起草单位和签约主体"
            elif update_drafting:
                suffix = "修改起草单位"
            elif update_contract_party:
                suffix = "修改签约主体"
            else:
                suffix = "修改合同单位信息"
            filename = f"{cd['dynamic_id']}_{suffix}.sql"

            base_dir = r"D:\临时文件"
            target_dir = os.path.join(base_dir, year_month, day)
            os.makedirs(target_dir, exist_ok=True)
            filepath = os.path.join(target_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(sql_content)

            # 记录文件保存
            logger.info(f"SQL文件已保存: {filepath}")

            temp_dir = os.path.join(settings.BASE_DIR, 'temp_downloads')
            os.makedirs(temp_dir, exist_ok=True)
            download_path = os.path.join(temp_dir, filename)
            with open(download_path, 'w', encoding='utf-8') as f:
                f.write(sql_content)

            # 将Decimal类型转换为字符串以支持JSON序列化
            session_data = {}
            for k, v in cd.items():
                if k != 'excel_file':
                    # 处理Decimal类型
                    if hasattr(v, 'to_eng_string'):
                        session_data[k] = v.to_eng_string()
                    else:
                        session_data[k] = v
            request.session['unit_change_last'] = session_data
            return render(request, 'success.html', {
                'filepath': filepath,
                'download_url': f'/download/{filename}',
                'active_menu': 'contract_price',
                'sidebar_groups': SIDEBAR_GROUPS,
            })
    else:
        if request.GET.get('clear'):
            request.session.pop('unit_change_last', None)
            form = UnitChangeForm()
        else:
            initial = request.session.get('unit_change_last')
            form = UnitChangeForm(initial=initial)

    return render(request, 'unit_change_form.html', {
        'form': form,
        'active_menu': 'unit_change',
        'sidebar_groups': SIDEBAR_GROUPS,
    })


def download_sql(request, filename):
    file_path = os.path.join(settings.BASE_DIR, 'temp_downloads', filename)
    if os.path.exists(file_path):
        response = FileResponse(open(file_path, 'rb'),
                                as_attachment=True, filename=filename)
        return response
    else:
        return HttpResponse("文件不存在", status=404)


def generate_price_sql(line_ids, new_quantity, new_price, orig_quantity=None, orig_price=None, ops_remark=''):
    line_id_str = "', '".join(line_ids)
    line_id_in = f"'{line_id_str}'"
    sql = []
    sql.append("1、执行语句")

    # 解析操作备注
    ops_remark = parse_ops_remark(ops_remark)
    if new_quantity is not None:
        stmt = (
            "UPDATE tphct02 SET "
            f"BPO_QTY={new_quantity}, "
            f"BPO_PRICE={new_price}, "
            f"BPO_AMT={new_price}*{new_quantity}, "
            f"BPO_NOTAX_PRICE={new_price}/(1+TAX_RATE), "
            f"BPO_NOTAX_AMT=({new_price}*{new_quantity})/(1+TAX_RATE), "
            f"OPS_REMARK='{ops_remark}' "
            f"WHERE BPO_LINE_ID IN ({line_id_in}) AND ALIVE_FLAG='1';"
        )
    else:
        stmt = (
            "UPDATE tphct02 SET "
            f"BPO_PRICE={new_price}, "
            f"BPO_AMT={new_price}*BPO_QTY, "
            f"BPO_NOTAX_PRICE={new_price}/(1+TAX_RATE), "
            f"BPO_NOTAX_AMT=({new_price}*BPO_QTY)/(1+TAX_RATE), "
            f"OPS_REMARK='{ops_remark}' "
            f"WHERE BPO_LINE_ID IN ({line_id_in}) AND ALIVE_FLAG='1';"
        )
    sql.append(stmt)

    # 获取唯一的BPO_ID列表
    bpo_ids = []
    for line_id in line_ids:
        # 从line_id中提取BPO_ID（假设格式为 BPO_ID-000001）
        bpo_id_parts = line_id.split('-')
        if len(bpo_id_parts) > 4:  # 处理包含多个连字符的情况
            bpo_id = '-'.join(bpo_id_parts[:-1])
        else:
            bpo_id = '-'.join(bpo_id_parts[:-1]
                              ) if len(bpo_id_parts) > 1 else line_id
        if bpo_id not in bpo_ids:
            bpo_ids.append(bpo_id)

    # 批量更新合同主表汇总金额
    sql.append("-- 批量更新合同的主表汇总金额")
    for i, bpo_id in enumerate(bpo_ids, 1):
        main_stmt = (
            f"UPDATE tphct01 SET "
            f"BPO_AMT=(SELECT SUM(BPO_AMT) FROM tphct02 WHERE BPO_ID='{bpo_id}' AND ALIVE_FLAG='1'), "
            f"TARGET_AMT=(SELECT SUM(BPO_AMT) FROM tphct02 WHERE BPO_ID='{bpo_id}' AND ALIVE_FLAG='1'), "
            f"BPO_NOTAX_AMT=(SELECT SUM(BPO_NOTAX_AMT) FROM tphct02 WHERE BPO_ID='{bpo_id}' AND ALIVE_FLAG='1'), "
            f"OPS_REMARK='{ops_remark}' "
            f"WHERE BPO_ID='{bpo_id}' AND ALIVE_FLAG='1';"
        )
        sql.append(main_stmt)

    # 回退语句部分
    sql.append("2、回退语句")
    if orig_price is not None and orig_quantity is not None:
        rollback_stmt = (
            "UPDATE tphct02 SET "
            f"BPO_QTY={orig_quantity}, "
            f"BPO_PRICE={orig_price}, "
            f"BPO_AMT={orig_price}*{orig_quantity}, "
            f"BPO_NOTAX_PRICE={orig_price}/(1+TAX_RATE), "
            f"BPO_NOTAX_AMT=({orig_price}*{orig_quantity})/(1+TAX_RATE), "
            f"OPS_REMARK='' "
            f"WHERE BPO_LINE_ID IN ({line_id_in}) AND ALIVE_FLAG='1';"
        )
        sql.append(rollback_stmt)
    elif orig_price is not None and orig_quantity is None:
        rollback_stmt = (
            "UPDATE tphct02 SET "
            f"BPO_PRICE={orig_price}, "
            f"BPO_AMT={orig_price}*BPO_QTY, "
            f"BPO_NOTAX_PRICE={orig_price}/(1+TAX_RATE), "
            f"BPO_NOTAX_AMT=({orig_price}*BPO_QTY)/(1+TAX_RATE), "
            f"OPS_REMARK='' "
            f"WHERE BPO_LINE_ID IN ({line_id_in}) AND ALIVE_FLAG='1';"
        )
        sql.append(rollback_stmt)
    elif orig_price is None and orig_quantity is not None:
        rollback_stmt = (
            "UPDATE tphct02 SET "
            f"BPO_QTY={orig_quantity}, "
            f"BPO_AMT=BPO_PRICE*{orig_quantity}, "
            f"BPO_NOTAX_AMT=(BPO_PRICE*{orig_quantity})/(1+TAX_RATE), "
            f"OPS_REMARK='' "
            f"WHERE BPO_LINE_ID IN ({line_id_in}) AND ALIVE_FLAG='1';"
        )
        sql.append(rollback_stmt)

    # 回退合同主表
    sql.append("-- 回退合同主表")
    for i, bpo_id in enumerate(bpo_ids, 1):
        main_rollback_stmt = (
            f"UPDATE tphct01 SET "
            f"BPO_AMT=(SELECT SUM(BPO_AMT) FROM tphct02 WHERE BPO_ID='{bpo_id}' AND ALIVE_FLAG='1'), "
            f"TARGET_AMT=(SELECT SUM(BPO_AMT) FROM tphct02 WHERE BPO_ID='{bpo_id}' AND ALIVE_FLAG='1'), "
            f"BPO_NOTAX_AMT=(SELECT SUM(BPO_NOTAX_AMT) FROM tphct02 WHERE BPO_ID='{bpo_id}' AND ALIVE_FLAG='1'), "
            f"OPS_REMARK='' "
            f"WHERE BPO_ID='{bpo_id}' AND ALIVE_FLAG='1';"
        )
        sql.append(main_rollback_stmt)

    # 数据库信息
    sql.append("3.数据库")
    sql.append("ip：192.168.11.71")
    sql.append("库名：cnnc_ph")

    return "\n".join(sql)


def parse_price_excel(file):
    wb = openpyxl.load_workbook(file)
    ws = wb.active
    headers = [cell.value for cell in ws[1]]
    idx = {str(h): i for i, h in enumerate(headers)}

    def pick(alts):
        for a in alts:
            if a in idx:
                return idx[a]
        return None
    lid_idx = pick(['line_id', 'BPO_LINE_ID', '明细行ID'])
    price_idx = pick(['price', 'BPO_PRICE', '单价'])
    qty_idx = pick(['quantity', 'BPO_QTY', '数量'])
    orig_qty_idx = pick(['orig_quantity', '原数量'])
    orig_price_idx = pick(['orig_price', '原单价'])
    if lid_idx is None or price_idx is None:
        raise ValueError("Excel 缺少必要列：明细行ID/单价")
    records = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row:
            continue
        lid = row[lid_idx]
        prc = row[price_idx]
        qty = row[qty_idx] if qty_idx is not None else None
        if lid is None or prc is None:
            continue
        rec = {
            'line_id': str(lid).strip(),
            'price': prc,
            'quantity': qty,
        }
        if orig_qty_idx is not None:
            rec['orig_quantity'] = row[orig_qty_idx]
        if orig_price_idx is not None:
            rec['orig_price'] = row[orig_price_idx]
        records.append(rec)
    if not records:
        raise ValueError("Excel 中没有有效的行数据")
    return records


def generate_price_sql_bulk(records, ops_remark=None):
    sql = []
    sql.append("1、执行语句")
    for i, r in enumerate(records, 1):
        q = r.get('quantity')
        if q is not None:
            exec_stmt = (
                f"UPDATE tphct02 SET "
                f"BPO_QTY={q}, "
                f"BPO_PRICE={r['price']}, "
                f"BPO_AMT={r['price']}*{q}, "
                f"BPO_NOTAX_PRICE={r['price']}/(1+TAX_RATE), "
                f"BPO_NOTAX_AMT=({r['price']}*{q})/(1+TAX_RATE), "
                f"OPS_REMARK='{ops_remark or ''}' "
                f"WHERE BPO_LINE_ID='{r['line_id']}' AND ALIVE_FLAG='1';"
            )
        else:
            exec_stmt = (
                f"UPDATE tphct02 SET "
                f"BPO_PRICE={r['price']}, "
                f"BPO_AMT={r['price']}*BPO_QTY, "
                f"BPO_NOTAX_PRICE={r['price']}/(1+TAX_RATE), "
                f"BPO_NOTAX_AMT=({r['price']}*BPO_QTY)/(1+TAX_RATE), "
                f"OPS_REMARK='{ops_remark or ''}' "
                f"WHERE BPO_LINE_ID='{r['line_id']}' AND ALIVE_FLAG='1';"
            )
        sql.append(exec_stmt)
    bpo_ids = []
    for r in records:
        parts = r['line_id'].split('-')
        if len(parts) > 4:
            bpo_id = '-'.join(parts[:-1])
        else:
            bpo_id = '-'.join(parts[:-1]) if len(parts) > 1 else r['line_id']
        if bpo_id not in bpo_ids:
            bpo_ids.append(bpo_id)
    sql.append("-- 批量更新合同的主表汇总金额")
    for i, bpo_id in enumerate(bpo_ids, 1):
        main_stmt = (
            f"UPDATE tphct01 SET "
            f"BPO_AMT=(SELECT SUM(BPO_AMT) FROM tphct02 WHERE BPO_ID='{bpo_id}' AND ALIVE_FLAG='1'), "
            f"TARGET_AMT=(SELECT SUM(BPO_AMT) FROM tphct02 WHERE BPO_ID='{bpo_id}' AND ALIVE_FLAG='1'), "
            f"BPO_NOTAX_AMT=(SELECT SUM(BPO_NOTAX_AMT) FROM tphct02 WHERE BPO_ID='{bpo_id}' AND ALIVE_FLAG='1'), "
            f"OPS_REMARK='{ops_remark or ''}' "
            f"WHERE BPO_ID='{bpo_id}' AND ALIVE_FLAG='1';"
        )
        sql.append(main_stmt)
    sql.append("2、回退语句")
    for i, r in enumerate(records, 1):
        rq = r.get('orig_quantity')
        rp = r.get('orig_price')
        if rq is not None and rp is not None:
            rollback_stmt = (
                f"UPDATE tphct02 SET "
                f"BPO_QTY={rq}, "
                f"BPO_PRICE={rp}, "
                f"BPO_AMT={rp}*{rq}, "
                f"BPO_NOTAX_PRICE={rp}/(1+TAX_RATE), "
                f"BPO_NOTAX_AMT=({rp}*{rq})/(1+TAX_RATE), "
                f"OPS_REMARK='' "
                f"WHERE BPO_LINE_ID='{r['line_id']}' AND ALIVE_FLAG='1';"
            )
            sql.append(rollback_stmt)
        elif rp is not None and rq is None:
            rollback_stmt = (
                f"UPDATE tphct02 SET "
                f"BPO_PRICE={rp}, "
                f"BPO_AMT={rp}*BPO_QTY, "
                f"BPO_NOTAX_PRICE={rp}/(1+TAX_RATE), "
                f"BPO_NOTAX_AMT=({rp}*BPO_QTY)/(1+TAX_RATE), "
                f"OPS_REMARK='' "
                f"WHERE BPO_LINE_ID='{r['line_id']}' AND ALIVE_FLAG='1';"
            )
            sql.append(rollback_stmt)
        elif rp is None and rq is not None:
            rollback_stmt = (
                f"UPDATE tphct02 SET "
                f"BPO_QTY={rq}, "
                f"BPO_AMT=BPO_PRICE*{rq}, "
                f"BPO_NOTAX_AMT=(BPO_PRICE*{rq})/(1+TAX_RATE), "
                f"OPS_REMARK='' "
                f"WHERE BPO_LINE_ID='{r['line_id']}' AND ALIVE_FLAG='1';"
            )
            sql.append(rollback_stmt)
    sql.append("-- 回退合同主表")
    for i, bpo_id in enumerate(bpo_ids, 1):
        main_rollback_stmt = (
            f"UPDATE tphct01 SET "
            f"BPO_AMT=(SELECT SUM(BPO_AMT) FROM tphct02 WHERE BPO_ID='{bpo_id}' AND ALIVE_FLAG='1'), "
            f"TARGET_AMT=(SELECT SUM(BPO_AMT) FROM tphct02 WHERE BPO_ID='{bpo_id}' AND ALIVE_FLAG='1'), "
            f"BPO_NOTAX_AMT=(SELECT SUM(BPO_NOTAX_AMT) FROM tphct02 WHERE BPO_ID='{bpo_id}' AND ALIVE_FLAG='1'), "
            f"OPS_REMARK='' "
            f"WHERE BPO_ID='{bpo_id}' AND ALIVE_FLAG='1';"
        )
        sql.append(main_rollback_stmt)
    sql.append("3.数据库")
    sql.append("ip：192.168.11.71")
    sql.append("库名：cnnc_ph")
    return "\n".join(sql)


def parse_item_excel(file):
    wb = openpyxl.load_workbook(file)
    ws = wb.active
    headers = [cell.value for cell in ws[1]]
    idx = {str(h): i for i, h in enumerate(headers)}

    def pick(alts):
        for a in alts:
            if a in idx:
                return idx[a]
        return None
    lid_idx = pick(['line_id', 'BPO_LINE_ID', '明细行ID'])
    new_id_idx = pick(['ITEM_ID', 'item_id', '物资编码'])
    new_name_idx = pick(['ITEM_NAME', 'item_name', '物资名称'])
    new_uom_idx = pick(['ITEM_UOM', 'item_uom', '计量单位'])
    new_cat_idx = pick(['CATEGORY', 'category', '物资分类编码'])
    orig_id_idx = pick(['orig_item_id', '原物资编码'])
    orig_name_idx = pick(['orig_item_name', '原物资名称'])
    orig_uom_idx = pick(['orig_item_uom', '原计量单位'])
    orig_cat_idx = pick(['orig_category', '原物资分类编码'])
    desc_idx = pick(['描述', 'desc', '错误'])
    if lid_idx is None:
        raise ValueError("Excel 缺少必要列：明细行ID")
    records = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row:
            continue
        lid = row[lid_idx]
        if lid is None:
            continue
        rec = {'line_id': str(lid).strip()}
        if new_id_idx is not None:
            rec['new_item_id'] = normalize_item_id(row[new_id_idx])
        if new_name_idx is not None:
            rec['new_item_name'] = row[new_name_idx]
        if new_uom_idx is not None:
            rec['new_item_uom'] = row[new_uom_idx]
        if new_cat_idx is not None:
            rec['new_category'] = row[new_cat_idx]
        if orig_id_idx is not None:
            rec['orig_item_id'] = normalize_item_id(row[orig_id_idx])
        if orig_name_idx is not None:
            rec['orig_item_name'] = row[orig_name_idx]
        if orig_uom_idx is not None:
            rec['orig_item_uom'] = row[orig_uom_idx]
        if orig_cat_idx is not None:
            rec['orig_category'] = row[orig_cat_idx]
        if desc_idx is not None:
            rec['desc'] = row[desc_idx]
        records.append(rec)
    if not records:
        raise ValueError("Excel 中没有有效的行数据")
    return records


def generate_item_sql_bulk(records, ops_remark=None):
    sql = []
    sql.append("1、执行语句")
    for r in records:
        parts = []
        if r.get('new_item_id'):
            parts.append(f"ITEM_ID = '{str(r['new_item_id']).strip()}'")
        if r.get('new_item_name'):
            parts.append(f"ITEM_NAME = '{str(r['new_item_name']).strip()}'")
        if r.get('new_item_uom'):
            parts.append(f"ITEM_UOM = '{str(r['new_item_uom']).strip()}'")
        if r.get('new_category'):
            parts.append(f"CATEGORY = '{str(r['new_category']).strip()}'")
        if parts:
            stmt = (
                "UPDATE TPHCT02 "
                "SET " + ", ".join(parts) + ", "
                f"OPS_REMARK = '{ops_remark or ''}' "
                f"WHERE BPO_LINE_ID = '{r['line_id']}' "
                "AND ALIVE_FLAG = '1';"
            )
            sql.append(stmt)
    sql.append("")
    sql.append("2、回退语句")
    for r in records:
        rb = []
        if r.get('orig_item_id'):
            rb.append(f"ITEM_ID = '{str(r['orig_item_id']).strip()}'")
        if r.get('orig_item_name'):
            rb.append(f"ITEM_NAME = '{str(r['orig_item_name']).strip()}'")
        if r.get('orig_item_uom'):
            rb.append(f"ITEM_UOM = '{str(r['orig_item_uom']).strip()}'")
        if r.get('orig_category'):
            rb.append(f"CATEGORY = '{str(r['orig_category']).strip()}'")
        if rb:
            stmt = (
                "UPDATE TPHCT02 "
                "SET " + ", ".join(rb) + ", "
                f"OPS_REMARK = '' "
                f"WHERE BPO_LINE_ID = '{r['line_id']}' "
                "AND ALIVE_FLAG = '1';"
            )
            sql.append(stmt)
    sql.append("")
    sql.append("3、数据库")
    sql.append("ip：192.168.11.71")
    sql.append("库名：cnnc_ph")
    return "\n".join(sql)


def contract_item_update_view(request):
    if request.method == 'POST':
        form = ContractItemUpdateForm(request.POST, request.FILES)
        if form.is_valid():
            cd = form.cleaned_data
            # 解析OPS_REMARK
            ops_remark = parse_ops_remark(cd.get('ops_remark', ''))

            if cd.get('excel_file'):
                records = parse_item_excel(cd['excel_file'])
                success_records = []
                fail_rows = []
                debug_lines = []
                for r in records:
                    nid = normalize_item_id(r.get('new_item_id'))
                    r['new_item_id'] = nid
                    if not nid:
                        fail_rows.append({**r, 'error': '物资编码为空'})
                        debug_lines.append('new 查询编码= 空 命中=N')
                        continue
                    obj = ItemDetail.objects.filter(item_id=nid).first()
                    if obj:
                        r['new_item_name'] = r.get(
                            'new_item_name') or obj.item_name
                        r['new_item_uom'] = r.get(
                            'new_item_uom') or obj.item_uom
                        r['new_category'] = r.get(
                            'new_category') or obj.category
                        success_records.append(r)
                        debug_lines.append(
                            f"new 查询编码={nid} 命中=Y 名称={r.get('new_item_name')} 计量={r.get('new_item_uom')} 分类={r.get('new_category')}")
                    else:
                        fail_rows.append({**r, 'error': f"物资编码不存在: {nid}"})
                        debug_lines.append(f"new 查询编码={nid} 命中=N")
                sql_content = generate_item_sql_bulk(
                    success_records, ops_remark)

                now = datetime.now()
                year_month = now.strftime("%Y%m")
                day = now.strftime("%d")
                filename = f"{cd['dynamic_id']}_修改合同物资编码.sql"
                base_dir = r"D:\临时文件"
                target_dir = os.path.join(base_dir, year_month, day)
                os.makedirs(target_dir, exist_ok=True)
                filepath = os.path.join(target_dir, filename)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(sql_content)
                temp_dir = os.path.join(settings.BASE_DIR, 'temp_downloads')
                os.makedirs(temp_dir, exist_ok=True)
                download_path = os.path.join(temp_dir, filename)
                with open(download_path, 'w', encoding='utf-8') as f:
                    f.write(sql_content)
                fail_download_url = None
                if fail_rows:
                    wb = openpyxl.Workbook()
                    ws = wb.active
                    ws.title = '失败明细'
                    ws.append(['明细行ID', '物资编码', '物资名称',
                              '计量单位', '物资分类编码', '描述'])
                    for r in fail_rows:
                        ws.append([
                            r.get('line_id'),
                            r.get('new_item_id'),
                            r.get('new_item_name'),
                            r.get('new_item_uom'),
                            r.get('new_category'),
                            r.get('error')
                        ])
                    fail_name = f"{cd['dynamic_id']}_修改合同物资编码_失败.xlsx"
                    fail_path = os.path.join(temp_dir, fail_name)
                    wb.save(fail_path)
                    fail_download_url = f"/download/{fail_name}"
                session_data = {}
                for k, v in cd.items():
                    if k != 'excel_file':
                        if hasattr(v, 'to_eng_string'):
                            session_data[k] = v.to_eng_string()
                        else:
                            session_data[k] = v
                request.session['contract_item_last'] = session_data
                return render(request, 'success.html', {
                    'filepath': filepath,
                    'download_url': f"/download/{filename}",
                    'fail_download_url': fail_download_url
                })
            else:
                rec = {
                    'line_id': cd['single_line_id'],
                    'new_item_id': normalize_item_id(cd.get('new_item_id')),
                    'new_item_name': cd.get('new_item_name'),
                    'new_item_uom': cd.get('new_item_uom'),
                    'new_category': cd.get('new_category'),
                    'orig_item_id': normalize_item_id(cd.get('orig_item_id')),
                    'orig_item_name': cd.get('orig_item_name'),
                    'orig_item_uom': cd.get('orig_item_uom'),
                    'orig_category': cd.get('orig_category'),
                }
                records = [rec]

            def enrich(rec, prefix):
                iid = normalize_item_id(rec.get(f'{prefix}_item_id'))
                name = rec.get(f'{prefix}_item_name')
                uom = rec.get(f'{prefix}_item_uom')
                cat = rec.get(f'{prefix}_category')
                if iid and (not name or not uom or not cat):
                    obj = ItemDetail.objects.filter(item_id=iid).first()
                    if obj:
                        if not name:
                            rec[f'{prefix}_item_name'] = obj.item_name
                        if not uom:
                            rec[f'{prefix}_item_uom'] = obj.item_uom
                        if not cat:
                            rec[f'{prefix}_category'] = obj.category
                        rec[f'{prefix}_item_id'] = iid
                        return True
                    return False
                if iid:
                    rec[f'{prefix}_item_id'] = iid
                return True
            errors = []
            for r in records:
                if r.get('new_item_id'):
                    ok = enrich(r, 'new')
                    if not ok:
                        errors.append(f"新物资编码未找到: {r.get('new_item_id')}")
                if r.get('orig_item_id'):
                    ok = enrich(r, 'orig')
                if r.get('new_item_id') and (not r.get('new_item_name') or not r.get('new_item_uom') or not r.get('new_category')):
                    iid = normalize_item_id(r['new_item_id'])
                    if not ItemDetail.objects.filter(item_id=iid).exists():
                        errors.append("新物资编码未找到，需填写名称/计量/分类")
                if r.get('orig_item_id') and (not r.get('orig_item_name') or not r.get('orig_item_uom') or not r.get('orig_category')):
                    iid = normalize_item_id(r['orig_item_id'])
            if errors:
                form.add_error(None, "; ".join(errors))
                return render(request, 'contract_item_form.html', {'form': form})
            sql_content = generate_item_sql_bulk(records, ops_remark)
            now = datetime.now()
            year_month = now.strftime("%Y%m")
            day = now.strftime("%d")
            filename = f"{cd['dynamic_id']}_修改合同物资编码.sql"
            base_dir = r"D:\临时文件"
            target_dir = os.path.join(base_dir, year_month, day)
            os.makedirs(target_dir, exist_ok=True)
            filepath = os.path.join(target_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(sql_content)

            # 记录文件保存
            logger.info(f"SQL文件已保存: {filepath}")
            temp_dir = os.path.join(settings.BASE_DIR, 'temp_downloads')
            os.makedirs(temp_dir, exist_ok=True)
            download_path = os.path.join(temp_dir, filename)
            with open(download_path, 'w', encoding='utf-8') as f:
                f.write(sql_content)
            # 将Decimal类型转换为字符串以支持JSON序列化
            session_data = {}
            for k, v in cd.items():
                if k != 'excel_file':
                    # 处理Decimal类型
                    if hasattr(v, 'to_eng_string'):
                        session_data[k] = v.to_eng_string()
                    else:
                        session_data[k] = v
            request.session['contract_item_last'] = session_data
            return render(request, 'success.html', {
                'filepath': filepath,
                'download_url': f"/download/{filename}"
            })
    else:
        if request.GET.get('clear'):
            request.session.pop('contract_item_last', None)
            form = ContractItemUpdateForm()
        else:
            initial = request.session.get('contract_item_last')
            form = ContractItemUpdateForm(initial=initial)
    return render(request, 'contract_item_form.html', {'form': form})


def download_item_template(request):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = '模板'
    ws.append(['明细行ID', '物资编码', '物资名称', '计量单位', '物资分类编码',
              '原物资编码', '原物资名称', '原计量单位', '原物资分类编码', '描述'])
    ws.append(['BPO-EXAMPLE-000001', '01607733', '鞋套',
              '双', '430798', None, None, None, None, None])
    guide = wb.create_sheet('说明')
    guide.append(['填写说明'])
    guide.append(['若物资编码在基础数据不存在，请补充“物资名称/计量单位/物资分类编码”。'])
    guide.append(['系统将按物资编码自动补齐上述信息；编码不存在时将校验失败。'])
    bio = io.BytesIO()
    wb.save(bio)
    bio.seek(0)
    response = FileResponse(bio, as_attachment=True,
                            filename='contract_item_template.xlsx')
    response['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    return response


def download_price_template(request):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = '模板'
    ws.append(['明细行ID', '单价', '数量', '原数量', '原单价'])
    ws.append(['BPO-EXAMPLE-000001', 100, 1, None, None])
    bio = io.BytesIO()
    wb.save(bio)
    bio.seek(0)
    response = FileResponse(bio, as_attachment=True,
                            filename='contract_price_template.xlsx')
    response['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    return response


def contract_detail_price_view(request):
    """
    处理合同明细单价修改的视图函数
    """
    if request.method == 'POST':
        form = ContractDetailPriceForm(request.POST, request.FILES)
        if form.is_valid():
            cd = form.cleaned_data
            log_view_input("合同明细单价修改", cd)

            # 解析OPS_REMARK
            ops_remark = parse_ops_remark(cd.get('ops_remark', ''))

            if cd.get('excel_file'):
                records = parse_price_excel(cd['excel_file'])
                sql_content = generate_price_sql_bulk(records, ops_remark)
            else:
                new_quantity = cd.get('new_quantity')
                new_price = cd.get('new_price')
                orig_quantity = cd.get('orig_quantity')
                orig_price = cd.get('orig_price')
                if not new_price or not cd.get('single_line_id'):
                    form.add_error(None, "单条模式需填写单价和明细行ID；数量可不填")
                    return render(request, 'contract_price_form.html', {'form': form})
                line_ids = [cd['single_line_id']]
                sql_content = generate_price_sql(
                    line_ids, new_quantity, new_price, orig_quantity, orig_price, ops_remark)

            # 生成文件名
            now = datetime.now()
            year_month = now.strftime("%Y%m")
            day = now.strftime("%d")
            filename = f"{cd['dynamic_id']}_修改合同明细单价.sql"

            # 保存到临时文件
            base_dir = r"D:\临时文件"
            target_dir = os.path.join(base_dir, year_month, day)
            os.makedirs(target_dir, exist_ok=True)
            filepath = os.path.join(target_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(sql_content)

            # 记录文件保存
            logger.info(f"SQL文件已保存: {filepath}")

            # 保存到下载目录
            temp_dir = os.path.join(settings.BASE_DIR, 'temp_downloads')
            os.makedirs(temp_dir, exist_ok=True)
            download_path = os.path.join(temp_dir, filename)
            with open(download_path, 'w', encoding='utf-8') as f:
                f.write(sql_content)

            # 将Decimal类型转换为字符串以支持JSON序列化
            session_data = {}
            for k, v in cd.items():
                if k != 'excel_file':
                    # 处理Decimal类型
                    if hasattr(v, 'to_eng_string'):
                        session_data[k] = v.to_eng_string()
                    else:
                        session_data[k] = v
            request.session['contract_price_last'] = session_data
            return render(request, 'success.html', {
                'filepath': filepath,
                'download_url': f'/download/{filename}'
            })
    else:
        if request.GET.get('clear'):
            request.session.pop('contract_price_last', None)
            form = ContractDetailPriceForm()
        else:
            initial = request.session.get('contract_price_last')
            form = ContractDetailPriceForm(initial=initial)

    return render(request, 'contract_price_form.html', {
        'form': form,
        'active_menu': 'contract_price',
        'sidebar_groups': SIDEBAR_GROUPS,
    })


def system_config_view(request):
    saved = False
    error = None
    if request.method == 'POST':
        try:
            cfg = get_config()
            mods = cfg.get('MERGE_MODULES', {})
            names = ['price', 'item', 'unit', 'budget', 'gov',
                     'importance', 'enddate', 'erp', 'price_type']
            for n in names:
                mods[n] = (request.POST.get(f'mod_{n}') == 'on')
            cfg['MERGE_MODULES'] = mods
            set_config(cfg)
            saved = True
        except Exception as e:
            error = str(e)
    cfg = get_config()
    return render(request, 'system_config.html', {
        'cfg': cfg,
        'active_menu': 'system_config',
        'sidebar_groups': SIDEBAR_GROUPS,
        'saved': saved,
        'error': error,
    })


def generate_sql(records, **kwargs):
    update_drafting = kwargs.get('update_drafting', False)
    update_contract_party = kwargs.get('update_contract_party', False)
    old_drafting_id = kwargs.get('old_drafting_id')
    old_drafting_name = kwargs.get('old_drafting_name')
    old_party_id = kwargs.get('old_party_id')
    old_party_name = kwargs.get('old_party_name')

    # 获取并解析ops_remark
    ops_remark = parse_ops_remark(kwargs.get('ops_remark', ''))

    sql = []
    sql.append("1、执行语句")
    for r in records:
        parts = []
        if update_drafting:
            ndid = r.get('new_drafting_id', kwargs.get('new_drafting_id'))
            ndnm = r.get('new_drafting_name', kwargs.get('new_drafting_name'))
            if not ndid and ndnm:
                code = extract_company_code(ndnm)
                if code:
                    ndid = code
            if ndid:
                parts.append(f"PRIMARY_CONTRACT_DRAFTING_UNIT='{ndid}'")
            if ndnm:
                parts.append(
                    f"PRIMARY_CONTRACT_DRAFTING_UNIT_NAME='{extract_company_name(ndnm)}'")
        if update_contract_party:
            npid = r.get('new_party_id', kwargs.get('new_party_id'))
            npnm = r.get('new_party_name', kwargs.get('new_party_name'))
            if not npid and npnm:
                code = extract_company_code(npnm)
                if code:
                    npid = code
            if npid:
                parts.append(f"CONTRACT_PARTY_ID='{npid}'")
            if npnm:
                parts.append(
                    f"CONTRACT_PARTY_NAME='{extract_company_name(npnm)}'")
        if parts:
            set_clause = ', '.join(parts)
            sql.append(
                f"update tprfa03 set {set_clause}, OPS_REMARK='{ops_remark}' where PURCHASE_SCHEME_NO='{r['scheme']}';")
            sql.append(
                f"update tprxj05 set {set_clause}, OPS_REMARK='{ops_remark}' where PURCHASE_SCHEME_NO='{r['scheme']}' AND INQ_ID='{r['inquiry']}';")
            sql.append(
                f"update tprnq03 set {set_clause}, OPS_REMARK='{ops_remark}' where PURCHASE_SCHEME_NO='{r['scheme']}' AND INQ_ID='{r['inquiry']}' AND sign_id='{r['result']}';")

    sql.append("2.回退语句")
    for r in records:
        rb_parts = []
        if update_drafting:
            odid = r.get('orig_drafting_id', old_drafting_id)
            odnm = r.get('orig_drafting_name', old_drafting_name)
            if not odid and odnm:
                code = extract_company_code(odnm)
                if code:
                    odid = code
            if odid:
                rb_parts.append(f"PRIMARY_CONTRACT_DRAFTING_UNIT='{odid}'")
            if odnm:
                rb_parts.append(
                    f"PRIMARY_CONTRACT_DRAFTING_UNIT_NAME='{extract_company_name(odnm)}'")
        if update_contract_party:
            opid = r.get('orig_party_id', old_party_id)
            opnm = r.get('orig_party_name', old_party_name)
            if not opid and opnm:
                code = extract_company_code(opnm)
                if code:
                    opid = code
            if opid:
                rb_parts.append(f"CONTRACT_PARTY_ID='{opid}'")
            if opnm:
                rb_parts.append(
                    f"CONTRACT_PARTY_NAME='{extract_company_name(opnm)}'")
        if rb_parts:
            rb_clause = ', '.join(rb_parts)
            sql.append(
                f"update tprfa03 set {rb_clause}, OPS_REMARK='' where PURCHASE_SCHEME_NO='{r['scheme']}';")
            sql.append(
                f"update tprxj05 set {rb_clause}, OPS_REMARK='' where PURCHASE_SCHEME_NO='{r['scheme']}' AND INQ_ID='{r['inquiry']}';")
            sql.append(
                f"update tprnq03 set {rb_clause}, OPS_REMARK='' where PURCHASE_SCHEME_NO='{r['scheme']}' AND INQ_ID='{r['inquiry']}' AND sign_id='{r['result']}';")

    sql.append("3.数据库")
    sql.append("ip：192.168.11.76")
    sql.append("库名：cnnc_ph")
    return "\n".join(sql)


def parse_excel(file):
    wb = openpyxl.load_workbook(file)
    ws = wb.active
    records = []
    headers = [cell.value for cell in ws[1]]
    hset = {str(h) if h is not None else '' for h in headers}
    idx = {str(h): i for i, h in enumerate(headers)}
    scheme_alts = ['scheme_no', 'PURCHASE_SCHEME_NO',
                   'purchase_scheme_no', '采购方案编号']
    inquiry_alts = ['inquiry_no', 'inq_id', 'INQ_ID', '询价单编号']
    result_alts = ['result_no', 'sign_id', 'SIGN_ID', '定标结果编号']

    def pick(alts):
        for a in alts:
            if a in idx:
                return idx[a]
        return None
    s_idx = pick(scheme_alts)
    i_idx = pick(inquiry_alts)
    r_idx = pick(result_alts)
    if s_idx is None or i_idx is None or r_idx is None:
        raise ValueError("Excel 缺少必要列：方案、询价、定标")
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not any(row):
            continue
        rec = {
            'scheme': row[s_idx],
            'inquiry': row[i_idx],
            'result': row[r_idx]
        }
        if not all(rec.values()):
            continue
        ndid = None
        ndnm = None
        npid = None
        npnm = None
        odid = None
        odnm = None
        opid = None
        opnm = None
        for k in ['new_drafting_id', '新起草单位ID']:
            if k in idx:
                ndid = row[idx[k]]
                break
        for k in ['new_drafting_name', '新起草单位名称', '组织机构名称']:
            if k in idx:
                ndnm = row[idx[k]]
                break
        for k in ['new_party_id', '新签约主体ID']:
            if k in idx:
                npid = row[idx[k]]
                break
        for k in ['new_party_name', '新签约主体名称']:
            if k in idx:
                npnm = row[idx[k]]
                break
        for k in ['orig_drafting_id', '原起草单位ID']:
            if k in idx:
                odid = row[idx[k]]
                break
        for k in ['orig_drafting_name', '原起草单位名称', '组织机构名称']:
            if k in idx:
                odnm = row[idx[k]]
                break
        for k in ['orig_party_id', '原签约主体ID']:
            if k in idx:
                opid = row[idx[k]]
                break
        for k in ['orig_party_name', '原签约主体名称']:
            if k in idx:
                opnm = row[idx[k]]
                break
        if ndid is not None:
            rec['new_drafting_id'] = ndid
        if ndnm is not None:
            rec['new_drafting_name'] = ndnm
        if npid is not None:
            rec['new_party_id'] = npid
        if npnm is not None:
            rec['new_party_name'] = npnm
        if odid is not None:
            rec['orig_drafting_id'] = odid
        if odnm is not None:
            rec['orig_drafting_name'] = odnm
        if opid is not None:
            rec['orig_party_id'] = opid
        if opnm is not None:
            rec['orig_party_name'] = opnm
        records.append(rec)
    return records


def unit_change_view(request):
    if request.method == 'POST':
        form = UnitChangeForm(request.POST, request.FILES)
        if form.is_valid():
            cd = form.cleaned_data

            if cd.get('excel_file'):
                records = parse_excel(cd['excel_file'])
            else:
                records = [{
                    'scheme': cd['scheme_no'],
                    'inquiry': cd['inquiry_no'],
                    'result': cd['result_no']
                }]

            update_drafting = bool(
                cd.get('new_drafting_id') or cd.get('new_drafting_name'))
            update_contract_party = bool(
                cd.get('new_party_id') or cd.get('new_party_name'))

            # 解析OPS_REMARK
            ops_remark = parse_ops_remark(cd.get('ops_remark', ''))

            sql_content = generate_sql(
                records,
                update_drafting=update_drafting,
                update_contract_party=update_contract_party,
                old_drafting_id=cd.get('old_drafting_id'),
                old_drafting_name=cd.get('old_drafting_name'),
                new_drafting_id=cd.get('new_drafting_id'),
                new_drafting_name=cd.get('new_drafting_name'),
                old_party_id=cd.get('old_party_id'),
                old_party_name=cd.get('old_party_name'),
                new_party_id=cd.get('new_party_id'),
                new_party_name=cd.get('new_party_name'),
                ops_remark=ops_remark
            )

            # 记录SQL生成结果
            logger.info(
                f"SQL生成完成: 更新起草单位={update_drafting}, 更新签约主体={update_contract_party}, SQL长度={len(sql_content)}")

            now = datetime.now()
            year_month = now.strftime("%Y%m")
            day = now.strftime("%d")
            if update_drafting and update_contract_party:
                suffix = "修改起草单位和签约主体"
            elif update_drafting:
                suffix = "修改起草单位"
            elif update_contract_party:
                suffix = "修改签约主体"
            else:
                suffix = "修改合同单位信息"
            filename = f"{cd['dynamic_id']}_{suffix}.sql"

            base_dir = r"D:\临时文件"
            target_dir = os.path.join(base_dir, year_month, day)
            os.makedirs(target_dir, exist_ok=True)
            filepath = os.path.join(target_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(sql_content)

            # 记录文件保存
            logger.info(f"SQL文件已保存: {filepath}")

            temp_dir = os.path.join(settings.BASE_DIR, 'temp_downloads')
            os.makedirs(temp_dir, exist_ok=True)
            download_path = os.path.join(temp_dir, filename)
            with open(download_path, 'w', encoding='utf-8') as f:
                f.write(sql_content)

            # 将Decimal类型转换为字符串以支持JSON序列化
            session_data = {}
            for k, v in cd.items():
                if k != 'excel_file':
                    # 处理Decimal类型
                    if hasattr(v, 'to_eng_string'):
                        session_data[k] = v.to_eng_string()
                    else:
                        session_data[k] = v
            request.session['unit_change_last'] = session_data
            return render(request, 'success.html', {
                'filepath': filepath,
                'download_url': f'/download/{filename}'
            })
    else:
        if request.GET.get('clear'):
            request.session.pop('unit_change_last', None)
            form = UnitChangeForm()
        else:
            initial = request.session.get('unit_change_last')
            form = UnitChangeForm(initial=initial)

    return render(request, 'unit_change_form.html', {'form': form})


def download_sql(request, filename):
    file_path = os.path.join(settings.BASE_DIR, 'temp_downloads', filename)
    if os.path.exists(file_path):
        response = FileResponse(open(file_path, 'rb'),
                                as_attachment=True, filename=filename)
        return response
    else:
        return HttpResponse("文件不存在", status=404)


def generate_price_sql(line_ids, new_quantity, new_price, orig_quantity=None, orig_price=None, ops_remark=''):
    line_id_str = "', '".join(line_ids)
    line_id_in = f"'{line_id_str}'"
    sql = []
    sql.append("1、执行语句")

    # 解析操作备注
    ops_remark = parse_ops_remark(ops_remark)
    if new_quantity is not None:
        stmt = (
            "UPDATE tphct02 SET "
            f"BPO_QTY={new_quantity}, "
            f"BPO_PRICE={new_price}, "
            f"BPO_AMT={new_price}*{new_quantity}, "
            f"BPO_NOTAX_PRICE={new_price}/(1+TAX_RATE), "
            f"BPO_NOTAX_AMT=({new_price}*{new_quantity})/(1+TAX_RATE), "
            f"OPS_REMARK='{ops_remark}' "
            f"WHERE BPO_LINE_ID IN ({line_id_in}) AND ALIVE_FLAG='1';"
        )
    else:
        stmt = (
            "UPDATE tphct02 SET "
            f"BPO_PRICE={new_price}, "
            f"BPO_AMT={new_price}*BPO_QTY, "
            f"BPO_NOTAX_PRICE={new_price}/(1+TAX_RATE), "
            f"BPO_NOTAX_AMT=({new_price}*BPO_QTY)/(1+TAX_RATE), "
            f"OPS_REMARK='{ops_remark}' "
            f"WHERE BPO_LINE_ID IN ({line_id_in}) AND ALIVE_FLAG='1';"
        )
    sql.append(stmt)

    # 获取唯一的BPO_ID列表
    bpo_ids = []
    for line_id in line_ids:
        # 从line_id中提取BPO_ID（假设格式为 BPO_ID-000001）
        bpo_id_parts = line_id.split('-')
        if len(bpo_id_parts) > 4:  # 处理包含多个连字符的情况
            bpo_id = '-'.join(bpo_id_parts[:-1])
        else:
            bpo_id = '-'.join(bpo_id_parts[:-1]
                              ) if len(bpo_id_parts) > 1 else line_id
        if bpo_id not in bpo_ids:
            bpo_ids.append(bpo_id)

    # 批量更新合同主表汇总金额
    sql.append("-- 批量更新合同的主表汇总金额")
    for i, bpo_id in enumerate(bpo_ids, 1):
        main_stmt = (
            f"UPDATE tphct01 SET "
            f"BPO_AMT=(SELECT SUM(BPO_AMT) FROM tphct02 WHERE BPO_ID='{bpo_id}' AND ALIVE_FLAG='1'), "
            f"TARGET_AMT=(SELECT SUM(BPO_AMT) FROM tphct02 WHERE BPO_ID='{bpo_id}' AND ALIVE_FLAG='1'), "
            f"BPO_NOTAX_AMT=(SELECT SUM(BPO_NOTAX_AMT) FROM tphct02 WHERE BPO_ID='{bpo_id}' AND ALIVE_FLAG='1'), "
            f"OPS_REMARK='{ops_remark}' "
            f"WHERE BPO_ID='{bpo_id}' AND ALIVE_FLAG='1';"
        )
        sql.append(main_stmt)

    # 回退语句部分
    sql.append("2、回退语句")
    if orig_price is not None and orig_quantity is not None:
        rollback_stmt = (
            "UPDATE tphct02 SET "
            f"BPO_QTY={orig_quantity}, "
            f"BPO_PRICE={orig_price}, "
            f"BPO_AMT={orig_price}*{orig_quantity}, "
            f"BPO_NOTAX_PRICE={orig_price}/(1+TAX_RATE), "
            f"BPO_NOTAX_AMT=({orig_price}*{orig_quantity})/(1+TAX_RATE), "
            f"OPS_REMARK='' "
            f"WHERE BPO_LINE_ID IN ({line_id_in}) AND ALIVE_FLAG='1';"
        )
        sql.append(rollback_stmt)
    elif orig_price is not None and orig_quantity is None:
        rollback_stmt = (
            "UPDATE tphct02 SET "
            f"BPO_PRICE={orig_price}, "
            f"BPO_AMT={orig_price}*BPO_QTY, "
            f"BPO_NOTAX_PRICE={orig_price}/(1+TAX_RATE), "
            f"BPO_NOTAX_AMT=({orig_price}*BPO_QTY)/(1+TAX_RATE), "
            f"OPS_REMARK='' "
            f"WHERE BPO_LINE_ID IN ({line_id_in}) AND ALIVE_FLAG='1';"
        )
        sql.append(rollback_stmt)
    elif orig_price is None and orig_quantity is not None:
        rollback_stmt = (
            "UPDATE tphct02 SET "
            f"BPO_QTY={orig_quantity}, "
            f"BPO_AMT=BPO_PRICE*{orig_quantity}, "
            f"BPO_NOTAX_AMT=(BPO_PRICE*{orig_quantity})/(1+TAX_RATE), "
            f"OPS_REMARK='' "
            f"WHERE BPO_LINE_ID IN ({line_id_in}) AND ALIVE_FLAG='1';"
        )
        sql.append(rollback_stmt)

    # 回退合同主表
    sql.append("-- 回退合同主表")
    for i, bpo_id in enumerate(bpo_ids, 1):
        main_rollback_stmt = (
            f"UPDATE tphct01 SET "
            f"BPO_AMT=(SELECT SUM(BPO_AMT) FROM tphct02 WHERE BPO_ID='{bpo_id}' AND ALIVE_FLAG='1'), "
            f"TARGET_AMT=(SELECT SUM(BPO_AMT) FROM tphct02 WHERE BPO_ID='{bpo_id}' AND ALIVE_FLAG='1'), "
            f"BPO_NOTAX_AMT=(SELECT SUM(BPO_NOTAX_AMT) FROM tphct02 WHERE BPO_ID='{bpo_id}' AND ALIVE_FLAG='1'), "
            f"OPS_REMARK='' "
            f"WHERE BPO_ID='{bpo_id}' AND ALIVE_FLAG='1';"
        )
        sql.append(main_rollback_stmt)

    # 数据库信息
    sql.append("3.数据库")
    sql.append("ip：192.168.11.71")
    sql.append("库名：cnnc_ph")

    return "\n".join(sql)


def parse_price_excel(file):
    wb = openpyxl.load_workbook(file)
    ws = wb.active
    headers = [cell.value for cell in ws[1]]
    idx = {str(h): i for i, h in enumerate(headers)}

    def pick(alts):
        for a in alts:
            if a in idx:
                return idx[a]
        return None
    lid_idx = pick(['line_id', 'BPO_LINE_ID', '明细行ID'])
    price_idx = pick(['price', 'BPO_PRICE', '单价'])
    qty_idx = pick(['quantity', 'BPO_QTY', '数量'])
    orig_qty_idx = pick(['orig_quantity', '原数量'])
    orig_price_idx = pick(['orig_price', '原单价'])
    if lid_idx is None or price_idx is None:
        raise ValueError("Excel 缺少必要列：明细行ID/单价")
    records = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row:
            continue
        lid = row[lid_idx]
        prc = row[price_idx]
        qty = row[qty_idx] if qty_idx is not None else None
        if lid is None or prc is None:
            continue
        rec = {
            'line_id': str(lid).strip(),
            'price': prc,
            'quantity': qty,
        }
        if orig_qty_idx is not None:
            rec['orig_quantity'] = row[orig_qty_idx]
        if orig_price_idx is not None:
            rec['orig_price'] = row[orig_price_idx]
        records.append(rec)
    if not records:
        raise ValueError("Excel 中没有有效的行数据")
    return records


def generate_price_sql_bulk(records, ops_remark=None):
    sql = []
    sql.append("1、执行语句")
    for i, r in enumerate(records, 1):
        q = r.get('quantity')
        if q is not None:
            exec_stmt = (
                f"UPDATE tphct02 SET "
                f"BPO_QTY={q}, "
                f"BPO_PRICE={r['price']}, "
                f"BPO_AMT={r['price']}*{q}, "
                f"BPO_NOTAX_PRICE={r['price']}/(1+TAX_RATE), "
                f"BPO_NOTAX_AMT=({r['price']}*{q})/(1+TAX_RATE), "
                f"OPS_REMARK='{ops_remark or ''}' "
                f"WHERE BPO_LINE_ID='{r['line_id']}' AND ALIVE_FLAG='1';"
            )
        else:
            exec_stmt = (
                f"UPDATE tphct02 SET "
                f"BPO_PRICE={r['price']}, "
                f"BPO_AMT={r['price']}*BPO_QTY, "
                f"BPO_NOTAX_PRICE={r['price']}/(1+TAX_RATE), "
                f"BPO_NOTAX_AMT=({r['price']}*BPO_QTY)/(1+TAX_RATE), "
                f"OPS_REMARK='{ops_remark or ''}' "
                f"WHERE BPO_LINE_ID='{r['line_id']}' AND ALIVE_FLAG='1';"
            )
        sql.append(exec_stmt)
    bpo_ids = []
    for r in records:
        parts = r['line_id'].split('-')
        if len(parts) > 4:
            bpo_id = '-'.join(parts[:-1])
        else:
            bpo_id = '-'.join(parts[:-1]) if len(parts) > 1 else r['line_id']
        if bpo_id not in bpo_ids:
            bpo_ids.append(bpo_id)
    sql.append("-- 批量更新合同的主表汇总金额")
    for i, bpo_id in enumerate(bpo_ids, 1):
        main_stmt = (
            f"UPDATE tphct01 SET "
            f"BPO_AMT=(SELECT SUM(BPO_AMT) FROM tphct02 WHERE BPO_ID='{bpo_id}' AND ALIVE_FLAG='1'), "
            f"TARGET_AMT=(SELECT SUM(BPO_AMT) FROM tphct02 WHERE BPO_ID='{bpo_id}' AND ALIVE_FLAG='1'), "
            f"BPO_NOTAX_AMT=(SELECT SUM(BPO_NOTAX_AMT) FROM tphct02 WHERE BPO_ID='{bpo_id}' AND ALIVE_FLAG='1'), "
            f"OPS_REMARK='{ops_remark or ''}' "
            f"WHERE BPO_ID='{bpo_id}' AND ALIVE_FLAG='1';"
        )
        sql.append(main_stmt)
    sql.append("2、回退语句")
    for i, r in enumerate(records, 1):
        rq = r.get('orig_quantity')
        rp = r.get('orig_price')
        if rq is not None and rp is not None:
            rollback_stmt = (
                f"UPDATE tphct02 SET "
                f"BPO_QTY={rq}, "
                f"BPO_PRICE={rp}, "
                f"BPO_AMT={rp}*{rq}, "
                f"BPO_NOTAX_PRICE={rp}/(1+TAX_RATE), "
                f"BPO_NOTAX_AMT=({rp}*{rq})/(1+TAX_RATE), "
                f"OPS_REMARK='' "
                f"WHERE BPO_LINE_ID='{r['line_id']}' AND ALIVE_FLAG='1';"
            )
            sql.append(rollback_stmt)
        elif rp is not None and rq is None:
            rollback_stmt = (
                f"UPDATE tphct02 SET "
                f"BPO_PRICE={rp}, "
                f"BPO_AMT={rp}*BPO_QTY, "
                f"BPO_NOTAX_PRICE={rp}/(1+TAX_RATE), "
                f"BPO_NOTAX_AMT=({rp}*BPO_QTY)/(1+TAX_RATE), "
                f"OPS_REMARK='' "
                f"WHERE BPO_LINE_ID='{r['line_id']}' AND ALIVE_FLAG='1';"
            )
            sql.append(rollback_stmt)
        elif rp is None and rq is not None:
            rollback_stmt = (
                f"UPDATE tphct02 SET "
                f"BPO_QTY={rq}, "
                f"BPO_AMT=BPO_PRICE*{rq}, "
                f"BPO_NOTAX_AMT=(BPO_PRICE*{rq})/(1+TAX_RATE), "
                f"OPS_REMARK='' "
                f"WHERE BPO_LINE_ID='{r['line_id']}' AND ALIVE_FLAG='1';"
            )
            sql.append(rollback_stmt)
    sql.append("-- 回退合同主表")
    for i, bpo_id in enumerate(bpo_ids, 1):
        main_rollback_stmt = (
            f"UPDATE tphct01 SET "
            f"BPO_AMT=(SELECT SUM(BPO_AMT) FROM tphct02 WHERE BPO_ID='{bpo_id}' AND ALIVE_FLAG='1'), "
            f"TARGET_AMT=(SELECT SUM(BPO_AMT) FROM tphct02 WHERE BPO_ID='{bpo_id}' AND ALIVE_FLAG='1'), "
            f"BPO_NOTAX_AMT=(SELECT SUM(BPO_NOTAX_AMT) FROM tphct02 WHERE BPO_ID='{bpo_id}' AND ALIVE_FLAG='1'), "
            f"OPS_REMARK='' "
            f"WHERE BPO_ID='{bpo_id}' AND ALIVE_FLAG='1';"
        )
        sql.append(main_rollback_stmt)
    sql.append("3.数据库")
    sql.append("ip：192.168.11.71")
    sql.append("库名：cnnc_ph")
    return "\n".join(sql)


def parse_item_excel(file):
    wb = openpyxl.load_workbook(file)
    ws = wb.active
    headers = [cell.value for cell in ws[1]]
    idx = {str(h): i for i, h in enumerate(headers)}

    def pick(alts):
        for a in alts:
            if a in idx:
                return idx[a]
        return None
    lid_idx = pick(['line_id', 'BPO_LINE_ID', '明细行ID'])
    new_id_idx = pick(['ITEM_ID', 'item_id', '物资编码'])
    new_name_idx = pick(['ITEM_NAME', 'item_name', '物资名称'])
    new_uom_idx = pick(['ITEM_UOM', 'item_uom', '计量单位'])
    new_cat_idx = pick(['CATEGORY', 'category', '物资分类编码'])
    orig_id_idx = pick(['orig_item_id', '原物资编码'])
    orig_name_idx = pick(['orig_item_name', '原物资名称'])
    orig_uom_idx = pick(['orig_item_uom', '原计量单位'])
    orig_cat_idx = pick(['orig_category', '原物资分类编码'])
    desc_idx = pick(['描述', 'desc', '错误'])
    if lid_idx is None:
        raise ValueError("Excel 缺少必要列：明细行ID")
    records = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row:
            continue
        lid = row[lid_idx]
        if lid is None:
            continue
        rec = {'line_id': str(lid).strip()}
        if new_id_idx is not None:
            rec['new_item_id'] = normalize_item_id(row[new_id_idx])
        if new_name_idx is not None:
            rec['new_item_name'] = row[new_name_idx]
        if new_uom_idx is not None:
            rec['new_item_uom'] = row[new_uom_idx]
        if new_cat_idx is not None:
            rec['new_category'] = row[new_cat_idx]
        if orig_id_idx is not None:
            rec['orig_item_id'] = normalize_item_id(row[orig_id_idx])
        if orig_name_idx is not None:
            rec['orig_item_name'] = row[orig_name_idx]
        if orig_uom_idx is not None:
            rec['orig_item_uom'] = row[orig_uom_idx]
        if orig_cat_idx is not None:
            rec['orig_category'] = row[orig_cat_idx]
        if desc_idx is not None:
            rec['desc'] = row[desc_idx]
        records.append(rec)
    if not records:
        raise ValueError("Excel 中没有有效的行数据")
    return records


def generate_item_sql_bulk(records, ops_remark=None):
    sql = []
    sql.append("1、执行语句")
    for r in records:
        parts = []
        if r.get('new_item_id'):
            parts.append(f"ITEM_ID = '{str(r['new_item_id']).strip()}'")
        if r.get('new_item_name'):
            parts.append(f"ITEM_NAME = '{str(r['new_item_name']).strip()}'")
        if r.get('new_item_uom'):
            parts.append(f"ITEM_UOM = '{str(r['new_item_uom']).strip()}'")
        if r.get('new_category'):
            parts.append(f"CATEGORY = '{str(r['new_category']).strip()}'")
        if parts:
            stmt = (
                "UPDATE TPHCT02 "
                "SET " + ", ".join(parts) + ", "
                f"OPS_REMARK = '{ops_remark or ''}' "
                f"WHERE BPO_LINE_ID = '{r['line_id']}' "
                "AND ALIVE_FLAG = '1';"
            )
            sql.append(stmt)
    sql.append("")
    sql.append("2、回退语句")
    for r in records:
        rb = []
        if r.get('orig_item_id'):
            rb.append(f"ITEM_ID = '{str(r['orig_item_id']).strip()}'")
        if r.get('orig_item_name'):
            rb.append(f"ITEM_NAME = '{str(r['orig_item_name']).strip()}'")
        if r.get('orig_item_uom'):
            rb.append(f"ITEM_UOM = '{str(r['orig_item_uom']).strip()}'")
        if r.get('orig_category'):
            rb.append(f"CATEGORY = '{str(r['orig_category']).strip()}'")
        if rb:
            stmt = (
                "UPDATE TPHCT02 "
                "SET " + ", ".join(rb) + ", "
                f"OPS_REMARK = '' "
                f"WHERE BPO_LINE_ID = '{r['line_id']}' "
                "AND ALIVE_FLAG = '1';"
            )
            sql.append(stmt)
    sql.append("")
    sql.append("3、数据库")
    sql.append("ip：192.168.11.71")
    sql.append("库名：cnnc_ph")
    return "\n".join(sql)


def contract_item_update_view(request):
    if request.method == 'POST':
        form = ContractItemUpdateForm(request.POST, request.FILES)
        if form.is_valid():
            cd = form.cleaned_data
            # 解析OPS_REMARK
            ops_remark = parse_ops_remark(cd.get('ops_remark', ''))

            if cd.get('excel_file'):
                records = parse_item_excel(cd['excel_file'])
            else:
                rec = {
                    'line_id': cd['single_line_id'],
                    'new_item_id': normalize_item_id(cd.get('new_item_id')),
                    'new_item_name': cd.get('new_item_name'),
                    'new_item_uom': cd.get('new_item_uom'),
                    'new_category': cd.get('new_category'),
                    'orig_item_id': normalize_item_id(cd.get('orig_item_id')),
                    'orig_item_name': cd.get('orig_item_name'),
                    'orig_item_uom': cd.get('orig_item_uom'),
                    'orig_category': cd.get('orig_category'),
                }
                records = [rec]
            debug_lines = []

            def enrich(rec, prefix):
                iid = normalize_item_id(rec.get(f'{prefix}_item_id'))
                name = rec.get(f'{prefix}_item_name')
                uom = rec.get(f'{prefix}_item_uom')
                cat = rec.get(f'{prefix}_category')
                if iid and (not name or not uom or not cat):
                    obj = ItemDetail.objects.filter(item_id=iid).first()
                    if obj:
                        if not name:
                            rec[f'{prefix}_item_name'] = obj.item_name
                        if not uom:
                            rec[f'{prefix}_item_uom'] = obj.item_uom
                        if not cat:
                            rec[f'{prefix}_category'] = obj.category
                        rec[f'{prefix}_item_id'] = iid
                        debug_lines.append(f"{prefix} 查询编码={iid} 命中=Y 名称={rec.get(f'{prefix}_item_name')} 计量={
                                           rec.get(f'{prefix}_item_uom')} 分类={rec.get(f'{prefix}_category')}")
                        return True
                    debug_lines.append(f"{prefix} 查询编码={iid} 命中=N")
                    return False
                if iid:
                    rec[f'{prefix}_item_id'] = iid
                    debug_lines.append(f"{prefix} 查询编码={iid} 已提供完整信息")
                return True
            for r in records:
                if r.get('new_item_id'):
                    ok = enrich(r, 'new')
                    if not ok:
                        debug_lines.append(
                            f"new 查询编码={r.get('new_item_id')} 命中=N")
                if r.get('orig_item_id'):
                    enrich(r, 'orig')
            sql_content = generate_item_sql_bulk(records, ops_remark)
            now = datetime.now()
            year_month = now.strftime("%Y%m")
            day = now.strftime("%d")
            filename = f"{cd['dynamic_id']}_修改合同物资编码.sql"
            base_dir = r"D:\临时文件"
            target_dir = os.path.join(base_dir, year_month, day)
            os.makedirs(target_dir, exist_ok=True)
            filepath = os.path.join(target_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(sql_content)

            # 记录文件保存
            logger.info(f"SQL文件已保存: {filepath}")
            temp_dir = os.path.join(settings.BASE_DIR, 'temp_downloads')
            os.makedirs(temp_dir, exist_ok=True)
            download_path = os.path.join(temp_dir, filename)
            with open(download_path, 'w', encoding='utf-8') as f:
                f.write(sql_content)
            # 将Decimal类型转换为字符串以支持JSON序列化
            session_data = {}
            for k, v in cd.items():
                if k != 'excel_file':
                    # 处理Decimal类型
                    if hasattr(v, 'to_eng_string'):
                        session_data[k] = v.to_eng_string()
                    else:
                        session_data[k] = v
            request.session['contract_item_last'] = session_data
            return render(request, 'success.html', {
                'filepath': filepath,
                'download_url': f"/download/{filename}"
            })
    else:
        if request.GET.get('clear'):
            request.session.pop('contract_item_last', None)
            form = ContractItemUpdateForm()
        else:
            initial = request.session.get('contract_item_last')
            form = ContractItemUpdateForm(initial=initial)
    return render(request, 'contract_item_form.html', {'form': form})


def download_item_template(request):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = '模板'
    ws.append(['明细行ID', '物资编码', '物资名称', '计量单位', '物资分类编码',
              '原物资编码', '原物资名称', '原计量单位', '原物资分类编码', '描述'])
    ws.append(['BPO-EXAMPLE-000001', '01607733', '鞋套',
              '双', '430798', None, None, None, None, None])
    bio = io.BytesIO()
    wb.save(bio)
    bio.seek(0)
    response = FileResponse(bio, as_attachment=True,
                            filename='contract_item_template.xlsx')
    response['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    return response


def download_price_template(request):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = '模板'
    ws.append(['明细行ID', '单价', '数量', '原数量', '原单价'])
    ws.append(['BPO-EXAMPLE-000001', 100, 1, None, None])
    bio = io.BytesIO()
    wb.save(bio)
    bio.seek(0)
    response = FileResponse(bio, as_attachment=True,
                            filename='contract_price_template.xlsx')
    response['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    return response


def contract_detail_price_view(request):
    """
    处理合同明细单价修改的视图函数
    """
    if request.method == 'POST':
        form = ContractDetailPriceForm(request.POST, request.FILES)
        if form.is_valid():
            cd = form.cleaned_data
            log_view_input("合同明细单价修改", cd)

            # 解析OPS_REMARK
            ops_remark = parse_ops_remark(cd.get('ops_remark', ''))

            if cd.get('excel_file'):
                records = parse_price_excel(cd['excel_file'])
                sql_content = generate_price_sql_bulk(records, ops_remark)
            else:
                new_quantity = cd.get('new_quantity')
                new_price = cd.get('new_price')
                orig_quantity = cd.get('orig_quantity')
                orig_price = cd.get('orig_price')
                if not new_price or not cd.get('single_line_id'):
                    form.add_error(None, "单条模式需填写单价和明细行ID；数量可不填")
                    return render(request, 'contract_price_form.html', {'form': form})
                line_ids = [cd['single_line_id']]
                sql_content = generate_price_sql(
                    line_ids, new_quantity, new_price, orig_quantity, orig_price, ops_remark)

            # 生成文件名
            now = datetime.now()
            year_month = now.strftime("%Y%m")
            day = now.strftime("%d")
            filename = f"{cd['dynamic_id']}_修改合同明细单价.sql"

            # 保存到临时文件
            base_dir = r"D:\临时文件"
            target_dir = os.path.join(base_dir, year_month, day)
            os.makedirs(target_dir, exist_ok=True)
            filepath = os.path.join(target_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(sql_content)

            # 记录文件保存
            logger.info(f"SQL文件已保存: {filepath}")

            # 保存到下载目录
            temp_dir = os.path.join(settings.BASE_DIR, 'temp_downloads')
            os.makedirs(temp_dir, exist_ok=True)
            download_path = os.path.join(temp_dir, filename)
            with open(download_path, 'w', encoding='utf-8') as f:
                f.write(sql_content)

            # 将Decimal类型转换为字符串以支持JSON序列化
            session_data = {}
            for k, v in cd.items():
                if k != 'excel_file':
                    # 处理Decimal类型
                    if hasattr(v, 'to_eng_string'):
                        session_data[k] = v.to_eng_string()
                    else:
                        session_data[k] = v
            request.session['contract_price_last'] = session_data
            return render(request, 'success.html', {
                'filepath': filepath,
                'download_url': f'/download/{filename}'
            })
    else:
        if request.GET.get('clear'):
            request.session.pop('contract_price_last', None)
            form = ContractDetailPriceForm()
        else:
            initial = request.session.get('contract_price_last')
            form = ContractDetailPriceForm(initial=initial)

    return render(request, 'contract_price_form.html', {'form': form})


def parse_gov_excel(file):
    wb = openpyxl.load_workbook(file)
    ws = wb.active
    headers = [cell.value for cell in ws[1]]
    idx = {str(h): i for i, h in enumerate(headers)}

    def pick(alts):
        for a in alts:
            if a in idx:
                return idx[a]
        return None
    s_idx = pick(['scheme_no', 'PURCHASE_SCHEME_NO', '采购方案编号'])
    i_idx = pick(['inq_id', 'INQ_ID', '询价单编号'])
    b_idx = pick(['bpo_id', 'BPO_ID', '合同号'])
    r_idx = pick(['report', 'is_report', '是否报送', 'IS_REPORT_TO_SASAC'])
    or_idx = pick(['orig_report', 'orig_is_report', '原是否报送'])
    records = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row:
            continue
        rec = {}
        if s_idx is not None and row[s_idx] is not None:
            rec['scheme_no'] = str(row[s_idx]).strip()
        if i_idx is not None and row[i_idx] is not None:
            rec['inq_id'] = str(row[i_idx]).strip()
        if b_idx is not None and row[b_idx] is not None:
            rec['bpo_id'] = str(row[b_idx]).strip()
        # 解析是否报送
        report_bool = None
        if r_idx is not None and row[r_idx] is not None:
            val = str(row[r_idx]).strip()
            if val in ['是', 'yes', 'YES', 'Y', 'y', '1']:
                report_bool = True
            elif val in ['否', 'no', 'NO', 'N', 'n', '0', '2']:
                report_bool = False
        orig_report_bool = None
        if or_idx is not None and row[or_idx] is not None:
            val = str(row[or_idx]).strip()
            if val in ['是', 'yes', 'YES', 'Y', 'y', '1']:
                orig_report_bool = True
            elif val in ['否', 'no', 'NO', 'N', 'n', '0', '2']:
                orig_report_bool = False
        if rec:
            if report_bool is not None:
                rec['report_bool'] = report_bool
            if orig_report_bool is not None:
                rec['orig_report_bool'] = orig_report_bool
            records.append(rec)
    if not records:
        raise ValueError("Excel 中没有有效的行数据")
    return records


def generate_gov_sql_bulk(records, ops_remark=None, report_choice=None, orig_report_choice=None):
    cfg = get_config()
    sql = []
    sql.append("1、执行语句")
    if cfg.get('MERGE_MODULES', {}).get('gov', True):
        def key_fn(r):
            rb = r.get('report_bool')
            if rb is None:
                if report_choice is None:
                    rb = True
                else:
                    rb = (report_choice == 'yes')
            return 1 if rb else 0
        groups = merge_by_key(records, key_fn)
        for report_val, recs in groups.items():
            submit_val = report_val
            schemes = [r.get('scheme_no') for r in recs if r.get('scheme_no')]
            inqs = [r.get('inq_id') for r in recs if r.get('inq_id')]
            bpos = [r.get('bpo_id') for r in recs if r.get('bpo_id')]
            for chunk in chunk_list(schemes, int(cfg.get('MERGE_MAX_IN_SIZE', 500))):
                sql.append(
                    f"UPDATE tprfa02 SET IS_REPORT_TO_SASAC='{report_val}', OPS_REMARK='{ops_remark or ''}' WHERE PURCHASE_SCHEME_NO IN ({format_in(chunk)});"
                )
            for chunk in chunk_list(inqs, int(cfg.get('MERGE_MAX_IN_SIZE', 500))):
                sql.append(
                    f"UPDATE tprxj02 SET IS_REPORT_TO_SASAC='{report_val}', OPS_REMARK='{ops_remark or ''}' WHERE INQ_ID IN ({format_in(chunk)});"
                )
            for chunk in chunk_list(bpos, int(cfg.get('MERGE_MAX_IN_SIZE', 500))):
                sql.append(
                    f"UPDATE tphct01 SET IS_SUBMIT_SASAC='{submit_val}', OPS_REMARK='{ops_remark or ''}' WHERE BPO_ID IN ({format_in(chunk)}) AND ALIVE_FLAG='1';"
                )
    else:
        for r in records:
            rb = r.get('report_bool')
            if rb is None:
                if report_choice is None:
                    rb = True
                else:
                    rb = (report_choice == 'yes')
            report_val = 1 if rb else 0
            submit_val = 1 if rb else 0
            if r.get('scheme_no'):
                sql.append(
                    f"UPDATE tprfa02 SET IS_REPORT_TO_SASAC='{report_val}', OPS_REMARK='{ops_remark or ''}' WHERE PURCHASE_SCHEME_NO='{r['scheme_no']}';"
                )
            if r.get('inq_id'):
                sql.append(
                    f"UPDATE tprxj02 SET IS_REPORT_TO_SASAC='{report_val}', OPS_REMARK='{ops_remark or ''}' WHERE INQ_ID='{r['inq_id']}';"
                )
            if r.get('bpo_id'):
                sql.append(
                    f"UPDATE tphct01 SET IS_SUBMIT_SASAC='{submit_val}', OPS_REMARK='{ops_remark or ''}' WHERE BPO_ID='{r['bpo_id']}' AND ALIVE_FLAG='1';"
                )
    sql.append("")
    sql.append("2、回退语句")
    if cfg.get('MERGE_MODULES', {}).get('gov', True):
        def rb_key(r):
            ob = r.get('orig_report_bool')
            if ob is None:
                if orig_report_choice is not None:
                    ob = (orig_report_choice == 'yes')
                else:
                    rb = r.get('report_bool')
                    if rb is None:
                        rb = (report_choice ==
                              'yes') if report_choice is not None else True
                    ob = not rb
            return 1 if ob else 0
        groups = merge_by_key(records, rb_key)
        for report_val, recs in groups.items():
            submit_val = report_val
            schemes = [r.get('scheme_no') for r in recs if r.get('scheme_no')]
            inqs = [r.get('inq_id') for r in recs if r.get('inq_id')]
            bpos = [r.get('bpo_id') for r in recs if r.get('bpo_id')]
            for chunk in chunk_list(schemes, int(cfg.get('MERGE_MAX_IN_SIZE', 500))):
                sql.append(
                    f"UPDATE tprfa02 SET IS_REPORT_TO_SASAC='{report_val}', OPS_REMARK='' WHERE PURCHASE_SCHEME_NO IN ({format_in(chunk)});")
            for chunk in chunk_list(inqs, int(cfg.get('MERGE_MAX_IN_SIZE', 500))):
                sql.append(
                    f"UPDATE tprxj02 SET IS_REPORT_TO_SASAC='{report_val}', OPS_REMARK='' WHERE INQ_ID IN ({format_in(chunk)});")
            for chunk in chunk_list(bpos, int(cfg.get('MERGE_MAX_IN_SIZE', 500))):
                sql.append(
                    f"UPDATE tphct01 SET IS_SUBMIT_SASAC='{submit_val}', OPS_REMARK='' WHERE BPO_ID IN ({format_in(chunk)}) AND ALIVE_FLAG='1';")
    else:
        for r in records:
            ob = r.get('orig_report_bool')
            if ob is None:
                if orig_report_choice is not None:
                    ob = (orig_report_choice == 'yes')
                else:
                    rb = r.get('report_bool')
                    if rb is None:
                        rb = (report_choice ==
                              'yes') if report_choice is not None else True
                    ob = not rb
            report_val = 1 if ob else 0
            submit_val = 1 if ob else 0
            if r.get('scheme_no'):
                sql.append(
                    f"UPDATE tprfa02 SET IS_REPORT_TO_SASAC='{report_val}', OPS_REMARK='' WHERE PURCHASE_SCHEME_NO='{r['scheme_no']}';")
            if r.get('inq_id'):
                sql.append(
                    f"UPDATE tprxj02 SET IS_REPORT_TO_SASAC='{report_val}', OPS_REMARK='' WHERE INQ_ID='{r['inq_id']}';")
            if r.get('bpo_id'):
                sql.append(
                    f"UPDATE tphct01 SET IS_SUBMIT_SASAC='{submit_val}', OPS_REMARK='' WHERE BPO_ID='{r['bpo_id']}' AND ALIVE_FLAG='1';")
    sql.append("")
    sql.append("3、数据库")
    sql.append("ip:192.168.11.69")
    sql.append("库名：cnnc_pr")
    sql.append("")
    sql.append("ip:192.168.11.71")
    sql.append("库名：cnnc_ph")
    return "\n".join(sql)


def gov_report_view(request):
    if request.method == 'POST':
        form = GovReportForm(request.POST, request.FILES)
        if form.is_valid():
            cd = form.cleaned_data
            log_view_input("合同物资编码修改", cd)
            ops_remark = parse_ops_remark(cd.get('ops_remark', ''))
            if cd.get('excel_file'):
                records = parse_gov_excel(cd['excel_file'])
                sql_content = generate_gov_sql_bulk(records, ops_remark)
            else:
                rec = {
                    'scheme_no': cd.get('scheme_no'),
                    'inq_id': cd.get('inq_id'),
                    'bpo_id': cd.get('bpo_id'),
                }
                records = [rec]
                sql_content = generate_gov_sql_bulk(records, ops_remark, cd.get(
                    'report_choice'), cd.get('orig_report_choice'))
            now = datetime.now()
            year_month = now.strftime("%Y%m")
            day = now.strftime("%d")
            filename = f"{cd['dynamic_id']}_是否报送国资委.sql"
            base_dir = r"D:\临时文件"
            target_dir = os.path.join(base_dir, year_month, day)
            os.makedirs(target_dir, exist_ok=True)
            filepath = os.path.join(target_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(sql_content)

            # 记录文件保存
            logger.info(f"SQL文件已保存: {filepath}")
            temp_dir = os.path.join(settings.BASE_DIR, 'temp_downloads')
            os.makedirs(temp_dir, exist_ok=True)
            download_path = os.path.join(temp_dir, filename)
            with open(download_path, 'w', encoding='utf-8') as f:
                f.write(sql_content)
            request.session['gov_report_last'] = {
                k: v for k, v in cd.items() if k != 'excel_file'}
            return render(request, 'success.html', {
                'filepath': filepath,
                'download_url': f"/download/{filename}"
            })
    else:
        if request.GET.get('clear'):
            request.session.pop('gov_report_last', None)
            form = GovReportForm()
        else:
            initial = request.session.get('gov_report_last')
            form = GovReportForm(initial=initial)
    return render(request, 'gov_report_form.html', {
        'form': form,
        'active_menu': 'gov_report',
        'sidebar_groups': SIDEBAR_GROUPS,
    })


def download_gov_template(request):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = '模板'
    ws.append(['采购方案编号', '询价单编号', '合同号', '是否报送', '原是否报送'])
    ws.append(['CNEC-CGFA-25-20795', 'CNEC-XJD-25-20009',
              '23EC-25-02605', '是', '否'])
    bio = io.BytesIO()
    wb.save(bio)
    bio.seek(0)
    response = FileResponse(bio, as_attachment=True,
                            filename='gov_report_template.xlsx')
    response['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    return response


def parse_importance_excel(file):
    wb = openpyxl.load_workbook(file)
    ws = wb.active
    headers = [cell.value for cell in ws[1]]
    idx = {str(h): i for i, h in enumerate(headers)}

    def pick(alts):
        for a in alts:
            if a in idx:
                return idx[a]
        return None
    s_idx = pick(['scheme_no', 'PURCHASE_SCHEME_NO', '采购方案编号'])
    i_idx = pick(['inq_id', 'INQ_ID', '询价单编号'])
    b_idx = pick(['bpo_id', 'BPO_ID', '合同号'])
    imp_idx = pick(['importance', 'PROJECT_IMPORTANCE', '物项重要性'])
    oimp_idx = pick(['orig_importance', '原重要性'])

    def map_imp(v):
        if v is None:
            return None
        val = str(v).strip()
        m = {
            '一般准入备案类': '0',
            '一般自行管理类': '1',
            '一般': '4',
            '核心': '3',
            '重要': '2',
        }
        if val in m:
            return m[val]
        if val in ['0', '1', '2', '3', '4']:
            return val
        return None
    records = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row:
            continue
        rec = {}
        if s_idx is not None and row[s_idx] is not None:
            rec['scheme_no'] = str(row[s_idx]).strip()
        if i_idx is not None and row[i_idx] is not None:
            rec['inq_id'] = str(row[i_idx]).strip()
        if b_idx is not None and row[b_idx] is not None:
            rec['bpo_id'] = str(row[b_idx]).strip()
        if imp_idx is not None:
            rec['importance_code'] = map_imp(row[imp_idx])
        if oimp_idx is not None:
            rec['orig_importance_code'] = map_imp(row[oimp_idx])
        if rec.get('scheme_no') or rec.get('inq_id') or rec.get('bpo_id'):
            records.append(rec)
    if not records:
        raise ValueError("Excel 中没有有效的行数据")
    return records


def generate_importance_sql_bulk(records, ops_remark=None, importance_code=None, orig_importance_code=None):
    cfg = get_config()
    sql = []
    sql.append("1、执行语句")
    if cfg.get('MERGE_MODULES', {}).get('importance', True):
        def key_fn(r):
            return r.get('importance_code') if r.get('importance_code') is not None else importance_code
        groups = merge_by_key(records, key_fn)
        for code, recs in groups.items():
            if code is None:
                continue
            schemes = [r.get('scheme_no') for r in recs if r.get('scheme_no')]
            inqs = [r.get('inq_id') for r in recs if r.get('inq_id')]
            bpos = [r.get('bpo_id') for r in recs if r.get('bpo_id')]
            for chunk in chunk_list(schemes, int(cfg.get('MERGE_MAX_IN_SIZE', 500))):
                sql.append(
                    f"UPDATE tprfa01 SET IMPORTANCE='{code}', OPS_REMARK='{ops_remark or ''}' WHERE PURCHASE_SCHEME_NO IN ({format_in(chunk)});")
            for chunk in chunk_list(inqs, int(cfg.get('MERGE_MAX_IN_SIZE', 500))):
                sql.append(
                    f"UPDATE tprxj01 SET IMPORTANCE='{code}', OPS_REMARK='{ops_remark or ''}' WHERE INQ_ID IN ({format_in(chunk)});")
                sql.append(
                    f"UPDATE tprnq01 SET PROJECT_IMPORTANCE='{code}', OPS_REMARK='{ops_remark or ''}' WHERE INQ_ID IN ({format_in(chunk)});")
            for chunk in chunk_list(bpos, int(cfg.get('MERGE_MAX_IN_SIZE', 500))):
                sql.append(
                    f"UPDATE tphct01 SET PROJECT_IMPORTANCE='{code}', OPS_REMARK='{ops_remark or ''}' WHERE BPO_ID IN ({format_in(chunk)});")
    else:
        for r in records:
            code = r.get('importance_code') if r.get(
                'importance_code') is not None else importance_code
            if r.get('scheme_no') and code is not None:
                sql.append(
                    f"UPDATE tprfa01 SET IMPORTANCE='{code}', OPS_REMARK='{ops_remark or ''}' WHERE PURCHASE_SCHEME_NO='{r['scheme_no']}';")
            if r.get('inq_id') and code is not None:
                sql.append(
                    f"UPDATE tprxj01 SET IMPORTANCE='{code}', OPS_REMARK='{ops_remark or ''}' WHERE INQ_ID='{r['inq_id']}';")
                sql.append(
                    f"UPDATE tprnq01 SET PROJECT_IMPORTANCE='{code}', OPS_REMARK='{ops_remark or ''}' WHERE INQ_ID='{r['inq_id']}';")
            if r.get('bpo_id') and code is not None:
                sql.append(
                    f"UPDATE tphct01 SET PROJECT_IMPORTANCE='{code}', OPS_REMARK='{ops_remark or ''}' WHERE BPO_ID='{r['bpo_id']}';")
    sql.append("")
    sql.append("2、回退语句")
    if cfg.get('MERGE_MODULES', {}).get('importance', True):
        def rb_key(r):
            if r.get('orig_importance_code') is not None:
                return r.get('orig_importance_code')
            return orig_importance_code if orig_importance_code is not None else '2'
        groups = merge_by_key(records, rb_key)
        for rcode, recs in groups.items():
            schemes = [r.get('scheme_no') for r in recs if r.get('scheme_no')]
            inqs = [r.get('inq_id') for r in recs if r.get('inq_id')]
            bpos = [r.get('bpo_id') for r in recs if r.get('bpo_id')]
            for chunk in chunk_list(schemes, int(cfg.get('MERGE_MAX_IN_SIZE', 500))):
                sql.append(
                    f"UPDATE tprfa01 SET IMPORTANCE='{rcode}', OPS_REMARK='' WHERE PURCHASE_SCHEME_NO IN ({format_in(chunk)});")
            for chunk in chunk_list(inqs, int(cfg.get('MERGE_MAX_IN_SIZE', 500))):
                sql.append(
                    f"UPDATE tprxj01 SET IMPORTANCE='{rcode}', OPS_REMARK='' WHERE INQ_ID IN ({format_in(chunk)});")
                sql.append(
                    f"UPDATE tprnq01 SET PROJECT_IMPORTANCE='{rcode}', OPS_REMARK='' WHERE INQ_ID IN ({format_in(chunk)});")
            for chunk in chunk_list(bpos, int(cfg.get('MERGE_MAX_IN_SIZE', 500))):
                sql.append(
                    f"UPDATE tphct01 SET PROJECT_IMPORTANCE='{rcode}', OPS_REMARK='' WHERE BPO_ID IN ({format_in(chunk)});")
    else:
        for r in records:
            rcode = r.get('orig_importance_code') if r.get('orig_importance_code') is not None else (
                orig_importance_code if orig_importance_code is not None else '2')
            if r.get('scheme_no'):
                sql.append(
                    f"UPDATE tprfa01 SET IMPORTANCE='{rcode}', OPS_REMARK='' WHERE PURCHASE_SCHEME_NO='{r['scheme_no']}';")
            if r.get('inq_id'):
                sql.append(
                    f"UPDATE tprxj01 SET IMPORTANCE='{rcode}', OPS_REMARK='' WHERE INQ_ID='{r['inq_id']}';")
                sql.append(
                    f"UPDATE tprnq01 SET PROJECT_IMPORTANCE='{rcode}', OPS_REMARK='' WHERE INQ_ID='{r['inq_id']}';")
            if r.get('bpo_id'):
                sql.append(
                    f"UPDATE tphct01 SET PROJECT_IMPORTANCE='{rcode}', OPS_REMARK='' WHERE BPO_ID='{r['bpo_id']}';")
    sql.append("")
    sql.append("3、数据库")
    sql.append("ip:192.168.11.69")
    sql.append("库名：cnnc_pr")
    sql.append("")
    sql.append("ip：192.168.11.71")
    sql.append("库名：cnnc_ph")
    return "\n".join(sql)


def importance_update_view(request):
    if request.method == 'POST':
        form = ImportanceForm(request.POST, request.FILES)
        if form.is_valid():
            cd = form.cleaned_data
            log_view_input("合同预算修改", cd)
            ops_remark = parse_ops_remark(cd.get('ops_remark', ''))
            if cd.get('excel_file'):
                records = parse_importance_excel(cd['excel_file'])
                sql_content = generate_importance_sql_bulk(records, ops_remark)
            else:
                rec = {
                    'scheme_no': cd.get('scheme_no'),
                    'inq_id': cd.get('inq_id'),
                    'bpo_id': cd.get('bpo_id'),
                }
                records = [rec]
                sql_content = generate_importance_sql_bulk(records, ops_remark, cd.get(
                    'importance_choice'), cd.get('orig_importance_choice'))
            now = datetime.now()
            year_month = now.strftime("%Y%m")
            day = now.strftime("%d")
            filename = f"{cd['dynamic_id']}_修改物项重要性.sql"
            base_dir = r"D:\临时文件"
            target_dir = os.path.join(base_dir, year_month, day)
            os.makedirs(target_dir, exist_ok=True)
            filepath = os.path.join(target_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(sql_content)

            # 记录文件保存
            logger.info(f"SQL文件已保存: {filepath}")
            temp_dir = os.path.join(settings.BASE_DIR, 'temp_downloads')
            os.makedirs(temp_dir, exist_ok=True)
            download_path = os.path.join(temp_dir, filename)
            with open(download_path, 'w', encoding='utf-8') as f:
                f.write(sql_content)
            request.session['importance_last'] = {
                k: v for k, v in cd.items() if k != 'excel_file'}
            return render(request, 'success.html', {
                'filepath': filepath,
                'download_url': f"/download/{filename}"
            })
    else:
        if request.GET.get('clear'):
            request.session.pop('importance_last', None)
            form = ImportanceForm()
        else:
            initial = request.session.get('importance_last')
            form = ImportanceForm(initial=initial)
    return render(request, 'importance_form.html', {
        'form': form,
        'active_menu': 'importance',
        'sidebar_groups': SIDEBAR_GROUPS,
    })


def download_importance_template(request):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = '模板'
    ws.append(['采购方案编号', '询价单编号', '合同号', '物项重要性', '原重要性'])
    ws.append(['HNGS-CGFA-25-01658', 'CNSC-XJD-25-02704',
              'HNGS-25-00255', '一般', '重要'])
    bio = io.BytesIO()
    wb.save(bio)
    bio.seek(0)
    response = FileResponse(bio, as_attachment=True,
                            filename='importance_template.xlsx')
    response['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    return response


def parse_enddate_excel(file):
    wb = openpyxl.load_workbook(file)
    ws = wb.active
    headers = [cell.value for cell in ws[1]]
    idx = {str(h): i for i, h in enumerate(headers)}

    def pick(alts):
        for a in alts:
            if a in idx:
                return idx[a]
        return None
    b_idx = pick(['bpo_id', 'BPO_ID', '合同号'])
    e_idx = pick(['end_date', 'END_DATE', '新失效日期'])
    o_idx = pick(['orig_end_date', '原失效日期'])
    records = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row:
            continue
        bpo = row[b_idx] if b_idx is not None else None
        endd = row[e_idx] if e_idx is not None else None
        orig = row[o_idx] if o_idx is not None else None
        if bpo is None or endd is None:
            continue
        rec = {
            'bpo_id': str(bpo).strip(),
            'end_date': str(endd).strip(),
        }
        if orig is not None:
            rec['orig_end_date'] = str(orig).strip()
        records.append(rec)
    if not records:
        raise ValueError("Excel 中没有有效的行数据")
    return records


def generate_enddate_sql_bulk(records, ops_remark=None):
    cfg = get_config()
    sql = []
    sql.append("1、执行语句")
    if cfg.get('MERGE_MODULES', {}).get('enddate', True):
        def key_fn(r):
            return r.get('end_date')
        groups = merge_by_key(records, key_fn)
        for endd, recs in groups.items():
            ids = [r['bpo_id'] for r in recs if r.get('bpo_id')]
            for chunk in chunk_list(ids, int(cfg.get('MERGE_MAX_IN_SIZE', 500))):
                inlist = format_in(chunk)
                sql.append(
                    f"UPDATE tphct01 SET END_DATE='{endd}', APPR_STATE='ACTIVE', OPS_REMARK='{ops_remark or ''}' WHERE BPO_ID IN ({inlist}) AND ALIVE_FLAG='1';")
                sql.append(
                    f"UPDATE tphct02 SET APPR_STATE='ACTIVE', OPS_REMARK='{ops_remark or ''}' WHERE BPO_ID IN ({inlist}) AND ALIVE_FLAG='1';")
    else:
        for r in records:
            sql.append(
                f"UPDATE tphct01 SET END_DATE='{r['end_date']}', APPR_STATE='ACTIVE', OPS_REMARK='{ops_remark or ''}' WHERE BPO_ID='{r['bpo_id']}' AND ALIVE_FLAG='1';")
            sql.append(
                f"UPDATE tphct02 SET APPR_STATE='ACTIVE', OPS_REMARK='{ops_remark or ''}' WHERE BPO_ID='{r['bpo_id']}' AND ALIVE_FLAG='1';")
    sql.append("")
    sql.append("2、回退语句")
    if cfg.get('MERGE_MODULES', {}).get('enddate', True):
        def rb_key(r):
            return r.get('orig_end_date') or ''
        groups = merge_by_key(records, rb_key)
        for orig, recs in groups.items():
            ids = [r['bpo_id'] for r in recs if r.get('bpo_id')]
            for chunk in chunk_list(ids, int(cfg.get('MERGE_MAX_IN_SIZE', 500))):
                inlist = format_in(chunk)
                if orig:
                    sql.append(
                        f"UPDATE tphct01 SET END_DATE='{orig}', APPR_STATE='CLOSED', OPS_REMARK='' WHERE BPO_ID IN ({inlist}) AND ALIVE_FLAG='1';")
                else:
                    sql.append(
                        f"UPDATE tphct01 SET APPR_STATE='CLOSED', OPS_REMARK='' WHERE BPO_ID IN ({inlist}) AND ALIVE_FLAG='1';")
                sql.append(
                    f"UPDATE tphct02 SET APPR_STATE='CLOSED', OPS_REMARK='' WHERE BPO_ID IN ({inlist}) AND ALIVE_FLAG='1';")
    else:
        for r in records:
            if r.get('orig_end_date'):
                sql.append(
                    f"UPDATE tphct01 SET END_DATE='{r['orig_end_date']}', APPR_STATE='CLOSED', OPS_REMARK='' WHERE BPO_ID='{r['bpo_id']}' AND ALIVE_FLAG='1';")
            else:
                sql.append(
                    f"UPDATE tphct01 SET APPR_STATE='CLOSED', OPS_REMARK='' WHERE BPO_ID='{r['bpo_id']}' AND ALIVE_FLAG='1';")
            sql.append(
                f"UPDATE tphct02 SET APPR_STATE='CLOSED', OPS_REMARK='' WHERE BPO_ID='{r['bpo_id']}' AND ALIVE_FLAG='1';")
    sql.append("")
    sql.append("3、数据库")
    sql.append("ip：192.168.11.71")
    sql.append("库名：cnnc_ph")
    return "\n".join(sql)


def enddate_update_view(request):
    if request.method == 'POST':
        form = EndDateUpdateForm(request.POST, request.FILES)
        if form.is_valid():
            cd = form.cleaned_data
            log_view_input("政府报送修改", cd)
            ops_remark = parse_ops_remark(cd.get('ops_remark', ''))
            if cd.get('excel_file'):
                records = parse_enddate_excel(cd['excel_file'])
                sql_content = generate_enddate_sql_bulk(records, ops_remark)
            else:
                records = [{'bpo_id': cd['bpo_id'], 'end_date': cd['end_date'],
                            'orig_end_date': cd.get('orig_end_date')}]
                sql_content = generate_enddate_sql_bulk(records, ops_remark)
            now = datetime.now()
            year_month = now.strftime("%Y%m")
            day = now.strftime("%d")
            filename = f"{cd['dynamic_id']}_修改合同失效日期.sql"
            base_dir = r"D:\临时文件"
            target_dir = os.path.join(base_dir, year_month, day)
            os.makedirs(target_dir, exist_ok=True)
            filepath = os.path.join(target_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(sql_content)

            # 记录文件保存
            logger.info(f"SQL文件已保存: {filepath}")
            temp_dir = os.path.join(settings.BASE_DIR, 'temp_downloads')
            os.makedirs(temp_dir, exist_ok=True)
            download_path = os.path.join(temp_dir, filename)
            with open(download_path, 'w', encoding='utf-8') as f:
                f.write(sql_content)
            request.session['enddate_last'] = {
                k: v for k, v in cd.items() if k != 'excel_file'}
            return render(request, 'success.html', {
                'filepath': filepath,
                'download_url': f"/download/{filename}"
            })
    else:
        if request.GET.get('clear'):
            request.session.pop('enddate_last', None)
            form = EndDateUpdateForm()
        else:
            initial = request.session.get('enddate_last')
            form = EndDateUpdateForm(initial=initial)
    return render(request, 'end_date_form.html', {
        'form': form,
        'active_menu': 'enddate',
        'sidebar_groups': SIDEBAR_GROUPS,
    })


def download_enddate_template(request):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = '模板'
    ws.append(['合同号', '新失效日期', '原失效日期'])
    ws.append(['203S-25-00039', '20251125', '20251105'])
    bio = io.BytesIO()
    wb.save(bio)
    bio.seek(0)
    response = FileResponse(bio, as_attachment=True,
                            filename='enddate_template.xlsx')
    response['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    return response


IMPORT_LOCK = threading.Lock()


def job_list_view(request):
    from .models import ImportJob
    jobs = ImportJob.objects.order_by('-id')[:100]
    return render(request, 'jobs.html', {
        'jobs': jobs,
        'active_menu': 'job_list',
        'sidebar_groups': SIDEBAR_GROUPS,
    })


def job_detail_view(request, job_id):
    from .models import ImportJob
    job = ImportJob.objects.get(id=job_id)
    return render(request, 'job_detail.html', {
        'job': job,
        'active_menu': 'job_list',
        'sidebar_groups': SIDEBAR_GROUPS,
    })


def job_status_api(request, job_id):
    from .models import ImportJob
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
    from .models import ImportJob
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
    from .models import ImportJob
    job = ImportJob.objects.get(id=job_id)
    if request.method != 'POST':
        return redirect('job_detail', job_id=job_id)
    if job.status == 'running':
        job.status = 'failed'
        job.error = 'manually failed'
        job.save(update_fields=['status', 'error', 'updated_at'])
    return redirect('job_detail', job_id=job_id)


def item_search_api(request):
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
    iid = request.GET.get('id', '').strip()
    if not iid:
        return JsonResponse({'found': False})
    o = ItemDetail.objects.filter(item_id=normalize_item_id(iid)).first()
    if not o:
        return JsonResponse({'found': False})
    return JsonResponse({'found': True, 'id': o.item_id, 'name': o.item_name, 'uom': o.item_uom, 'category': o.category})


def parse_price_type_excel(file):
    wb = openpyxl.load_workbook(file)
    ws = wb.active
    headers = [cell.value for cell in ws[1]]
    idx = {str(h): i for i, h in enumerate(headers)}

    def pick(alts):
        for a in alts:
            if a in idx:
                return idx[a]
        return None
    bpo_idx = pick(['BPO_ID', 'bpo_id', '合同编号'])
    if bpo_idx is None:
        raise ValueError('Excel 缺少必要列：合同编号')
    records = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row:
            continue
        bpo = row[bpo_idx]
        if not bpo:
            continue
        rec = {
            'bpo_id': str(bpo).strip(),
        }
        records.append(rec)
    if not records:
        raise ValueError('Excel 中没有有效的行数据')
    return records


def generate_price_type_sql(records, ops_remark=''):
    ops_remark = parse_ops_remark(ops_remark)
    sql = []
    sql.append('1、执行语句')
    for r in records:
        bpo = r['bpo_id']
        newt = '20'
        sql.append(
            f"update TPHCT02 set PUR_PRICE_TYPE='{newt}', OPS_REMARK='{ops_remark}' WHERE BPO_ID='{bpo}' and ALIVE_FLAG='1';"
        )
        sql.append(
            f"update tprly04 set PUR_PRICE_TYPE='{newt}', OPS_REMARK='{ops_remark}' WHERE BPO_ID='{bpo}' and ALIVE_FLAG='1';"
        )
    sql.append('')
    sql.append('2、回退语句')
    for r in records:
        bpo = r['bpo_id']
        orig = '10'
        sql.append(
            f"update TPHCT02 set PUR_PRICE_TYPE='{orig}', OPS_REMARK='' WHERE BPO_ID='{bpo}' and ALIVE_FLAG='1';"
        )
        sql.append(
            f"update tprly04 set PUR_PRICE_TYPE='{orig}', OPS_REMARK='' WHERE BPO_ID='{bpo}' and ALIVE_FLAG='1';"
        )
    sql.append('')
    sql.append('3.数据库')
    sql.append('ip：192.168.11.71')
    sql.append('库名：cnnc_ph')
    return "\n".join(sql)


def floating_price_type_view(request):
    if request.method == 'POST':
        form = FloatingPriceTypeForm(request.POST, request.FILES)
        if form.is_valid():
            cd = form.cleaned_data
            log_view_input("物项重要性修改", cd)
            ops_remark = cd.get('ops_remark', '')
            if cd.get('excel_file'):
                records = parse_price_type_excel(cd['excel_file'])
                fail_rows = []
                valid = []
                for r in records:
                    desc = []
                    if not r.get('bpo_id'):
                        desc.append('合同编号为空')
                    if desc:
                        fail_rows.append({**r, 'desc': '; '.join(desc)})
                    else:
                        valid.append(r)
                sql_content = generate_price_type_sql(valid, ops_remark)
                now = datetime.now()
                filename = f"{cd['dynamic_id']}_价格类型修改为浮动单价.sql"
                base_dir = r"D:\临时文件"
                year_month = now.strftime('%Y%m')
                day = now.strftime('%d')
                target_dir = os.path.join(base_dir, year_month, day)
                os.makedirs(target_dir, exist_ok=True)
                filepath = os.path.join(target_dir, filename)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(sql_content)
                temp_dir = os.path.join(settings.BASE_DIR, 'temp_downloads')
                os.makedirs(temp_dir, exist_ok=True)
                download_path = os.path.join(temp_dir, filename)
                with open(download_path, 'w', encoding='utf-8') as f:
                    f.write(sql_content)
                fail_download_url = None
                if fail_rows:
                    wb = openpyxl.Workbook()
                    ws = wb.active
                    ws.title = '失败明细'
                    ws.append(['合同编号', '描述'])
                    for r in fail_rows:
                        ws.append([r.get('bpo_id'), r.get('desc')])
                    fail_name = f"{cd['dynamic_id']}_浮动单价类型修改_失败.xlsx"
                    fail_path = os.path.join(temp_dir, fail_name)
                    wb.save(fail_path)
                    fail_download_url = f"/download/{fail_name}"
            else:
                rec = {
                    'bpo_id': cd['bpo_id']
                }
                sql_content = generate_price_type_sql([rec], ops_remark)
                now = datetime.now()
                filename = f"{cd['dynamic_id']}_价格类型修改为浮动单价.sql"
                base_dir = r"D:\临时文件"
                year_month = now.strftime('%Y%m')
                day = now.strftime('%d')
                target_dir = os.path.join(base_dir, year_month, day)
                os.makedirs(target_dir, exist_ok=True)
                filepath = os.path.join(target_dir, filename)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(sql_content)
                temp_dir = os.path.join(settings.BASE_DIR, 'temp_downloads')
                os.makedirs(temp_dir, exist_ok=True)
                download_path = os.path.join(temp_dir, filename)
                with open(download_path, 'w', encoding='utf-8') as f:
                    f.write(sql_content)
                fail_download_url = None
            session_data = {}
            for k, v in cd.items():
                if k != 'excel_file':
                    if hasattr(v, 'to_eng_string'):
                        session_data[k] = v.to_eng_string()
                    else:
                        session_data[k] = v
            request.session['floating_price_type_last'] = session_data
            return render(request, 'success.html', {
                'filepath': filepath,
                'download_url': f"/download/{filename}",
                'fail_download_url': fail_download_url,
                'active_menu': 'price_type_update',
                'sidebar_groups': SIDEBAR_GROUPS,
            })
    else:
        if request.GET.get('clear'):
            request.session.pop('floating_price_type_last', None)
            form = FloatingPriceTypeForm()
        else:
            initial = request.session.get('floating_price_type_last')
            form = FloatingPriceTypeForm(initial=initial)
    return render(request, 'floating_price_type_form.html', {
        'form': form,
        'active_menu': 'price_type_update',
        'sidebar_groups': SIDEBAR_GROUPS,
    })


def download_price_type_template(request):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = '模板'
    ws.append(['合同编号'])
    ws.append(['22EC-25-02800'])
    bio = io.BytesIO()
    wb.save(bio)
    bio.seek(0)
    response = FileResponse(bio, as_attachment=True,
                            filename='price_type_template.xlsx')
    response['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    return response
