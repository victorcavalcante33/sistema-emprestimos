from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from django.conf.urls.static import static
from django.conf import settings
from django.http import HttpResponse

def empty_favicon(request):
    return HttpResponse(status=204)

app_name = 'PELFCRED'

urlpatterns = [
    path('', views.totais, name='home'),
    path('cadastrar_cliente/', views.cadastrar_cliente, name='cadastrar_cliente'),
    path('lista_clientes/', views.lista_clientes, name='lista_clientes'),
    path('editar_cliente/<str:cpf>/', views.editar_cliente, name='editar_cliente'),
    path('clientes/excluir/<str:cpf>/', views.excluir_cliente, name='excluir_cliente'),
    path('detalhes_cliente/<str:cpf>/', views.detalhes_cliente, name='detalhes_cliente'), 
    path('cadastrar_emprestimo/<str:cpf>/', views.cadastrar_emprestimo, name='cadastrar_emprestimo'),
    path('lista_emprestimos/', views.lista_emprestimos, name='lista_emprestimos'),
    path('registrar_pagamento/<int:id_emprestimo>/', views.registrar_pagamento, name='registrar_pagamento'),
    path('buscar_cliente/', views.buscar_cliente, name='buscar_cliente'),
    path('renovar_emprestimo/<int:id>/', views.renovar_emprestimo, name='renovar_emprestimo'),
    path('editar_emprestimo/<int:id>/', views.editar_emprestimo, name='editar_emprestimo'),
    path('excluir_emprestimo/<int:id>/', views.excluir_emprestimo, name='excluir_emprestimo'),
    path('analisar_pagamentos/', views.analisar_pagamentos, name='analisar_pagamentos'),
    path('rejeitar_pagamento/<int:pagamento_id>/', views.rejeitar_pagamento, name='rejeitar_pagamento'),
    path('atualizar_pagamento/<int:pagamento_id>/', views.atualizar_pagamento, name='atualizar_pagamento'),
    path('importar_comprovante_pix/', views.importar_comprovante_pix, name='importar_comprovante_pix'),
    path('editar-parcelas/<int:id_emprestimo>/', views.editar_parcelas, name='editar_parcelas'),
    path('pelfcred/cadastrar_emprestimo/', views.cadastrar_emprestimo, name='cadastrar_emprestimo_sem_cpf'),
    path('registrar_pagamento/', views.registrar_pagamento, name='registrar_pagamento_sem_emprestimo'),
    path('totais/', views.totais, name='totais'),
    path('historico_pagamentos/<int:id_emprestimo>/', views.historico_pagamentos, name='historico_pagamentos'),
    path('alterar_status_cliente/<str:cpf>/', views.alterar_status_cliente, name='alterar_status_cliente'),
    path('clientes/', views.lista_clientes, name='lista_clientes'),
    path('clientes/exportar_csv/', views.exportar_csv, name='exportar_csv'),
    path('clientes/exportar_pdf/', views.exportar_pdf, name='exportar_pdf'),
    path('finalizar_contrato/<int:id_emprestimo>/', views.finalizar_contrato, name='finalizar_contrato'),
    path('marcar_inadimplente/<int:id_emprestimo>/', views.marcar_inadimplente, name='marcar_inadimplente'),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
]
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)