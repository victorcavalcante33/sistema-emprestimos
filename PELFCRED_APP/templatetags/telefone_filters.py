from django import template

register = template.Library()

@register.filter
def formata_telefone(valor):
    if valor is None:
        return ''  # Retorna uma string vazia se o valor for None
    if len(valor) == 11:  # Celular
        return f"({valor[:2]}) {valor[2]} {valor[3:7]}-{valor[7:]}"
    elif len(valor) == 10:  # Telefone fixo
        return f"({valor[:2]}) {valor[2:6]}-{valor[6:]}"
    return valor  # Retorna o valor como está se não corresponder a 10 ou 11 dígitos