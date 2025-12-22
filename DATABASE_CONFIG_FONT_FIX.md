# 数据库配置页面字体问题修复

## 问题描述
进入数据库配置管理页面时，全局字体会发生改变，影响其他页面的显示。

## 根本原因
`work_tools/static/css/system-pages.css` 文件中使用了全局CSS选择器：

```css
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft YaHei', sans-serif;
    font-size: 14px;
    line-height: 1.6;
    color: #333;
    background: #f5f5f5;
}
```

这些全局选择器会影响整个页面的所有元素，包括侧边栏和其他组件。

## 修复方案
将全局样式限定在特定的作用域内，只影响数据库配置页面本身。

### 修改的文件

#### 1. work_tools/static/css/system-pages.css
**修改前**:
```css
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft YaHei', sans-serif;
    font-size: 14px;
    line-height: 1.6;
    color: #333;
    background: #f5f5f5;
}
```

**修改后**:
```css
/* 仅在数据库配置页面应用样式 */
.database-config-page {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft YaHei', sans-serif;
    font-size: 14px;
    line-height: 1.6;
    color: #333;
    background: #f5f5f5;
}
```

#### 2. work_tools/templates/modules/system_config/database_config.html
**修改前**:
```html
<body>
    {% include 'sidebar.html' %}
```

**修改后**:
```html
<body class="database-config-page">
    {% include 'sidebar.html' %}
```

## 修复效果

### 修复前
- ❌ 进入数据库配置页面后，全局字体改变
- ❌ 侧边栏字体受影响
- ❌ 其他页面元素样式被覆盖

### 修复后
- ✅ 数据库配置页面保持独立样式
- ✅ 侧边栏字体不受影响
- ✅ 其他页面元素样式正常
- ✅ 页面切换时字体保持一致

## 最佳实践

### 避免使用全局选择器
```css
/* ❌ 不推荐 - 影响所有元素 */
* {
    margin: 0;
    padding: 0;
}

body {
    font-family: Arial;
}

/* ✅ 推荐 - 使用特定的class */
.my-page {
    font-family: Arial;
}

.my-page * {
    margin: 0;
    padding: 0;
}
```

### CSS作用域隔离
1. 为每个独立页面使用唯一的class
2. 所有样式都嵌套在这个class下
3. 避免使用 `*`, `body`, `html` 等全局选择器

### 示例
```css
/* 页面特定样式 */
.database-config-page {
    /* 页面级样式 */
}

.database-config-page .container {
    /* 容器样式 */
}

.database-config-page .btn {
    /* 按钮样式 */
}
```

## 相关文件
- `work_tools/static/css/system-pages.css` - 系统页面样式
- `work_tools/templates/modules/system_config/database_config.html` - 数据库配置页面模板

## 测试建议
1. 访问数据库配置管理页面
2. 检查页面字体是否正常
3. 切换到其他页面
4. 确认其他页面字体未受影响
5. 返回数据库配置页面
6. 确认样式保持一致

## 日期
2024-12-19
