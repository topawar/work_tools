"""
合同明细单价修改模块
包含单价修改的所有视图函数和SQL生成逻辑
"""
import io
import logging
from django.shortcuts import render
from django.http import FileResponse
from ..forms import ContractDetailPriceForm
from ..navigation import SIDEBAR_GROUPS
from ..config import get_config
from ..sql_merge import chunk_list, format_in, merge_by_key
from ..logger_utils import log_view_input
from .base import parse_ops_remark, save_sql_file

try:
    import openpyxl
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False

logger = logging.getLogger('work_tools.view')
sql_logger = logging.getLogger('work_tools.sql')


def parse_price_excel(file):
    """解析Excel文件,提取单价修改数据"""
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
    """
    生成批量单价修改SQL - 支持SQL合并策略
    相同单价和数量的记录会自动合并为IN查询
    """
    cfg = get_config()
    sql = []
    sql.append("1、执行语句")

    # 日志: 记录SQL生成开始
    sql_logger.info(
        f"[SQL合并] 开始生成单价SQL, 记录数={len(records)}, 配置启用={cfg.get('MERGE_MODULES', {}).get('price', True)}")

    if cfg.get('MERGE_MODULES', {}).get('price', True):
        # 启用SQL合并策略: 按单价和数量分组
        def key_fn(r):
            return (r.get('price'), r.get('quantity'))

        groups = merge_by_key(records, key_fn)
        sql_logger.info(f"[SQL合并] 分组结果: {len(groups)}个分组")

        for k, recs in groups.items():
            p, q = k
            ids = [r['line_id'] for r in recs if r.get('line_id')]
            sql_logger.info(
                f"[SQL合并] 处理分组: price={p}, qty={q}, 记录数={len(ids)}")

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
                sql_logger.info(f"[SQL合并] 生成IN查询: {len(chunk)}条记录")
    else:
        # 未启用合并策略: 逐条生成SQL
        sql_logger.info("[SQL合并] 合并策略已禁用, 逐条生成SQL")
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

    # 更新合同主表汇总金额
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

    # 生成回退语句
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

    sql_logger.info(f"[SQL合并] SQL生成完成, 总行数={len(sql)}")
    return "\n".join(sql)


def download_contract_price_template(request):
    """下载合同单价修改Excel模板"""
    if not OPENPYXL_AVAILABLE:
        return render(request, 'error.html', {'error': '服务器缺少 openpyxl 库'})

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = '合同明细单价修改'
    ws.append(['明细行ID', '单价', '数量', '原单价', '原数量'])
    ws.append(['BPO-EXAMPLE-000001', 100, 1, None, None])

    bio = io.BytesIO()
    wb.save(bio)
    bio.seek(0)

    response = FileResponse(bio, as_attachment=True,
                            filename='contract_price_template.xlsx')
    response['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    return response


def contract_detail_price_view(request):
    """合同明细单价修改视图 - 支持单条和批量导入"""
    saved_file = None

    if request.method == 'POST':
        form = ContractDetailPriceForm(request.POST, request.FILES)
        if form.is_valid():
            cd = form.cleaned_data
            log_view_input("合同明细单价修改", cd)

            ops_remark = parse_ops_remark(cd.get('ops_remark', ''))

            if cd.get('excel_file'):
                # Excel批量导入模式
                records = parse_price_excel(cd['excel_file'])
                sql_content = generate_price_sql_bulk(records, ops_remark)
            else:
                # 单条记录模式 - 也使用SQL合并策略
                new_quantity = cd.get('new_quantity')
                new_price = cd.get('new_price')
                orig_quantity = cd.get('orig_quantity')
                orig_price = cd.get('orig_price')

                single_record = {
                    'line_id': cd['single_line_id'],
                    'price': new_price,
                    'quantity': new_quantity,
                    'orig_price': orig_price,
                    'orig_quantity': orig_quantity
                }
                sql_content = generate_price_sql_bulk(
                    [single_record], ops_remark)

            # 保存SQL到固定目录
            saved_file = save_sql_file(
                sql_content, '修改合同明细单价', cd.get('dynamic_id'))
    else:
        form = ContractDetailPriceForm()

    return render(request, 'contract_price_form.html', {
        'form': form,
        'saved_file': saved_file,
        'active_menu': 'contract_price',
        'sidebar_groups': SIDEBAR_GROUPS,
    })


# 为了兼容旧代码,保留contract_price_view作为别名
contract_price_view = contract_detail_price_view
download_price_template = download_contract_price_template


__all__ = [
    'parse_price_excel',
    'generate_price_sql_bulk',
    'download_contract_price_template',
    'download_price_template',
    'contract_detail_price_view',
    'contract_price_view',
]
