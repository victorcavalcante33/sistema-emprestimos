from django import template
import re
register = template.Library()
@register.filter(name='format_cpf')
def format_cpf(value):
    return re.sub(r'(\d{3})(\d{3})(\d{3})(\d{2})', r'\1.\2.\3-\4', str(value))
@register.filter(name='format_cnpj')
def format_cnpj(value):
    return re.sub(r'(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})', r'\1.\2.\3/\4-\5', str(value))
@register.filter(name='format_telefone')
def format_telefone(value):
    return re.sub(r'(\d{2})(\d{4})(\d{4})', r'(\1) \2-\3', str(value))
@register.filter(name='format_cep')
def format_cep(value):
    return re.sub(r'(\d{5})(\d{3})', r'\1-\2', str(value))
@register.filter(name='somente_numeros')
def somente_numeros(value):
    """Removes all non-numeric characters from the input string."""
    return re.sub(r'\D', '', str(value))


@register.filter(name='is_pdf')
def is_pdf(value):
    return value.endswith('.pdf')

@register.filter
def toggle_order(current_order, orders):
    """
    Toggles between two order values.
    Usage: {{ current_order|toggle_order:"asc,desc" }}
    """
    asc_order, desc_order = orders.split(',')
    if current_order == asc_order:
        return desc_order
    else:
        return asc_order

@register.filter
def add_class(field, css_class):
    """Adiciona uma classe CSS a um campo do formulário."""
    return field.as_widget(attrs={"class": css_class})

@register.filter
def add_error_class(field_errors):
    """Adiciona a classe is-invalid se houver erros."""
    return 'is-invalid' if field_errors else ''

@register.filter
def get_item(dictionary, key):
    # Verifica se 'dictionary' é de fato um dicionário antes de acessar o método 'get'
    if isinstance(dictionary, dict):
        return dictionary.get(key, '')
    return ''