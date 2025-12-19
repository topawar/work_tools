from django import template
from django.forms import BoundField

register = template.Library()


@register.filter(name='add_class')
def add_class(field, css_class):
    """
    为表单字段添加CSS类
    
    用法:
    {{ form.field_name|add_class:"form-input" }}
    """
    if hasattr(field, 'as_widget'):
        return field.as_widget(attrs={'class': css_class})
    return field


@register.inclusion_tag('tags/render_field.html')
def render_field(field, input_class='', label_class='', help_text=''):
    """
    渲染表单字段的自定义标签
    
    用法:
    {% render_field form.field_name input_class="form-input" label_class="form-label" %}
    """
    # 如果提供了input_class，则添加到字段的widget属性中
    rendered_field = field
    if input_class and hasattr(field, 'as_widget'):
        rendered_field = field.as_widget(attrs={'class': input_class})
    
    return {
        'field': field,
        'rendered_field': rendered_field,
        'input_class': input_class,
        'label_class': label_class,
        'help_text': help_text or (field.help_text if hasattr(field, 'help_text') else ''),
    }