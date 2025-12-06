"""
合同单位修改模块
包含起草单位和签约主体的修改功能
"""
import io
import os
import logging
from datetime import datetime
from django.shortcuts import render
from django.http import FileResponse
from ..forms import UnitChangeForm
from ..navigation import SIDEBAR_GROUPS
from ..config import get_config
from ..sql_merge import chunk_list, format_in, merge_by_key, compose_or
from ..logger_utils import log_view_input
from .base import parse_ops_remark, extract_company_code, extract_company_name, _unique_code_by_name, save_sql_file

try:
    import openpyxl
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False

logger = logging.getLogger('work_tools.view')


def generate_unit_sql(records, **kwargs):
    """生成单位修改SQL"""
    cfg = get_config()
    update_drafting = kwargs.get('update_drafting', False)
    update_contract_party = kwargs.get('update_contract_party', False)
    old_drafting_id = kwargs.get('old_drafting_id')
    old_drafting_name = kwargs.get('old_drafting_name')
    old_party_id = kwargs.get('old_party_id')
    old_party_name = kwargs.get('old_party_name')
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

        groups = merge_by_key(records, set_parts_from)
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


def parse_unit_excel(file):
    """解析单位修改Excel"""
    wb = openpyxl.load_workbook(file)
    ws = wb.active
    records = []
    headers = [cell.value for cell in ws[1]]
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

        # 提取新起草单位信息
        for k in ['new_drafting_id', '新起草单位ID']:
            if k in idx:
                rec['new_drafting_id'] = row[idx[k]]
                break
        for k in ['new_drafting_name', '新起草单位名称', '组织机构名称']:
            if k in idx:
                rec['new_drafting_name'] = row[idx[k]]
                break
        # 提取新签约主体信息
        for k in ['new_party_id', '新签约主体ID']:
            if k in idx:
                rec['new_party_id'] = row[idx[k]]
                break
        for k in ['new_party_name', '新签约主体名称']:
            if k in idx:
                rec['new_party_name'] = row[idx[k]]
                break
        # 提取原起草单位信息
        for k in ['orig_drafting_id', '原起草单位ID']:
            if k in idx:
                rec['orig_drafting_id'] = row[idx[k]]
                break
        for k in ['orig_drafting_name', '原起草单位名称']:
            if k in idx:
                rec['orig_drafting_name'] = row[idx[k]]
                break
        # 提取原签约主体信息
        for k in ['orig_party_id', '原签约主体ID']:
            if k in idx:
                rec['orig_party_id'] = row[idx[k]]
                break
        for k in ['orig_party_name', '原签约主体名称']:
            if k in idx:
                rec['orig_party_name'] = row[idx[k]]
                break

        records.append(rec)
    return records


def unit_change_view(request):
    """合同单位修改视图"""
    saved_file = None

    if request.method == 'POST':
        form = UnitChangeForm(request.POST, request.FILES)
        if form.is_valid():
            cd = form.cleaned_data
            log_view_input("合同起草、签约单位修改", cd)

            if cd.get('excel_file'):
                records = parse_unit_excel(cd['excel_file'])
                # 从记录中判断是否更新
                will_update_drafting = any(r.get('new_drafting_id') or r.get(
                    'new_drafting_name') for r in records)
                will_update_party = any(r.get('new_party_id') or r.get(
                    'new_party_name') for r in records)
                # 统一处理名称到编号的转换
                for r in records:
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
            else:
                records = [{
                    'scheme': cd['scheme_no'],
                    'inquiry': cd['inquiry_no'],
                    'result': cd['result_no']
                }]
                will_update_drafting = bool(
                    cd.get('new_drafting_id') or cd.get('new_drafting_name'))
                will_update_party = bool(
                    cd.get('new_party_id') or cd.get('new_party_name'))
                # 单条记录的名称到编号转换
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

            ops_remark = parse_ops_remark(cd.get('ops_remark', ''))
            sql_content = generate_unit_sql(
                records,
                update_drafting=will_update_drafting,
                update_contract_party=will_update_party,
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

            # 确定文件名前缀
            if will_update_drafting and will_update_party:
                suffix = "修改起草单位和签约主体"
            elif will_update_drafting:
                suffix = "修改起草单位"
            elif will_update_party:
                suffix = "修改签约主体"
            else:
                suffix = "修改单位信息"

            saved_file = save_sql_file(
                sql_content, suffix, cd.get('dynamic_id'))
            logger.info(f"SQL文件已保存: {saved_file}")

            # 保存会话数据
            session_data = {}
            for k, v in cd.items():
                if k != 'excel_file':
                    if hasattr(v, 'to_eng_string'):
                        session_data[k] = v.to_eng_string()
                    else:
                        session_data[k] = v
            request.session['unit_change_last'] = session_data
    else:
        if request.GET.get('clear'):
            request.session.pop('unit_change_last', None)
            form = UnitChangeForm()
        else:
            initial = request.session.get('unit_change_last')
            form = UnitChangeForm(initial=initial)

    return render(request, 'unit_change_form.html', {
        'form': form,
        'saved_file': saved_file,
        'active_menu': 'unit_change',
        'sidebar_groups': SIDEBAR_GROUPS,
    })


def download_unit_template(request):
    """下载单位修改Excel模板"""
    if not OPENPYXL_AVAILABLE:
        from django.http import HttpResponse
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


__all__ = ['unit_change_view', 'download_unit_template',
           'generate_unit_sql', 'parse_unit_excel']
