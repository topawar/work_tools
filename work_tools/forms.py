from django import forms

class StripWhitespaceMixin:
    def clean(self):
        cleaned_data = super().clean()
        for k, v in list(cleaned_data.items()):
            if isinstance(v, str):
                field = self.fields.get(k)
                if field and isinstance(field.widget, forms.Textarea):
                    cleaned_data[k] = v.strip()
                else:
                    cleaned_data[k] = v.strip().replace("\r", "").replace("\n", "")
        return cleaned_data

class OrgImportForm(StripWhitespaceMixin, forms.Form):
    csv_file = forms.FileField(
        label="CSV 文件（列：company_code, company_name, plate_code, plate_name）",
        required=True,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
    )
    

class ItemImportForm(StripWhitespaceMixin, forms.Form):
    csv_file = forms.FileField(
        label="CSV 文件（列：item_id, item_name, category, item_uom, purc_type）",
        required=True,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
    )
    
    batch_size = forms.IntegerField(
        label="批大小",
        required=False,
        initial=2000,
        min_value=100,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )

    

class UnitChangeForm(StripWhitespaceMixin, forms.Form):
    dynamic_id = forms.CharField(
        label="动态编号（如变更单号）",
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    ops_remark = forms.CharField(
        label="操作备注（支持解析ONES链接）",
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '输入任务描述或ONES链接'})
    )

    # 修改类型取消：通过是否填写新字段来自动判断修改内容

    old_drafting_id = forms.CharField(
        label="原起草单位ID", 
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    old_drafting_name = forms.CharField(
        label="原起草单位名称", 
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    new_drafting_id = forms.CharField(
        label="新起草单位ID", 
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    new_drafting_name = forms.CharField(
        label="新起草单位名称", 
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    old_party_id = forms.CharField(
        label="原签约主体ID", 
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    old_party_name = forms.CharField(
        label="原签约主体名称", 
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    new_party_id = forms.CharField(
        label="新签约主体ID", 
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    new_party_name = forms.CharField(
        label="新签约主体名称", 
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    scheme_no = forms.CharField(
        label="采购方案编号（单条）", 
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    inquiry_no = forms.CharField(
        label="询价单编号（单条）", 
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    result_no = forms.CharField(
        label="定标结果编号（单条）", 
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    excel_file = forms.FileField(
        label="或上传 Excel（列：采购方案编号/询价单编号/定标结果编号；可选：新起草单位ID/新起草单位名称/新签约主体ID/新签约主体名称；原起草单位/原签约主体用于回退）",
        required=False,
        help_text=".xlsx；每行可配置不同新值；为空则不修改；原字段用于生成精确回退",
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
    )

    def clean(self):
        cleaned_data = super().clean()
        excel = cleaned_data.get('excel_file')
        single = any([
            cleaned_data.get('scheme_no'),
            cleaned_data.get('inquiry_no'),
            cleaned_data.get('result_no')
        ])

        if not excel and not single:
            raise forms.ValidationError("请至少填写单条记录或上传 Excel 文件。")
        if excel and single:
            raise forms.ValidationError("不能同时填写单条记录和上传 Excel 文件。")
        return cleaned_data


class ContractDetailPriceForm(StripWhitespaceMixin, forms.Form):
    dynamic_id = forms.CharField(
        label="动态编号（如变更单号）",
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    ops_remark = forms.CharField(
        label="操作备注（支持解析ONES链接）",
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '输入任务描述或ONES链接'})
    )

    new_quantity = forms.DecimalField(
        label="新数量",
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    
    new_price = forms.DecimalField(
        label="新单价",
        decimal_places=8,
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.00000001'})
    )

    orig_quantity = forms.DecimalField(
        label="原数量（可选）",
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    orig_price = forms.DecimalField(
        label="原单价（可选）",
        decimal_places=8,
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.00000001'})
    )

    # 单条合同明细行ID
    single_line_id = forms.CharField(
        label="合同明细行ID（单条）",
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    # Excel批量导入
    excel_file = forms.FileField(
        label="或上传 Excel（列：明细行ID/单价；可选：数量/原数量/原单价）",
        required=False,
        help_text=".xlsx；至少提供明细行ID与单价；可选原字段用于回退",
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
    )

class ContractItemUpdateForm(StripWhitespaceMixin, forms.Form):
    dynamic_id = forms.CharField(
        label="动态编号（如变更单号）",
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    ops_remark = forms.CharField(
        label="操作备注（支持解析ONES链接）",
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '输入任务描述或ONES链接'})
    )

    single_line_id = forms.CharField(
        label="合同明细行ID（单条）",
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    new_item_id = forms.CharField(label="新物资编码", required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    new_item_name = forms.CharField(label="新物资名称", required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    new_item_uom = forms.CharField(label="新计量单位", required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    new_category = forms.CharField(label="新物资分类编码", required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))

    orig_item_id = forms.CharField(label="原物资编码（可选）", required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    orig_item_name = forms.CharField(label="原物资名称（可选）", required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    orig_item_uom = forms.CharField(label="原计量单位（可选）", required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    orig_category = forms.CharField(label="原物资分类编码（可选）", required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))

    excel_file = forms.FileField(
        label="或上传 Excel（列：明细行ID/单价/数量为示例列名，物资列支持：物资编码/物资名称/计量单位/物资分类编码；支持英文与SQL字段名）",
        required=False,
        help_text=".xlsx；至少提供明细行ID与任意一个新物资字段。可选原物资字段用于回退",
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
    )

    def clean(self):
        cleaned_data = super().clean()
        single_line_id = cleaned_data.get('single_line_id')
        excel_file = cleaned_data.get('excel_file')
        
        # 验证必须提供单条记录或上传Excel文件
        if not single_line_id and not excel_file:
            raise forms.ValidationError("请至少填写单条合同明细行ID或上传Excel文件")
        
        # 验证不能同时提供单条记录和上传Excel文件
        if single_line_id and excel_file:
            raise forms.ValidationError("不能同时填写单条合同明细行ID和上传Excel文件")

        if single_line_id and not excel_file:
            if not cleaned_data.get('new_item_id'):
                raise forms.ValidationError("单条提交时新物资编码为必填项")

        return cleaned_data

class ContractBudgetUpdateForm(StripWhitespaceMixin, forms.Form):
    dynamic_id = forms.CharField(
        label="动态编号（如变更单号）",
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    ops_remark = forms.CharField(
        label="操作备注（支持解析ONES链接）",
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '输入任务描述或ONES链接'})
    )
    contract_bpo_id = forms.CharField(
        label="合同编号（可选）",
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    section_no = forms.CharField(
        label="询价单标段编号（单条）",
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    supplier_id = forms.CharField(
        label="供应商ID（可选）",
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    new_budget = forms.DecimalField(
        label="新预算金额/单价",
        decimal_places=8,
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.00000001'})
    )
    orig_budget = forms.DecimalField(
        label="原预算金额/单价（可选，用于回退）",
        decimal_places=8,
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.00000001'})
    )
    excel_file = forms.FileField(
        label="或上传 Excel（列：合同编号/询价单标段编号/供应商ID(可选)/新预算/原预算）",
        required=False,
        help_text=".xlsx；至少提供标段编号或合同编号与新预算；可选供应商ID以增加限定；原预算用于回退",
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
    )

    def clean(self):
        cd = super().clean()
        excel = cd.get('excel_file')
        single = any([
            cd.get('section_no'),
            cd.get('contract_bpo_id')
        ]) and (cd.get('new_budget') is not None)
        if not excel and not single:
            raise forms.ValidationError("请填写单条标段或合同号及新预算，或上传Excel文件")
        if excel and (cd.get('section_no') or cd.get('contract_bpo_id') or (cd.get('new_budget') is not None)):
            raise forms.ValidationError("不能同时填写单条记录和上传Excel文件")
        return cd

class ErpTerminateForm(StripWhitespaceMixin, forms.Form):
    dynamic_id = forms.CharField(
        label="动态编号（如变更单号）",
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    ops_remark = forms.CharField(
        label="操作备注（支持解析ONES链接）",
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '输入任务描述或ONES链接'})
    )
    inq_id = forms.CharField(label="询价单编号（单条）", required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    purchase_scheme_no = forms.CharField(label="采购方案编号（单条）", required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    purchase_package_no = forms.CharField(label="PURCHASE_PACKAGE_NO（单条）", required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    excel_file = forms.FileField(
        label="或上传 Excel（列：询价单编号/采购方案编号/PURCHASE_PACKAGE_NO）",
        required=False,
        help_text=".xlsx；至少提供任一列以生成对应SQL",
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
    )
    def clean(self):
        cleaned_data = super().clean()
        inq_id = cleaned_data.get('inq_id')
        sch = cleaned_data.get('purchase_scheme_no')
        pkg = cleaned_data.get('purchase_package_no')
        excel_file = cleaned_data.get('excel_file')
        if not excel_file and not (inq_id or sch or pkg):
            raise forms.ValidationError("请至少填写单条ID或上传Excel文件")
        if excel_file and (inq_id or sch or pkg):
            raise forms.ValidationError("不能同时填写单条并上传Excel")
        return cleaned_data



class GovReportForm(StripWhitespaceMixin, forms.Form):
    dynamic_id = forms.CharField(
        label="动态编号（如变更单号）",
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    ops_remark = forms.CharField(
        label="操作备注（支持解析ONES链接）",
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '输入任务描述或ONES链接'})
    )

    scheme_no = forms.CharField(
        label="采购方案编号（可选）",
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    inq_id = forms.CharField(
        label="询价单编号（可选）",
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    bpo_id = forms.CharField(
        label="合同编号（可选）",
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    REPORT_CHOICES = [
        ('yes', '是（报送）'),
        ('no', '否（不报送）'),
    ]
    report_choice = forms.ChoiceField(
        label="是否报送（单条）",
        choices=REPORT_CHOICES,
        required=False,
        widget=forms.RadioSelect
    )
    orig_report_choice = forms.ChoiceField(
        label="回退是否报送（单条，可选）",
        choices=REPORT_CHOICES,
        required=False,
        widget=forms.RadioSelect
    )

    excel_file = forms.FileField(
        label="或上传 Excel（列：采购方案编号/询价单编号/合同编号/是否报送(是/否)）",
        required=False,
        help_text=".xlsx；每行任意提供方案/询价/合同之一；填写“是否报送”为是/否",
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
    )

    def clean(self):
        cd = super().clean()
        excel = cd.get('excel_file')
        single_any = any([cd.get('scheme_no'), cd.get('inq_id'), cd.get('bpo_id')])
        if not excel and not single_any:
            raise forms.ValidationError("请至少填写方案/询价/合同之一，或上传Excel文件")
        if excel and single_any:
            raise forms.ValidationError("不能同时填写单条记录和上传Excel文件")
        if not excel and single_any and not cd.get('report_choice'):
            raise forms.ValidationError("单条模式需选择是否报送")
        return cd


class ImportanceForm(StripWhitespaceMixin, forms.Form):
    dynamic_id = forms.CharField(
        label="动态编号（如变更单号）",
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    ops_remark = forms.CharField(
        label="操作备注（支持解析ONES链接）",
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '输入任务描述或ONES链接'})
    )

    scheme_no = forms.CharField(
        label="采购方案编号（可选）",
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    inq_id = forms.CharField(
        label="询价单编号（可选）",
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    bpo_id = forms.CharField(
        label="合同号（BPO_ID，可选）",
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    IMPORTANCE_CHOICES = [
        ('0', '一般准入备案类 0'),
        ('1', '一般自行管理类 1'),
        ('4', '一般 4'),
        ('3', '核心 3'),
        ('2', '重要 2'),
    ]
    importance_choice = forms.ChoiceField(
        label="物项重要性（单条）",
        choices=IMPORTANCE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    orig_importance_choice = forms.ChoiceField(
        label="原重要性（可选，用于回退）",
        choices=IMPORTANCE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    excel_file = forms.FileField(
        label="或上传 Excel（列：采购方案编号/询价单编号/合同编号/物项重要性/原重要性）",
        required=False,
        help_text=".xlsx；每行任意提供方案/询价/合同之一；原重要性用于回退",
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
    )

    def clean(self):
        cd = super().clean()
        excel = cd.get('excel_file')
        single_any = any([cd.get('scheme_no'), cd.get('inq_id'), cd.get('bpo_id')])
        if not excel and not single_any:
            raise forms.ValidationError("请至少填写方案/询价/合同之一，或上传Excel文件")
        if excel and single_any:
            raise forms.ValidationError("不能同时填写单条记录和上传Excel文件")
        if not excel and single_any and not cd.get('importance_choice'):
            raise forms.ValidationError("单条模式需选择物项重要性")
        return cd


class EndDateUpdateForm(StripWhitespaceMixin, forms.Form):
    dynamic_id = forms.CharField(
        label="动态编号（如变更单号）",
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    ops_remark = forms.CharField(
        label="操作备注（支持解析ONES链接）",
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '输入任务描述或ONES链接'})
    )

    end_date = forms.CharField(
        label="新失效日期（YYYYMMDD）",
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '如 20251125'})
    )

    orig_end_date = forms.CharField(
        label="原失效日期（可选，用于回退）",
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '如 20251105'})
    )

    bpo_id = forms.CharField(
        label="合同编号（单条）",
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )


    excel_file = forms.FileField(
        label="或上传 Excel（列：合同编号/新失效日期/原失效日期）",
        required=False,
        help_text=".xlsx；至少提供合同编号与新失效日期；原失效日期用于回退",
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
    )

    def clean(self):
        cd = super().clean()
        excel = cd.get('excel_file')
        single_any = bool(cd.get('bpo_id'))
        if not excel and not single_any:
            raise forms.ValidationError("请填写单条/批量合同号，或上传Excel文件")
        if excel and single_any:
            raise forms.ValidationError("不能同时填写单条合同号和上传Excel文件")
        if not excel and single_any and not cd.get('end_date'):
            raise forms.ValidationError("需填写新失效日期")
        return cd
class FloatingPriceTypeForm(StripWhitespaceMixin, forms.Form):
    dynamic_id = forms.CharField(
        label="动态编号（如变更单号）",
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    ops_remark = forms.CharField(
        label="操作备注（支持解析ONES链接）",
        max_length=200,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '输入任务描述或ONES链接'})
    )
    bpo_id = forms.CharField(label="合同编号（单条）", required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    excel_file = forms.FileField(
        label="或上传 Excel（列：合同编号）",
        required=False,
        help_text=".xlsx；提供合同编号即可，系统将执行由10→20的固定修改，回退为20→10",
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
    )
    def clean(self):
        cd = super().clean()
        excel = cd.get('excel_file')
        has_single = bool(cd.get('bpo_id'))
        if not excel and not has_single:
            raise forms.ValidationError("请填写单条合同编号，或上传Excel文件")
        if excel and cd.get('bpo_id'):
            raise forms.ValidationError("不能同时填写单条并上传Excel")
        if not cd.get('ops_remark'):
            raise forms.ValidationError("操作备注为必填项")
        return cd
