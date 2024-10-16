from django.contrib.auth.models import Group

def admin_status(request):
    # Verifica se o usuário está no grupo 'admin' ou é superusuário
    is_admin = request.user.is_authenticated and (request.user.is_superuser or request.user.groups.filter(name='admin').exists())
    return {'is_admin': is_admin}