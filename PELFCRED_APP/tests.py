from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User, Group

class ListaClientesViewTest(TestCase):

    def setUp(self):
        # Cria um usuário e um grupo para o teste
        self.grupo = Group.objects.create(name="Test Group")
        self.user = User.objects.create_user(username="testuser", password="12345")
        self.user.groups.add(self.grupo)
        self.user.save()

        # Loga o usuário para as views protegidas
        self.client.login(username="testuser", password="12345")

        # Cria um cliente associado ao grupo do usuário
        Cliente.objects.create(nome="Cliente Teste", cpf="12345678901", grupo=self.grupo)

    def test_lista_clientes_status_code(self):
        response = self.client.get(reverse('lista_clientes'))
        self.assertEqual(response.status_code, 200)

    def test_lista_clientes_template(self):
        response = self.client.get(reverse('lista_clientes'))
        self.assertTemplateUsed(response, 'lista_clientes.html')

    def test_lista_clientes_conteudo(self):
        response = self.client.get(reverse('lista_clientes'))
        self.assertContains(response, "Cliente Teste")
        
        from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User, Group
from .models import Cliente, Emprestimo

class HomeViewTest(TestCase):
    
    def setUp(self):
        # Configuração de dados de teste
        self.admin_group = Group.objects.create(name='admin')
        self.user_group = Group.objects.create(name='user')

        self.admin_user = User.objects.create_user(username='admin', password='adminpass')
        self.admin_user.groups.add(self.admin_group)

        self.user = User.objects.create_user(username='normal_user', password='userpass')
        self.user.groups.add(self.user_group)

        self.cliente_admin = Cliente.objects.create(nome='Cliente Admin', grupo=self.admin_group, usuario=self.admin_user)
        self.cliente_user = Cliente.objects.create(nome='Cliente User', grupo=self.user_group, usuario=self.user)

        self.emprestimo_admin = Emprestimo.objects.create(cliente=self.cliente_admin, capital=1000, taxa_juros=2.5)
        self.emprestimo_user = Emprestimo.objects.create(cliente=self.cliente_user, capital=500, taxa_juros=1.5)

    def test_home_view_admin(self):
        # Verifica se o admin consegue ver os dados de todos os grupos
        self.client.login(username='admin', password='adminpass')
        response = self.client.get(reverse('PELFCRED_APP:home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Cliente Admin')
        self.assertContains(response, 'Cliente User')

    def test_home_view_normal_user(self):
        # Verifica se um usuário normal vê apenas os dados do seu grupo
        self.client.login(username='normal_user', password='userpass')
        response = self.client.get(reverse('PELFCRED_APP:home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Cliente User')
        self.assertNotContains(response, 'Cliente Admin')

