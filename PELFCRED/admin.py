from django.contrib import admin
from .models import Cliente, Emprestimo, Pagamento

# Registrar modelos para gerenciar no Django Admin
admin.site.register(Cliente)
admin.site.register(Emprestimo)
admin.site.register(Pagamento)
