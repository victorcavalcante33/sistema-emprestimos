from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from PELFCRED_APP.views import home, cadastrar_cliente, lista_clientes, cadastrar_emprestimo, registrar_pagamento
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('', home, name='home'),
    path('cadastrar_cliente/', cadastrar_cliente, name='cadastrar_cliente'),
    path('lista_clientes/', lista_clientes, name='lista_clientes'),
    path('cadastrar_emprestimo/', cadastrar_emprestimo, name='cadastrar_emprestimo'),
    path('registrar_pagamento/<int:id_emprestimo>/', registrar_pagamento, name='registrar_pagamento'),
    path('pelfcred/', include('PELFCRED_APP.urls')),
]
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)