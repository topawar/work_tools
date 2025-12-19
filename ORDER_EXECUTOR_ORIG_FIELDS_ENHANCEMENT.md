# 订单执行人修改 - 原字段允许为空功能增强

## 需求描述
用户要求在订单执行人修改功能中，原订单执行人账号和原订单执行人名称都允许为空，不进行强制验证。

## 实现方案

### 1. 后端表单验证修改 (`work_tools/forms.py`)

**修改位置**: `OrderExecutorUpdateForm.clean()` 方法

**修改前**:
```python
# 验证原订单执行人账号（如果填写了）
if orig_order_executor:
    if not UserOrgDetail.objects.filter(login_name=orig_order_executor).exists():
        raise forms.ValidationError(f"原订单执行人账号 {orig_order_executor} 不存在，请检查后重试。")
```

**修改后**:
```python
# 原订单执行人账号和名称允许为空，不进行强制验证
# 即使填写了也不验证有效性，因为可能是历史数据或其他特殊情况
```

**说明**: 完全移除了对原订单执行人账号的强制验证，允许任何值（包括空值和无效值）。

### 2. 后端SQL生成逻辑修改 (`work_tools/views/order_executor.py`)

**修改位置**: `_generate_sqls()` 函数中的回退SQL生成逻辑

**修改前**:
```python
orig_user_org = UserOrgDetail.objects.filter(login_name=orig_order_executor).first()
if not orig_user_org:
    validation_failures.append({
        'row': row_idx,
        'orig_order_executor': orig_order_executor,
        'error': f'未找到原订单执行人信息：{orig_order_executor}'
    })
    continue
```

**修改后**:
```python
orig_user_org = UserOrgDetail.objects.filter(login_name=orig_order_executor).first()

# 如果原订单执行人账号无效，使用提供的名称或空值，不报错
if not orig_user_org:
    # 使用提供的原订单执行人名称，如果没有则为空
    orig_executor_name = item.get('orig_order_executor_name', '')
    
    # 生成回退SQL（使用提供的信息或空值）
    # ... SQL生成逻辑
    continue
```

**说明**: 当原订单执行人账号在数据库中不存在时，不再报错，而是使用用户提供的原订单执行人名称生成回退SQL。

### 3. 前端界面优化 (`work_tools/templates/order_executor_form.html`)

**修改1**: 添加字段说明
```html
<div class="help-text">原订单执行人账号，允许为空（原本可能就没有执行人）</div>
```

**修改2**: JavaScript验证逻辑优化
```javascript
// 原订单执行人允许无效，不阻止提交
isOrigExecutorValid = true;
```

**说明**: 
- 为原订单执行人账号字段添加了明确的提示说明
- 修改JavaScript验证逻辑，确保即使原账号无效也不会阻止表单提交

## 支持的使用场景

### 场景1: 补充订单执行人（原本为空）
- **输入**: 原订单执行人账号为空，原订单执行人名称为空
- **行为**: 正常处理，回退时清空所有相关字段
- **用途**: 为原本没有执行人的订单补充执行人信息

### 场景2: 修改订单执行人（原本有值且有效）
- **输入**: 原订单执行人账号有效，系统自动填充名称
- **行为**: 查询数据库获取完整的原执行人信息用于回退
- **用途**: 标准的执行人修改场景

### 场景3: 历史数据处理（原账号无效）
- **输入**: 原订单执行人账号无效，手动填写原订单执行人名称
- **行为**: 使用用户提供的信息生成回退SQL，不验证账号有效性
- **用途**: 处理历史数据或特殊情况，允许用户手动指定原始信息

## 功能特点

### ✅ 灵活性
- 原订单执行人账号和名称都允许为空
- 支持无效的原账号（历史数据场景）
- 不强制验证原字段的有效性

### ✅ 用户友好
- 清晰的字段说明和提示
- 自动填充功能（当账号有效时）
- 手动填写选项（当账号无效时）

### ✅ 数据完整性
- 仍然验证新执行人账号的有效性
- 支持多种回退策略
- 保持SQL生成的准确性

## 测试验证

运行测试脚本验证功能：
```bash
python test_order_executor_simple.py
```

测试覆盖：
- ✓ 表单验证逻辑（原字段为空/无效）
- ✓ SQL生成逻辑（三种场景）
- ✓ 前端验证逻辑（不阻止提交）

## 总结

此次修改完全满足了用户的需求：
1. **原订单执行人账号允许为空** - 支持补充执行人场景
2. **原订单执行人名称允许为空** - 不强制要求填写
3. **原字段无效时不报错** - 支持历史数据和特殊情况
4. **保持功能完整性** - 仍然支持正常的修改和回退操作

修改后的功能更加灵活和用户友好，能够处理各种实际业务场景。