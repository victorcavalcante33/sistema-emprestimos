from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Sum, F, ExpressionWrapper, DecimalField, Case, When, Value
from django.contrib import messages
from django.contrib.auth.models import Group, User
from decimal import Decimal, InvalidOperation
from .models import Emprestimo, Pagamento, Cliente, Parcela, Saida, DescontoJuros, BonusJuros, JurosRecebido
from .forms import EmprestimoForm, ClienteForm, ComprovantePIXForm, EditarEmprestimoForm
from datetime import timedelta, datetime, date
import logging
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.template.loader import get_template
from xhtml2pdf import pisa
import csv
from django.utils.dateparse import parse_date
from django.contrib.auth.decorators import user_passes_test
from django.db import transaction
from django.contrib.auth import authenticate, login
from django.utils.timezone import now, localtime


@login_required
def load_usuarios(request):
    grupo_id = request.GET.get('grupo_id')
    if grupo_id:
        usuarios = User.objects.filter(groups__id=grupo_id).order_by('username')
    else:
        usuarios = User.objects.none()
    usuarios_data = [{'id': usuario.id, 'username': usuario.username} for usuario in usuarios]
    return JsonResponse({'usuarios': usuarios_data})

@login_required
@user_passes_test(lambda u: u.is_superuser)
def excluir_desconto(request, desconto_id):
    if request.method == 'POST':
        desconto = get_object_or_404(DescontoJuros, id=desconto_id)
        desconto.delete()
        messages.success(request, 'Desconto excluído com sucesso.')
    else:
        messages.error(request, 'Ação inválida.')
    return redirect('PELFCRED_APP:totais')
logger = logging.getLogger(__name__)

@login_required
def editar_parcelas(request, id_emprestimo):
    emprestimo = get_object_or_404(Emprestimo, id=id_emprestimo)
    parcelas = Parcela.objects.filter(emprestimo=emprestimo)

    # Obtenção do número de parcelas a partir do empréstimo ou atribui um valor padrão (exemplo: 1)
    numero_parcelas = emprestimo.numero_parcelas if emprestimo.numero_parcelas else 1

    # Se as parcelas ainda não foram criadas ou o número de parcelas mudou, cria novas parcelas
    if not parcelas.exists() or numero_parcelas != parcelas.count():
        # Apaga as parcelas antigas
        parcelas.delete()

        # Definir a data de início corretamente
        data_inicio = emprestimo.data_inicio + timedelta(days=1)  # Ajuste para calcular a primeira parcela corretamente
        frequencia = emprestimo.frequencia

        # Dicionário de frequências
        dias_frequencia = {
            'diaria': 1,
            'semanal': 7,
            'quinzenal': 15,
            'mensal': 30
        }

        # Criar as novas parcelas com base na frequência
        for i in range(numero_parcelas):
            data_vencimento = data_inicio + timedelta(days=dias_frequencia[frequencia] * i)
            Parcela.objects.create(
                emprestimo=emprestimo,
                data_vencimento=data_vencimento,
                pago=False
            )

        # Atualizar as parcelas depois de criadas
        parcelas = Parcela.objects.filter(emprestimo=emprestimo)

    # Processamento do formulário POST
    if request.method == 'POST':
        if 'confirm' in request.POST:
            for parcela in parcelas:
                nova_data_vencimento = request.POST.get(f'data_vencimento_parcela_{parcela.id}')
                if nova_data_vencimento:
                    parcela.data_vencimento = nova_data_vencimento
                    parcela.save()

            # Atualizar o saldo devedor após editar parcelas, se necessário
            emprestimo.saldo_devedor = emprestimo.calcular_saldo_devedor()
            emprestimo.save()

            messages.success(request, 'Parcelas atualizadas com sucesso.')
            return redirect('PELFCRED_APP:lista_emprestimos')

        elif 'cancel' in request.POST:
            # Aqui podemos apagar o empréstimo, se desejado
            emprestimo.delete()  # Apaga o empréstimo se o usuário cancelar
            messages.info(request, 'Edição de parcelas cancelada e empréstimo removido.')
            return redirect('PELFCRED_APP:lista_emprestimos')
        
        

    return render(request, 'editar_parcelas.html', {'emprestimo': emprestimo, 'parcelas': parcelas})

@login_required
def buscar_cliente(request):
    search_query = request.GET.get('search', '').strip()
    logger.debug(f"Busca de cliente iniciada com o termo: {search_query}")
    print(f"Buscando cliente com o termo: {search_query}")

    cliente = Cliente.objects.filter(
        Q(cpf__icontains=search_query) | 
        Q(nome__icontains=search_query) | 
        Q(apelido__icontains=search_query)
    ).first()

    if cliente:
        logger.debug(f"Cliente encontrado: {cliente.nome} - CPF: {cliente.cpf}")
        contratos = Emprestimo.objects.filter(cliente=cliente).values(
            'id', 'valor_total', 'capital', 'taxa_juros', 'data_inicio', 'data_vencimento'
        )
        total_pagamentos = Pagamento.objects.filter(emprestimo__cliente=cliente).aggregate(total=Sum('valor_pago'))['total'] or Decimal(0)
        valor_devido = sum(contrato['valor_total'] for contrato in contratos) - total_pagamentos
        
        data = {
            'success': True,
            'cliente': {
                'id': cliente.cpf,
                'nome': cliente.nome,
                'apelido': cliente.apelido,
                'cpf': cliente.cpf,
                'valor_devido': valor_devido,
                'contratos': list(contratos)
            }
        }
    else:
        print("Cliente não encontrado.")
        logger.warning("Cliente não encontrado.")
        data = {'success': False}
    
    return JsonResponse(data)
@login_required
def editar_cliente(request, cpf):
    cliente = get_object_or_404(Cliente, cpf=cpf)
    if request.method == 'POST':
        form = ClienteForm(request.POST, instance=cliente, user=request.user)  # Passa o usuário ao formulário
        if form.is_valid():
            form.save()
            return redirect('PELFCRED_APP:lista_clientes')
    else:
        form = ClienteForm(instance=cliente, user=request.user)  # Passa o usuário ao formulário
    return render(request, 'editar_cliente.html', {'form': form})


@login_required
def excluir_cliente(request, cpf):
    if request.method == 'POST':
        cliente = get_object_or_404(Cliente, cpf=cpf)
        cliente.delete()
        return JsonResponse({'success': True, 'message': 'Cliente excluído com sucesso.'})
    return JsonResponse({'success': False, 'message': 'Método não permitido.'}, status=405)

@login_required
def detalhes_cliente(request, cpf):
    cliente = get_object_or_404(Cliente, cpf=cpf)
    
    # Obtém o parâmetro de filtro de status da URL
    status_filter = request.GET.get('status', 'ativos')  # Valor padrão: 'ativos'
    
    if status_filter == 'finalizado':
        emprestimos = Emprestimo.objects.filter(cliente=cliente, status='finalizado')
    elif status_filter == 'inadimplentes':
        emprestimos = Emprestimo.objects.filter(cliente=cliente, status='inadimplentes')
    elif status_filter == 'todos':
        emprestimos = Emprestimo.objects.filter(cliente=cliente)
    else:  # 'ativos'
        emprestimos = Emprestimo.objects.filter(cliente=cliente, status__in=['ativo', 'R', 'NG'])
        
    # Calcula o valor total do empréstimo
    for emprestimo in emprestimos:
        emprestimo.valor_total_calculado = emprestimo.calcular_valor_total()

        # Filtrar apenas os pagamentos feitos após a renovação
        if emprestimo.renovado and emprestimo.data_renovacao:
            emprestimo.total_pago = emprestimo.pagamentos.filter(data_pagamento__gte=emprestimo.data_renovacao).aggregate(Sum('valor_pago'))['valor_pago__sum'] or 0
        else:
            emprestimo.total_pago = emprestimo.pagamentos.aggregate(Sum('valor_pago'))['valor_pago__sum'] or 0

        # Atualiza o saldo devedor
        emprestimo.saldo_devedor_atual = emprestimo.calcular_saldo_devedor()

    return render(request, 'detalhes_cliente.html', {
        'cliente': cliente, 
        'emprestimos': emprestimos,
        'status_filter': status_filter,
    })



@login_required
def lista_clientes(request):
    # Captura os parâmetros de filtro da URL
    status_selecionado = request.GET.get('status', '')
    search_query = request.GET.get('search', '')
    grupo_selecionado = request.GET.get('grupo', '')
    usuario_selecionado = request.GET.get('usuario', '')
    data_inicio = request.GET.get('data_inicio', '')
    data_fim = request.GET.get('data_fim', '')
    dias_semana = request.GET.get('dias_semana', '')
    user_group = request.user.groups.first()


    # Busca os clientes relacionados ao grupo e usuário, se existir
    clientes = Cliente.objects.select_related('grupo', 'usuario').all()
    clientes = Cliente.objects.filter(grupo=user_group)

      # Se o usuário não for superusuário, filtrar apenas os clientes do grupo do usuário
    if not request.user.is_superuser:
        user_group = request.user.groups.first()
        clientes = clientes.filter(grupo=user_group)
    else:
        # Superusuários podem ver todos os clientes, sem limitação de grupo
        clientes = Cliente.objects.all()

    # Filtro por busca de nome, apelido ou CPF
    if search_query:
        clientes = clientes.filter(
            Q(nome__icontains=search_query) | 
            Q(apelido__icontains=search_query) | 
            Q(cpf__icontains=search_query)
        )
        


    # Filtro por grupo
    if grupo_selecionado:
        clientes = clientes.filter(grupo__name=grupo_selecionado)
        
    # Filtro por usuário
    if usuario_selecionado:
        clientes = clientes.filter(usuario__username=usuario_selecionado)
        
    # Filtro por status (ativo/inativo/NV)
    if status_selecionado == 'NV':
        clientes = clientes.filter(status_relatorio='NV')
    elif status_selecionado == 'ativo':
        clientes = clientes.filter(bloqueado=False)
    elif status_selecionado == 'inativo':
        clientes = clientes.filter(bloqueado=True)
        
    # Filtro por dias da semana dos empréstimos
    if dias_semana:
        clientes = clientes.filter(emprestimo__dias_semana__icontains=dias_semana)

 # Filtro por intervalo de datas
    if data_inicio and data_fim:
        data_inicio_parsed = parse_date(data_inicio)
        data_fim_parsed = parse_date(data_fim)
        if data_inicio_parsed and data_fim_parsed:
            clientes = clientes.filter(data_registro__range=[data_inicio_parsed, data_fim_parsed])

    # Ordena os clientes por nome
    clientes = clientes.order_by('nome')

    # Paginação - mostrando 10 clientes por página
    paginator = Paginator(clientes, 10)
    page = request.GET.get('page')

    try:
        clientes = paginator.page(page)
    except PageNotAnInteger:
        clientes = paginator.page(1)
    except EmptyPage:
        clientes = paginator.page(paginator.num_pages)

    # Total de clientes filtrados
    total_clientes = clientes.paginator.count

    # Listagem de grupos e usuários para os filtros
    grupos = Group.objects.all()
    usuarios = User.objects.all()

    # Renderiza o template com os dados
    return render(request, 'lista_clientes.html', {
        'clientes': clientes,
        'grupos': grupos,
        'usuarios': usuarios,
        'grupo_selecionado': grupo_selecionado,
        'usuario_selecionado': usuario_selecionado,
        'status_selecionado': status_selecionado,  # Adiciona o status selecionado no contexto
        'data_inicio': data_inicio,  # Adiciona a data de início no contexto
        'data_fim': data_fim,  # Adiciona a data de fim no contexto
        'total_clientes': total_clientes,
    })

# Função para aplicar os filtros em ambos os exportadores
def aplicar_filtros(request, clientes):
    search_query = request.GET.get('search', '')
    grupo_selecionado = request.GET.get('grupo', '')
    usuario_selecionado = request.GET.get('usuario', '')
    status_selecionado = request.GET.get('status', '')
    data_inicio = request.GET.get('data_inicio', '')
    data_fim = request.GET.get('data_fim', '')
    data_range = request.GET.get('data_range', '')

    if search_query:
        clientes = clientes.filter(
            Q(nome__icontains=search_query) | 
            Q(apelido__icontains=search_query) | 
            Q(cpf__icontains=search_query) | 
            Q(emprestimo__id__icontains=search_query)
        )
    
    if grupo_selecionado:
        clientes = clientes.filter(grupo__name=grupo_selecionado)
    
    if usuario_selecionado:
        clientes = clientes.filter(usuario__username=usuario_selecionado)
    
    if status_selecionado == 'ativo':
        clientes = clientes.filter(bloqueado=False)
    elif status_selecionado == 'inativo':
        clientes = clientes.filter(bloqueado=True)

    if data_inicio:
        data_inicio_dt = datetime.strptime(data_inicio, '%d/%m/%Y')
        clientes = clientes.filter(data_registro__gte=data_inicio_dt)
    
    if data_fim:
        data_fim_dt = datetime.strptime(data_fim, '%d/%m/%Y')
        clientes = clientes.filter(data_registro__lte=data_fim_dt)
        
    if data_range and ' até ' in data_range:
        data_inicio, data_fim = data_range.split(' até ')
        try:
            data_inicio = datetime.strptime(data_inicio, '%d/%m/%Y').date()
            data_fim = datetime.strptime(data_fim, '%d/%m/%Y').date()
            clientes = clientes.filter(data_registro__range=[data_inicio, data_fim])
        except ValueError:
            pass
    
    return clientes

@login_required
def exportar_pdf(request):
    # Obter os empréstimos filtrados
    emprestimos = filtrar_emprestimos(request)
    
    # Renderiza o template PDF com os dados filtrados
    context = {
        'emprestimos': emprestimos,
    }
    
    template_path = 'emprestimos_export_pdf.html'  # Certifique-se de criar este template
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="emprestimos.pdf"'
    
    template = get_template(template_path)
    html = template.render(context)
    
    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse(f'Erro ao gerar PDF: {pisa_status.err}')
    
    return response


@login_required
def exportar_csv(request):
    # Obter os empréstimos filtrados
    emprestimos = filtrar_emprestimos(request)
    
    # Gera o CSV com base nos filtros aplicados
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="emprestimos.csv"'
    
    writer = csv.writer(response)
    
    # Cabeçalho do CSV
    writer.writerow(['Cliente', 'Apelido', 'CPF', 'Contrato ID', 'Capital', 'Taxa de Juros', 'Juros', 'Total', 'Saldo Devedor', 'Data de Início', 'Data de Vencimento', 'Status'])
    
    # Loop pelos empréstimos filtrados
    for emprestimo in emprestimos:
        writer.writerow([
            emprestimo.cliente.nome,
            emprestimo.cliente.apelido,
            emprestimo.cliente.cpf,
            emprestimo.id,
            float(emprestimo.capital),
            float(emprestimo.taxa_juros),
            float(emprestimo.calcular_valor_juros()),
            float(emprestimo.valor_total),
            float(emprestimo.saldo_devedor),
            emprestimo.data_inicio.strftime("%d/%m/%Y"),
            emprestimo.data_vencimento.strftime("%d/%m/%Y"),
            emprestimo.get_status_display()
        ])
    
    return response

def filtrar_emprestimos(request):
    user = request.user
    user_group = user.groups.first()  # Grupo do usuário logado
    
    # Inicializar o queryset de empréstimos
    emprestimos = Emprestimo.objects.all()
    
    # Se o usuário não for admin, filtrar por grupo e usuário
    if not user.is_superuser:
        emprestimos = emprestimos.filter(grupo=user_group, usuario=user)
    
    # Filtros de busca e status
    search_query = request.GET.get('search', None)
    grupo_filtrado = request.GET.get('grupo', None)
    usuario_filtrado = request.GET.get('usuario', None)
    status_filtrado = request.GET.get('status', None)
    dias_semana = request.GET.get('dias_semana', None)
    data_registro_inicio = request.GET.get('data_registro_inicio', None)
    data_registro_fim = request.GET.get('data_registro_fim', None)
    data_vencimento_inicio = request.GET.get('data_vencimento_inicio', None)
    data_vencimento_fim = request.GET.get('data_vencimento_fim', None)

    # Aplicar filtros por grupo e usuário se for admin
    if user.is_superuser:
        if grupo_filtrado:
            emprestimos = emprestimos.filter(grupo__name=grupo_filtrado)
        if usuario_filtrado:
            emprestimos = emprestimos.filter(usuario__username=usuario_filtrado)
    
    # Filtro por status
    if status_filtrado:
        if status_filtrado == 'ativos':
            emprestimos = emprestimos.filter(Q(status='ativo') | Q(status='NG') | Q(status='R'), saldo_devedor__gt=0)
        elif status_filtrado == 'finalizados':
            emprestimos = emprestimos.filter(status='finalizado', saldo_devedor=0)
        elif status_filtrado == 'inadimplentes':
            emprestimos = emprestimos.filter(status='inadimplentes')
        elif status_filtrado == 'Renovados':
            emprestimos = emprestimos.filter(status='R', saldo_devedor__gt=0)
        elif status_filtrado == 'Negociados':
            emprestimos = emprestimos.filter(status='NG')
    
    # Filtro por busca
    if search_query:
        emprestimos = emprestimos.filter(
            Q(cliente__nome__icontains=search_query) |
            Q(cliente__apelido__icontains=search_query) |
            Q(cliente__cpf__icontains=search_query) |
            Q(id__icontains=search_query)
        )
    
    # Filtro por dias da semana
    if dias_semana:
        emprestimos = emprestimos.filter(dias_semana__icontains=dias_semana)
    
    # Filtro por datas de registro
    if data_registro_inicio and data_registro_fim:
        emprestimos = emprestimos.filter(data_inicio__range=[data_registro_inicio, data_registro_fim])
    elif data_registro_inicio:
        emprestimos = emprestimos.filter(data_inicio__gte=data_registro_inicio)
    elif data_registro_fim:
        emprestimos = emprestimos.filter(data_inicio__lte=data_registro_fim)
    
    # Filtro por datas de vencimento
    if data_vencimento_inicio and data_vencimento_fim:
        emprestimos = emprestimos.filter(data_vencimento__range=[data_vencimento_inicio, data_vencimento_fim])
    elif data_vencimento_inicio:
        emprestimos = emprestimos.filter(data_vencimento__gte=data_vencimento_inicio)
    elif data_vencimento_fim:
        emprestimos = emprestimos.filter(data_vencimento__lte=data_vencimento_fim)
    
    return emprestimos

@login_required
def home(request):
    # Verifica se o usuário está no grupo 'admin' ou é superusuário
    is_admin = request.user.is_superuser or request.user.groups.filter(name='admin').exists()
    
    return render(request, 'base.html', {'is_admin': is_admin})



@login_required
def cadastrar_cliente(request):
    if request.method == 'POST':
        form = ClienteForm(request.POST, user=request.user)
        if form.is_valid():
            cliente = form.save(commit=False)
            if request.user.is_superuser:
                # Atribui o grupo e o usuário ao cliente, caso seja admin
                cliente.grupo = form.cleaned_data.get('grupo')
                cliente.usuario = form.cleaned_data.get('usuario')
            else:
                # Atribuir grupo e usuário do request
                cliente.grupo = request.user.groups.first()
                cliente.usuario = request.user
            cliente.save()
            
            # Verifica se o cliente tem empréstimos ativos
            tem_emprestimo_ativo = Emprestimo.objects.filter(cliente=cliente, status='ativo').exists()

            # Define o status do relatório
            status_relatorio = 'NV' if not tem_emprestimo_ativo else 'Outro'
            cliente.status_relatorio = status_relatorio

            # Salva o cliente com o status atualizado
            cliente.save()

            messages.success(request, "Cliente cadastrado com sucesso!")
            return redirect('PELFCRED_APP:lista_clientes')
        else:
            messages.error(request, "Por favor, corrija os erros abaixo.")
    else:
        form = ClienteForm(user=request.user)

    return render(request, 'cadastrar_cliente.html', {'form': form})

@login_required
def lista_emprestimos(request):
    user = request.user
    user_group = user.groups.first()  # Grupo do usuário logado

    # Inicializar o queryset de empréstimos
    emprestimos = Emprestimo.objects.all()

    # Se o usuário não for admin, filtrar por grupo e usuário
    if not user.is_superuser:
        emprestimos = emprestimos.filter(grupo=user_group, usuario=user)

    # Filtros de busca e status
    search_query = request.GET.get('search', None)
    grupo_filtrado = request.GET.get('grupo', None)
    usuario_filtrado = request.GET.get('usuario', None)
    status_filtrado = request.GET.get('status', None)
    dias_semana = request.GET.get('dias_semana', None)
    data_registro_inicio = request.GET.get('data_registro_inicio', None)
    data_registro_fim = request.GET.get('data_registro_fim', None)
    data_vencimento_inicio = request.GET.get('data_vencimento_inicio', None)
    data_vencimento_fim = request.GET.get('data_vencimento_fim', None)

    # Aplicar filtros por grupo e usuário se for admin
    if user.is_superuser:
        if grupo_filtrado:
            emprestimos = emprestimos.filter(grupo__name=grupo_filtrado)
        if usuario_filtrado:
            emprestimos = emprestimos.filter(usuario__username=usuario_filtrado)

    # Filtro por status (ativos, finalizados, inadimplentes)
    if status_filtrado:
        if status_filtrado == 'ativos':
            emprestimos = emprestimos.filter(Q(status='ativo') | Q(status='NG') | Q(status='R'), saldo_devedor__gt=0)
        elif status_filtrado == 'finalizados':
            emprestimos = emprestimos.filter(status='finalizado', saldo_devedor=0)
        elif status_filtrado == 'inadimplentes':
            emprestimos = emprestimos.filter(status='inadimplentes')
        elif status_filtrado == 'Renovados':
            emprestimos = emprestimos.filter(status='R', saldo_devedor__gt=0)
        elif status_filtrado == 'Negociados':   
            emprestimos = emprestimos.filter(status='NG')
            
    # Filtro por busca (CPF, Nome, Apelido ou ID do contrato)
    if search_query:
        emprestimos = emprestimos.filter(
            Q(cliente__nome__icontains=search_query) |
            Q(cliente__apelido__icontains=search_query) |
            Q(cliente__cpf__icontains=search_query) |
            Q(id__icontains=search_query)  # Filtro por ID do contrato
        )

    # Filtro por dias da semana
    if dias_semana:
        emprestimos = emprestimos.filter(dias_semana__icontains=dias_semana)

    # Filtro por datas de registro
    if data_registro_inicio and data_registro_fim:
        emprestimos = emprestimos.filter(data_inicio__range=[data_registro_inicio, data_registro_fim])
    elif data_registro_inicio:
        emprestimos = emprestimos.filter(data_inicio__gte=data_registro_inicio)
    elif data_registro_fim:
        emprestimos = emprestimos.filter(data_inicio__lte=data_registro_fim)

    # Filtro por datas de vencimento
    if data_vencimento_inicio and data_vencimento_fim:
        emprestimos = emprestimos.filter(data_vencimento__range=[data_vencimento_inicio, data_vencimento_fim])
    elif data_vencimento_inicio:
        emprestimos = emprestimos.filter(data_vencimento__gte=data_vencimento_inicio)
    elif data_vencimento_fim:
        emprestimos = emprestimos.filter(data_vencimento__lte=data_vencimento_fim)

    # Ordenação com mapeamento
    ordenar_por = request.GET.get('ordenar_por', 'cliente__nome')
    ordenar_por_dict = {
        'nome_asc': 'cliente__nome',
        'nome_desc': '-cliente__nome',
        'contrato_asc': 'id',
        'contrato_desc': '-id',
        'capital_asc': 'capital',
        'capital_desc': '-capital',
        'taxa_juros_asc': 'taxa_juros',
        'taxa_juros_desc': '-taxa_juros',
        'valor_total_asc': 'valor_total',
        'valor_total_desc': '-valor_total',
        'saldo_devedor_asc': 'saldo_devedor',
        'saldo_devedor_desc': '-saldo_devedor',
        'data_inicio_asc': 'data_inicio',
        'data_inicio_desc': '-data_inicio',
        'data_vencimento_asc': 'data_vencimento',
        'data_vencimento_desc': '-data_vencimento',
        'juros_asc': 'juros',
        'juros_desc': '-juros',
        'semana_asc': 'dias_semana',
        'semana_desc': '-dias_semana',
    }

    # Verifica se a chave de ordenação existe no dicionário, caso contrário, ordena por nome do cliente
    if ordenar_por in ordenar_por_dict:
        emprestimos = emprestimos.order_by(ordenar_por_dict[ordenar_por])

    # Paginação
    paginator = Paginator(emprestimos, 10)  # 10 empréstimos por página
    page = request.GET.get('page')
    emprestimos_paginados = paginator.get_page(page)

    # Obtenção de grupos e usuários para os filtros
    grupos = Group.objects.all()
    usuarios = User.objects.all()

    # Preparação do contexto para renderização
    context = {
        'emprestimos': emprestimos_paginados,
        'page_obj': emprestimos_paginados,
        'search_query': search_query,
        'grupos': grupos,
        'usuarios': usuarios,
        'status_filtro': status_filtrado,
        'dias_semana': dias_semana,
        'data_registro_inicio': data_registro_inicio,
        'data_registro_fim': data_registro_fim,
        'data_vencimento_inicio': data_vencimento_inicio,
        'data_vencimento_fim': data_vencimento_fim,
        'ordenar_por': ordenar_por,
    }

    return render(request, 'lista_emprestimos.html', context)


logger = logging.getLogger(__name__)

@login_required
def marcar_inadimplente(request, id_emprestimo):
    logger.info(f"View marcar_inadimplente chamada com id_emprestimo={id_emprestimo}")

    if request.method == 'POST':
        logger.info("Requisição POST recebida com sucesso.")

        try:
            emprestimo = get_object_or_404(Emprestimo, id=id_emprestimo)
            logger.info(f"Empréstimo {id_emprestimo} encontrado: {emprestimo}")

            # Calcular o valor dos juros
            valor_juros = emprestimo.calcular_valor_juros()
            logger.info(f"Valor dos juros calculado: {valor_juros}")

            # Atualizar o saldo devedor subtraindo os juros, sem permitir saldo negativo
            novo_saldo_devedor = emprestimo.saldo_devedor - valor_juros
            if novo_saldo_devedor < Decimal('0.00'):
                valor_juros = emprestimo.saldo_devedor  # Ajustar o valor_juros para não deixar saldo negativo
                emprestimo.saldo_devedor = Decimal('0.00')
            else:
                emprestimo.saldo_devedor = novo_saldo_devedor

            # Atualizar o status do empréstimo para inadimplente
            emprestimo.status = 'inadimplentes'

            # Salvar as alterações no empréstimo
            emprestimo.save()
            logger.info(f"Empréstimo {id_emprestimo} atualizado e salvo como inadimplente.")

            messages.success(request, 'Empréstimo marcado como inadimplente com sucesso. Juros descontados do saldo devedor e registrados na reserva.')
        except Exception as e:
            logger.error(f"Erro ao marcar o empréstimo {id_emprestimo} como inadimplente: {e}")
            messages.error(request, 'Ocorreu um erro ao tentar marcar o empréstimo como inadimplente.')
    else:
        logger.warning("A requisição não foi do tipo POST.")

    return redirect('PELFCRED_APP:detalhes_cliente', cpf=emprestimo.cliente.cpf)




@login_required
def editar_emprestimo(request, id):
    emprestimo = get_object_or_404(Emprestimo, id=id)
    if request.method == 'POST':
        form = EditarEmprestimoForm(request.POST, instance=emprestimo, user=request.user)
        if form.is_valid():
            emprestimo = form.save(commit=False)
            # Recalcular o valor parcelado
            emprestimo.valor_parcelado = emprestimo.valor_total / emprestimo.numero_parcelas
            emprestimo.save()
            messages.success(request, 'Contrato atualizado com sucesso.')
            return redirect('PELFCRED_APP:lista_emprestimos')
        else:
            messages.error(request, f'Erro ao editar o contrato: {form.errors}')
    else:
        form = EditarEmprestimoForm(instance=emprestimo, user=request.user)
    
    return render(request, 'editar_emprestimo.html', {'form': form, 'emprestimo': emprestimo})


@login_required
def cadastrar_emprestimo(request, cpf=None):
    cliente = get_object_or_404(Cliente, cpf=cpf)

    if request.method == 'POST':
        form = EmprestimoForm(request.POST, user=request.user)
        if form.is_valid():
            emprestimo = form.save(commit=False)
            emprestimo.cliente = cliente  # Vincular o cliente ao empréstimo

            if request.user.is_superuser:
                # Se for admin, usamos os valores do formulário
                emprestimo.grupo = form.cleaned_data.get('grupo')
                emprestimo.usuario = form.cleaned_data.get('usuario')
            else:
                # Se não for admin, usamos o grupo e usuário do request
                emprestimo.grupo = request.user.groups.first()
                emprestimo.usuario = request.user

            # Restante do código permanece igual
            emprestimo.capital_inicial = emprestimo.capital

            # Processa os dias da semana selecionados
            dias_semana = form.cleaned_data.get('dias_semana', [])
            emprestimo.dias_semana = ','.join(dias_semana)

            # Captura o número de parcelas corretamente
            emprestimo.numero_parcelas = form.cleaned_data['parcelas']

            # Calcula o valor total (capital + juros)
            emprestimo.valor_total = emprestimo.capital + (emprestimo.capital * emprestimo.taxa_juros / 100)

            # Inicializa o saldo devedor com o valor total
            emprestimo.saldo_devedor = emprestimo.valor_total

            # Atribui o valor parcelado
            emprestimo.valor_parcelado = emprestimo.valor_total / emprestimo.numero_parcelas

            # Salva o empréstimo
            emprestimo.save()

            # Criar um registro de saída com o capital inicial
            Saida.objects.create(
                emprestimo=emprestimo,
                valor=emprestimo.capital_inicial,
                data_hora=timezone.now()
            )

            # Gerar as parcelas com base na frequência
            numero_parcelas = emprestimo.numero_parcelas
            data_inicio = emprestimo.data_inicio
            frequencia = emprestimo.frequencia

            # Dicionário para converter frequência em dias
            dias_frequencia = {
                'diaria': 1,
                'semanal': 7,
                'quinzenal': 15,
                'mensal': 30
            }

            # Cria as parcelas de acordo com a frequência
            for i in range(numero_parcelas):
                data_vencimento = data_inicio + timedelta(days=dias_frequencia[frequencia] * i)
                Parcela.objects.create(
                    emprestimo=emprestimo,
                    data_vencimento=data_vencimento,
                    pago=False  # Inicialmente não pago
                )

            messages.success(request, 'Empréstimo cadastrado com sucesso.')
            logger.info("Redirecionando para lista de empréstimos.")
            return redirect('PELFCRED_APP:detalhes_cliente', cpf=cliente.cpf)
        else:
            logger.error(f"Erro ao cadastrar o empréstimo: {form.errors}")
            messages.error(request, f'Erro ao cadastrar o empréstimo: {form.errors}')
    else:
        form = EmprestimoForm(initial={'cliente': cliente}, user=request.user)
        logger.info("Formulário de empréstimo inicializado.")

    return render(request, 'cadastrar_emprestimo.html', {'form': form, 'cliente': cliente})




@login_required 
def renovar_emprestimo(request, id):
    emprestimo = get_object_or_404(Emprestimo, id=id)

    # Verificar se o status do empréstimo permite renovação
    if emprestimo.status not in ['ativo', 'NG']:
        messages.error(request, 'Apenas empréstimos ativos ou negociados podem ser renovados.')
        return redirect('PELFCRED_APP:detalhes_cliente', cpf=emprestimo.cliente.cpf)

    if request.method == 'POST':
        # Capturar os valores de entrada
        nova_taxa_juros_input = request.POST.get('nova_taxa_juros', '').strip()
        capital_adicional_input = request.POST.get('capital_adicional', '').strip()
        numero_parcelas_input = request.POST.get('parcelas', '').strip()
        frequencia = request.POST.get('frequencia')

        # Processar os dias da semana selecionados
        dias_semana = request.POST.getlist('dias_semana')
        emprestimo.dias_semana = ','.join(dias_semana)

        # Validar e converter os valores
        try:
            nova_taxa_juros = Decimal(nova_taxa_juros_input) if nova_taxa_juros_input else emprestimo.taxa_juros
            capital_adicional = Decimal(capital_adicional_input) if capital_adicional_input else Decimal('0')
            numero_parcelas = int(numero_parcelas_input) if numero_parcelas_input else emprestimo.numero_parcelas
        except (InvalidOperation, ValueError):
            messages.error(request, 'Valores inválidos fornecidos. Por favor, verifique os dados inseridos.')
            return redirect('PELFCRED_APP:renovar_emprestimo', id=emprestimo.id)

        try:
            with transaction.atomic():
                # Atualizar campos do empréstimo
                emprestimo.numero_parcelas = numero_parcelas
                emprestimo.frequencia = frequencia
                emprestimo.taxa_juros = nova_taxa_juros  # Atualizar a taxa de juros

                # Chamar o método renovar
                renovou = emprestimo.renovar(
                    nova_taxa_juros=nova_taxa_juros,
                    capital_adicional=capital_adicional,
                )
            if renovou:
                logger.info(f"Contrato {emprestimo.id} renovado com sucesso por {request.user.username}.")
                messages.success(request, 'Contrato renovado com sucesso!')
                return redirect('PELFCRED_APP:totais')  # Redirecionar para a tela Totais
            else:
                messages.error(request, 'Não foi possível renovar o contrato.')
                return redirect('PELFCRED_APP:totais')  # Redirecionar para a tela Totais
        except Exception as e:
            messages.error(request, f'Erro ao renovar o contrato: {str(e)}')
            return redirect('PELFCRED_APP:renovar_emprestimo', id=emprestimo.id)

    saldo_devedor = emprestimo.calcular_saldo_devedor()

    return render(request, 'renovar_emprestimo.html', {
        'emprestimo': emprestimo,
        'saldo_devedor': saldo_devedor,
        'juros_atual': emprestimo.taxa_juros,
        'capital_atual': emprestimo.capital,
        'dias_semana': emprestimo.dias_semana.split(',') if emprestimo.dias_semana else [],
    })

    
def excluir_emprestimo(request, id):
    emprestimo = get_object_or_404(Emprestimo, id=id)
    if request.method == 'POST':
        emprestimo.delete()
        return redirect('PELFCRED_APP:lista_emprestimos')
    return render(request, 'confirmar_exclusao_emprestimo.html', {'emprestimo': emprestimo})

@login_required
def historico_pagamentos(request, id_emprestimo):
    emprestimo = get_object_or_404(Emprestimo, id=id_emprestimo)
    pagamentos = emprestimo.pagamentos.all()  # Pega todos os pagamentos, independentemente da renovação

    return render(request, 'historico_pagamentos.html', {'emprestimo': emprestimo, 'pagamentos': pagamentos})


@login_required
def analisar_pagamentos(request):
    # Captura de parâmetros de filtro
    grupo_id = request.GET.get('grupo', None)
    usuario_id = request.GET.get('usuario', None)
    search_query = request.GET.get('search', '')
    data_inicio = request.GET.get('data_inicio', '')
    data_fim = request.GET.get('data_fim', '')
    saldo_negativo = request.GET.get('saldo_negativo', '')

    # Inicialização do queryset de pagamentos
    if request.user.is_superuser:
        pagamentos = Pagamento.objects.all()
    else:
        pagamentos = Pagamento.objects.filter(usuario=request.user)

    # Aplicação dos filtros
    if search_query:
        pagamentos = pagamentos.filter(
            Q(emprestimo__cliente__cpf__icontains=search_query) |
            Q(emprestimo__cliente__nome__icontains=search_query) |
            Q(emprestimo__cliente__apelido__icontains=search_query)
        )

    if grupo_id:
        pagamentos = pagamentos.filter(emprestimo__grupo_id=grupo_id)

    if usuario_id:
        pagamentos = pagamentos.filter(emprestimo__usuario_id=usuario_id)

    if data_inicio and data_fim:
        pagamentos = pagamentos.filter(data_pagamento__range=[data_inicio, data_fim])

    if saldo_negativo == '1':
        pagamentos = pagamentos.filter(emprestimo__saldo_devedor__lt=0)

    # Calcular os totais após aplicar os filtros
    total_pix = pagamentos.filter(tipo_pagamento='PIX').aggregate(Sum('valor_pago'))['valor_pago__sum'] or 0
    total_dinheiro = pagamentos.filter(tipo_pagamento='DINHEIRO').aggregate(Sum('valor_pago'))['valor_pago__sum'] or 0
    total_pagamentos = pagamentos.aggregate(total=Sum('valor_pago'))['total'] or 0
    
    # Calcular os totais de pagamentos usando o conjunto base de pagamentos
    total_pix = pagamentos.aggregate(
        total_pix=Sum('valor_pago', filter=Q(tipo_pagamento__iexact='PIX'))
    )['total_pix'] or Decimal(0)

    total_dinheiro = pagamentos.aggregate(
        total_dinheiro=Sum('valor_pago', filter=Q(tipo_pagamento__iexact='DINHEIRO'))
    )['total_dinheiro'] or Decimal(0)


    # Paginação
    paginator = Paginator(pagamentos, 10)
    page = request.GET.get('page')

    try:
        pagamentos = paginator.page(page)
    except PageNotAnInteger:
        pagamentos = paginator.page(1)
    except EmptyPage:
        pagamentos = paginator.page(paginator.num_pages)

    context = {
        'pagamentos': pagamentos,
        'grupos': Group.objects.all(),
        'usuarios': User.objects.all(),
        'total_pagamentos': total_pagamentos,
        'total_pix': total_pix,
        'total_dinheiro': total_dinheiro,
    }

    return render(request, 'analisar_pagamentos.html', context)
@login_required
def rejeitar_pagamento(request, pagamento_id):
    if request.method == 'POST':
        try:
            # Buscar o pagamento a ser rejeitado
            pagamento = get_object_or_404(Pagamento, id=pagamento_id)
            emprestimo = pagamento.emprestimo

            # Verificar se o pagamento foi feito hoje
            hoje = timezone.now().date()
            if pagamento.data_pagamento.date() != hoje:
                return JsonResponse({
                    'success': False,
                    'message': 'Você só pode rejeitar pagamentos feitos no dia de hoje.'
                }, status=400)

            # Deleta o pagamento rejeitado
            pagamento.delete()

            # Converter a data/hora do pagamento para o fuso horário local
            data_pagamento_local = localtime(pagamento.data_pagamento)

            # Remover o registro de BonusJuros associado, se houver
            bonus_juros = BonusJuros.objects.filter(
                emprestimo=emprestimo,
                data__date=data_pagamento_local.date()
            ).first()
            if bonus_juros:
                bonus_juros.delete()
                logger.info(f"BonusJuros excluído para o empréstimo {emprestimo.id} na data {data_pagamento_local.date()}.")
            else:
                logger.warning(f"Nenhum BonusJuros encontrado para o empréstimo {emprestimo.id} na data {data_pagamento_local.date()}.")

            # Remover o registro de JurosRecebido associado, se houver
            juros_recebido = JurosRecebido.objects.filter(
                emprestimo=emprestimo,
                data_hora__date=data_pagamento_local.date()
            ).first()
            if juros_recebido:
                juros_recebido.delete()
                logger.info(f"JurosRecebido excluído para o empréstimo {emprestimo.id} na data {data_pagamento_local.date()}.")
            else:
                logger.warning(f"Nenhum JurosRecebido encontrado para o empréstimo {emprestimo.id} na data {data_pagamento_local.date()}.")

            # Recalcular o total pago e o saldo devedor
            total_pago = emprestimo.pagamentos.aggregate(Sum('valor_pago'))['valor_pago__sum'] or Decimal('0.00')
            emprestimo.saldo_devedor = emprestimo.valor_total - total_pago

            # Recalcular o total de juros recebidos após a rejeição
            total_investido = emprestimo.capital_inicial + emprestimo.capital_adicional_total
            emprestimo.total_juros_recebidos = max(Decimal('0.00'), total_pago - total_investido)

            # Se o empréstimo estava finalizado, verificar se deve reabrir
            if emprestimo.status == 'finalizado':
                emprestimo.status = emprestimo.status_anterior or 'ativo'
                emprestimo.status_anterior = None
                emprestimo.data_finalizacao = None

            # Salvar as alterações no empréstimo
            emprestimo.save()

            # Retornar resposta de sucesso
            return JsonResponse({'success': True, 'message': 'Pagamento rejeitado com sucesso.'})

        except Exception as e:
            logger.error(f"Erro ao rejeitar pagamento: {e}")
            return JsonResponse({'success': False, 'message': 'Erro ao rejeitar o pagamento.'}, status=500)

    return JsonResponse({'success': False, 'message': 'Método não permitido.'}, status=405)





@login_required
def importar_comprovante_pix(request):
    if request.method == 'POST':
        form = ComprovantePIXForm(request.POST, request.FILES)
        if form.is_valid():
            comprovante_pix = form.save(commit=False)
            comprovante_pix.usuario = request.user
            comprovante_pix.save()

            messages.success(request, 'Comprovante PIX importado com sucesso!')
            return redirect('PELFCRED_APP:analisar_pagamentos')
    else:
        form = ComprovantePIXForm()

    return render(request, 'importar_comprovante_pix.html', {'form': form})

@login_required
def atualizar_pagamento(request, pagamento_id):
    pagamento = get_object_or_404(Pagamento, id=pagamento_id)
    if request.method == 'POST':
        novo_valor_pago = request.POST.get('novo_valor_pago')
        
    if novo_valor_pago:
        pagamento.valor_pago = Decimal(novo_valor_pago)
        pagamento.save()
        messages.success(request, 'Valor do pagamento atualizado com sucesso!')
        
        # Recalcular o saldo devedor do contrato
        pagamento.emprestimo.saldo_devedor = pagamento.emprestimo.calcular_juros() - pagamento.valor_pago
        pagamento.emprestimo.save()

        return redirect('PELFCRED_APP:analisar_pagamentos')

@login_required
def registrar_pagamento(request, id_emprestimo=None):
    emprestimo = get_object_or_404(Emprestimo, id=id_emprestimo)

    # Impedir pagamentos em contratos finalizados
    if emprestimo.status == 'finalizado':
        messages.error(request, 'Não é possível registrar pagamentos em contratos finalizados.')
        return redirect('PELFCRED_APP:detalhes_cliente', cpf=emprestimo.cliente.cpf)

    # Somar os pagamentos feitos até o momento
    valor_pago_total = emprestimo.pagamentos.aggregate(Sum('valor_pago'))['valor_pago__sum'] or Decimal(0)
    saldo_devedor = emprestimo.calcular_saldo_devedor()

    if request.method == 'POST':
        valor_pago = Decimal(request.POST.get('valor_pago', 0))
        comprovante = request.FILES.get('comprovante')
        tipo_pagamento = request.POST.get('tipo_pagamento')

        # Certifique-se de que o valor pago é maior que 0
        if valor_pago > 0:
            # Registrar o pagamento
            pagamento = Pagamento.objects.create(
                emprestimo=emprestimo,
                data_pagamento=timezone.now(),
                valor_pago=valor_pago,
                tipo_pagamento=tipo_pagamento.upper(),
                cpf_pagador=emprestimo.cliente.cpf,
                nome_pagador=emprestimo.cliente.nome,
                comprovante_pix=comprovante,
                usuario=request.user
            )

            # Atualizar o total pago e o saldo devedor
            valor_pago_total += valor_pago
            saldo_devedor -= valor_pago

            # Se o pagamento exceder o saldo devedor, calcular o bônus de juros
            if saldo_devedor < 0:
                bonus_juros = abs(saldo_devedor)
                saldo_devedor = Decimal('0.00')

                # Registrar o bônus de juros usando a data e hora exatas do pagamento
                BonusJuros.objects.create(
                    emprestimo=emprestimo,
                    valor=bonus_juros,
                    data=pagamento.data_pagamento  # Usar a data e hora completas
                )

            else:
                bonus_juros = Decimal('0.00')

            # Atualizar o saldo devedor do empréstimo
            emprestimo.saldo_devedor = saldo_devedor

            # Atualizar o total de juros recebidos
            total_investido = emprestimo.capital_inicial + emprestimo.capital_adicional_total
            juros_recebido = max(Decimal('0.00'), valor_pago_total - total_investido)
            emprestimo.total_juros_recebidos = juros_recebido

            # Se o saldo devedor for zero, finalizar o contrato
            if saldo_devedor == Decimal('0.00'):
                emprestimo.status_anterior = emprestimo.status
                emprestimo.status = 'finalizado'
                emprestimo.data_finalizacao = timezone.now()

                # Registrar o JurosRecebido usando a data e hora exatas do pagamento
                JurosRecebido.objects.create(
                    emprestimo=emprestimo,
                    valor=juros_recebido,
                    data_hora=pagamento.data_pagamento  # Usar a data e hora completas
                )

                # Atualizar o status_relatorio do cliente para 'AC'
                emprestimo.cliente.status_relatorio = 'AC'
                emprestimo.cliente.save()

            # **Salvar o empréstimo após atualizar os campos**
            emprestimo.save()

            messages.success(request, 'Pagamento registrado com sucesso!')
            return redirect('PELFCRED_APP:detalhes_cliente', cpf=emprestimo.cliente.cpf)
        else:
            messages.error(request, 'Erro ao registrar pagamento. O valor deve ser maior que zero.')

    return render(request, 'registrar_pagamento.html', {
        'emprestimo': emprestimo,
        'valor_pago_total': valor_pago_total,
        'saldo_devedor': saldo_devedor,
    })


    
@login_required
def finalizar_contrato(request, id_emprestimo):
    emprestimo = get_object_or_404(Emprestimo, id=id_emprestimo)

    # Acessando o total pago usando o método dinamicamente
    total_pago = emprestimo.total_pago()

    # Verificar se o total pago cobre o valor total do empréstimo
    if total_pago < emprestimo.valor_total:
        messages.error(request, "O contrato não pode ser finalizado. O valor total ainda não foi pago.")
        return redirect('PELFCRED_APP:detalhes_cliente', cpf=emprestimo.cliente.cpf)


    # Calcular os juros recebidos
    juros_recebido = max(0, total_pago - emprestimo.capital_inicial + emprestimo.capital_adicional)
    
    # Atualizar o campo de juros recebidos
    emprestimo.total_juros_recebidos = juros_recebido
    emprestimo.status = 'finalizado'
    emprestimo.save()

    messages.success(request, f"Contrato finalizado com sucesso. Juros recebidos: R$ {juros_recebido:.2f}.")
    return redirect('PELFCRED_APP:detalhes_cliente', cpf=emprestimo.cliente.cpf)


logger = logging.getLogger(__name__)


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, 'Login realizado com sucesso!')
            return redirect('PELFCRED_APP:home')
        else:
            messages.error(request, 'Usuário ou senha inválidos.')
    return render(request, 'PELFCRED_APP/login.html')
@login_required
def totais(request):
    logger.info("Entrando na view 'totais'.")
    # Obtenção dos parâmetros de filtro
    grupo_filtrado = request.GET.get('grupo', '')
    usuario_filtrado = request.GET.get('usuario', '')
    data_inicio = request.GET.get('data_inicio', '')
    data_fim = request.GET.get('data_fim', '')
    status_filtro = request.GET.get('status', 'NV')

    # Obtenção do usuário atual e seu grupo
    user = request.user
    grupo = user.groups.first()

    # Define se o usuário é administrador
    admin_view = user.is_superuser or user.groups.filter(name='admin').exists()

    # Validação de datas
    try:
        data_inicio_datetime = None
        data_fim_datetime = None

        if data_inicio:
            data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
            data_inicio_datetime = datetime.combine(data_inicio, datetime.min.time())
        if data_fim:
            data_fim = datetime.strptime(data_fim, '%Y-%m-%d').date()
            data_fim_datetime = datetime.combine(data_fim, datetime.max.time())

        if data_inicio and data_fim and data_fim < data_inicio:
            messages.error(request, 'A data final não pode ser anterior à data de início.')
            data_inicio, data_fim = None, None
            data_inicio_datetime, data_fim_datetime = None, None

    except ValueError:
        messages.error(request, 'Formato de data inválido. Use o formato AAAA-MM-DD.')
        data_inicio, data_fim = None, None
        data_inicio_datetime, data_fim_datetime = None, None
        logger.debug(f"Data início: {data_inicio_datetime}, Data fim: {data_fim_datetime}")

    # Inicializa as queries
    clientes = Cliente.objects.all()
    emprestimos = Emprestimo.objects.all()
    pagamentos = Pagamento.objects.all()

    # Aplicar filtros de visualização (grupo, usuário)
    if not admin_view:
        clientes = clientes.filter(grupo=grupo, usuario=user)
        emprestimos = emprestimos.filter(cliente__grupo=grupo, cliente__usuario=user)
        pagamentos = pagamentos.filter(emprestimo__cliente__grupo=grupo, emprestimo__cliente__usuario=user)
    else:
        if grupo_filtrado:
            clientes = clientes.filter(grupo__name=grupo_filtrado)
            emprestimos = emprestimos.filter(cliente__grupo__name=grupo_filtrado)
            pagamentos = pagamentos.filter(emprestimo__cliente__grupo__name=grupo_filtrado)
        if usuario_filtrado:
            clientes = clientes.filter(usuario__username=usuario_filtrado)
            emprestimos = emprestimos.filter(cliente__usuario__username=usuario_filtrado)
            pagamentos = pagamentos.filter(emprestimo__cliente__usuario__username=usuario_filtrado)

    # Inicializar 'total_capital' com zero
    total_capital = Decimal('0.00')

    # Aplicação dos filtros de data
    if data_inicio_datetime and data_fim_datetime:
        clientes = clientes.filter(data_registro__range=[data_inicio_datetime, data_fim_datetime])
        emprestimos = emprestimos.filter(
            Q(data_inicio__range=[data_inicio_datetime, data_fim_datetime]) |
            Q(data_renovacao__range=[data_inicio_datetime, data_fim_datetime])
        )
        pagamentos = pagamentos.filter(data_pagamento__range=[data_inicio_datetime, data_fim_datetime])
    elif data_inicio_datetime:
        clientes = clientes.filter(data_registro__gte=data_inicio_datetime)
        emprestimos = emprestimos.filter(
            Q(data_inicio__gte=data_inicio_datetime) |
            Q(data_renovacao__gte=data_inicio_datetime)
        )
        pagamentos = pagamentos.filter(data_pagamento__gte=data_inicio_datetime)
    elif data_fim_datetime:
        clientes = clientes.filter(data_registro__lte=data_fim_datetime)
        emprestimos = emprestimos.filter(
            Q(data_inicio__lte=data_fim_datetime) |
            Q(data_renovacao__lte=data_fim_datetime)
        )
        pagamentos = pagamentos.filter(data_pagamento__lte=data_fim_datetime)
        
    # Calcular o total de juros recebidos
    if data_inicio_datetime and data_fim_datetime:
        total_juros_recebidos = JurosRecebido.objects.filter(
            data_hora__range=[data_inicio_datetime, data_fim_datetime],
            emprestimo__in=emprestimos
        ).aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
    else:
        total_juros_recebidos = JurosRecebido.objects.filter(
            emprestimo__in=emprestimos
        ).aggregate(total=Sum('valor'))['total'] or Decimal('0.00')

    # Calcular o total de bônus de juros
    if data_inicio_datetime and data_fim_datetime:
        total_bonus_juros = BonusJuros.objects.filter(
            data__range=[data_inicio_datetime, data_fim_datetime],
            emprestimo__in=emprestimos
        ).aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
    else:
        total_bonus_juros = BonusJuros.objects.filter(
            emprestimo__in=emprestimos
        ).aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
    
    # Aplicação dos filtros por data de status e pagamentos
    if data_inicio and data_fim:
        emprestimos = emprestimos.filter(Q(data_inicio__gte=data_inicio) & Q(data_vencimento__lte=data_fim))
        pagamentos = pagamentos.filter(Q(data_pagamento__date__range=[data_inicio, data_fim]))

    # Filtrar clientes pelo status do relatório
    if status_filtro:
        clientes = clientes.filter(status_relatorio=status_filtro)

    # Atualizar os conjuntos de dados base após os filtros de data
    clientes_base = clientes
    emprestimos_base = emprestimos
    pagamentos_base = pagamentos

    # Obter todos os empréstimos relevantes para o cálculo de total_investido
    emprestimos_todos = emprestimos_base.filter(status__in=['ativo', 'R', 'NG', 'AC', 'inadimplentes', 'finalizado'])

    # Anotar o capital total (capital_inicial + capital_adicional_total)
    emprestimos_todos = emprestimos_todos.annotate(
        capital_total=ExpressionWrapper(
            F('capital_inicial') + F('capital_adicional_total'),
            output_field=DecimalField()
        )
    )


    # Obter os registros de BonusJuros dentro do intervalo de datas filtrado
    bonus_juros_queryset = BonusJuros.objects.all()

    # Aplicar filtros de data ao queryset de BonusJuros
    if data_inicio_datetime and data_fim_datetime:
        bonus_juros_queryset = bonus_juros_queryset.filter(data__range=[data_inicio_datetime, data_fim_datetime])
    elif data_inicio_datetime:
        bonus_juros_queryset = bonus_juros_queryset.filter(data__gte=data_inicio_datetime)
    elif data_fim_datetime:
        bonus_juros_queryset = bonus_juros_queryset.filter(data__lte=data_fim_datetime)

    # Aplicar filtros de grupo e usuário ao queryset de BonusJuros
    if not admin_view:
        bonus_juros_queryset = bonus_juros_queryset.filter(emprestimo__grupo=grupo, emprestimo__usuario=user)
    else:
        if grupo_filtrado:
            bonus_juros_queryset = bonus_juros_queryset.filter(emprestimo__grupo__name=grupo_filtrado)
        if usuario_filtrado:
            bonus_juros_queryset = bonus_juros_queryset.filter(emprestimo__usuario__username=usuario_filtrado)

    # Calcular o total de bônus de juros com base nos filtros aplicados
    total_bonus_juros = bonus_juros_queryset.aggregate(total=Sum('valor'))['total'] or Decimal('0.00')

    # Filtrar clientes e empréstimos para exibição na tabela
    clientes = clientes.filter(
        Q(status_relatorio__in=['NV', 'R', 'NG', 'AC']) |
        Q(emprestimo__status__in=['R', 'NG', 'inadimplentes', 'finalizado', 'ativo'])
    ).distinct()

    emprestimos = emprestimos.filter(
        status__in=['R', 'NG', 'inadimplentes', 'finalizado', 'ativo']
    )

    # Anotar total_capital e lucro nos empréstimos
    if data_inicio_datetime and data_fim_datetime:
        emprestimos = emprestimos.annotate(
            total_capital=Sum(
                'saidas__valor',
                filter=Q(saidas__data_hora__range=(data_inicio_datetime, data_fim_datetime))
            ),
            lucro=Sum(
                'jurosrecebidos__valor',
                filter=Q(jurosrecebidos__data_hora__range=(data_inicio_datetime, data_fim_datetime))
            )
        )
    else:
        emprestimos = emprestimos.annotate(
            total_capital=Sum('saidas__valor'),
            lucro=Sum('jurosrecebidos__valor')
        )

    # Calcular o total de juros recebidos
    total_juros_recebidos = emprestimos.aggregate(
        total=Sum('jurosrecebidos__valor')
    )['total'] or Decimal('0.00')

    # Atualizar os pagamentos com base nos empréstimos filtrados para exibição
    pagamentos = pagamentos.filter(emprestimo__in=emprestimos)

    # Calcular os totais de pagamentos usando o conjunto base de pagamentos
    total_pix = pagamentos_base.aggregate(
        total_pix=Sum('valor_pago', filter=Q(tipo_pagamento__iexact='PIX'))
    )['total_pix'] or Decimal(0)

    total_dinheiro = pagamentos_base.aggregate(
        total_dinheiro=Sum('valor_pago', filter=Q(tipo_pagamento__iexact='DINHEIRO'))
    )['total_dinheiro'] or Decimal(0)

    # Calcular o total geral de pagamentos
    total_pagamentos = pagamentos_base.aggregate(
        total=Sum('valor_pago')
    )['total'] or Decimal(0)

    # Contabilização dos totais usando os conjuntos de dados base
    total_nv = clientes_base.filter(status_relatorio='NV').count()
    total_nvc = emprestimos_base.filter(status='ativo').count()
    total_ng = emprestimos_base.filter(status='NG').count()
    total_r = emprestimos_base.filter(status='R').count()
    total_ac = emprestimos_base.filter(status='finalizado').count()

    # Calcular inadimplentes usando o conjunto base de empréstimos
    total_inadimplentes = emprestimos_base.filter(status='inadimplentes').count()

    total_amarelo = emprestimos_base.filter(
        Q(data_vencimento__lt=timezone.now().date() - timedelta(days=29)) &
        Q(data_vencimento__gte=timezone.now().date() - timedelta(days=59))
    ).count()

    total_vermelho = emprestimos_base.filter(
        Q(data_vencimento__lt=timezone.now().date() - timedelta(days=59))
    ).count()

    # Cálculo dos totais financeiros
    total_investido = emprestimos_todos.aggregate(
        total=Sum('capital_total')
    )['total'] or Decimal(0)

    # Calcular total de saídas (capital) dentro do intervalo de datas
    if data_inicio_datetime and data_fim_datetime:
        saidas = Saida.objects.filter(
            data_hora__range=[data_inicio_datetime, data_fim_datetime]
        )
    elif data_inicio_datetime:
        saidas = Saida.objects.filter(
            data_hora__gte=data_inicio_datetime
        )
    elif data_fim_datetime:
        saidas = Saida.objects.filter(
            data_hora__lte=data_fim_datetime
        )
    else:
        saidas = Saida.objects.all()


    # Aplicar filtros de grupo e usuário nas saídas
    if not admin_view:
        saidas = saidas.filter(emprestimo__grupo=grupo, emprestimo__usuario=user)
    else:
        if grupo_filtrado:
            saidas = saidas.filter(emprestimo__grupo__name=grupo_filtrado)
        if usuario_filtrado:
            saidas = saidas.filter(emprestimo__usuario__username=usuario_filtrado)

    # Calcular total_capital a partir das saídas
    total_capital = saidas.aggregate(total=Sum('valor'))['total'] or Decimal('0.00')

    totais_financeiros = {
        'total_capital': total_capital,
        'total_saldo_devedor': emprestimos_base.aggregate(total=Sum('saldo_devedor'))['total'] or Decimal(0),
    }

    # Obter os empréstimos inadimplentes e anotar o valor dos juros
    emprestimos_inadimplentes = emprestimos.filter(status='inadimplentes').annotate(
        valor_juros=ExpressionWrapper(
            F('capital') * F('taxa_juros') / 100,
            output_field=DecimalField(max_digits=10, decimal_places=2)
        )
    )

    # Obter o valor total dos inadimplentes
    total_inadimplentes_valor = emprestimos_inadimplentes.aggregate(
        total=Sum('saldo_devedor')
    )['total']
    if total_inadimplentes_valor is None:
        total_inadimplentes_valor = Decimal('0.00')

    

    # Cálculo do total geral
    total_geral = {
        'emprestimos_inadimplentes': emprestimos_inadimplentes,
        'total_clientes': clientes_base.count(),
        'total_inadimplentes_valor': total_inadimplentes_valor,
        'total_juros_recebidos': total_juros_recebidos,
        'total_emprestimos': emprestimos_base.count(),
        'total_investido': total_investido,
        'total_juros_recebidos': total_juros_recebidos,
    }

    # Processar o formulário de desconto
    if request.method == 'POST' and 'valor_desconto' in request.POST:
        valor_desconto = request.POST.get('valor_desconto')
        try:
            valor_desconto = Decimal(valor_desconto)
            if valor_desconto > 0:
                # Salvar o desconto no banco de dados com a data atual
                DescontoJuros.objects.create(
                    valor=valor_desconto,
                    data=timezone.now(),
                    usuario=request.user,
                    data_inicio=data_inicio_datetime,
                    data_fim=data_fim_datetime,
                )
                messages.success(request, 'Desconto aplicado com sucesso.')
            else:
                messages.error(request, 'O valor do desconto deve ser positivo.')
        except (InvalidOperation, TypeError):
            messages.error(request, 'Insira um valor numérico válido para o desconto.')

    # Obter o histórico de descontos aplicados dentro do intervalo de datas filtrado
    descontos = DescontoJuros.objects.all().order_by('-data')

    if data_inicio_datetime and data_fim_datetime:
        descontos = descontos.filter(data__range=[data_inicio_datetime, data_fim_datetime])
    elif data_inicio_datetime:
        descontos = descontos.filter(data__gte=data_inicio_datetime)
    elif data_fim_datetime:
        descontos = descontos.filter(data__lte=data_fim_datetime)

    # Calcular o total de descontos aplicados
    total_descontos = descontos.aggregate(total=Sum('valor'))['total'] or Decimal('0.00')

    # Processar o formulário de desconto
    if request.method == 'POST' and 'valor_desconto' in request.POST:
        valor_desconto = request.POST.get('valor_desconto')
        try:
            valor_desconto = Decimal(valor_desconto)
            if valor_desconto > 0:
                # Salvar o desconto no banco de dados com a data atual
                DescontoJuros.objects.create(
                    valor=valor_desconto,
                    data=timezone.now(),
                    usuario=request.user,
                    data_inicio=data_inicio_datetime,
                    data_fim=data_fim_datetime,
                )
                messages.success(request, 'Desconto aplicado com sucesso.')
                # Recalcular 'descontos' e 'total_descontos' após adicionar o novo desconto
                descontos = DescontoJuros.objects.all().order_by('-data')
                if data_inicio_datetime and data_fim_datetime:
                    descontos = descontos.filter(data__range=[data_inicio_datetime, data_fim_datetime])
                elif data_inicio_datetime:
                    descontos = descontos.filter(data__gte=data_inicio_datetime)
                elif data_fim_datetime:
                    descontos = descontos.filter(data__lte=data_fim_datetime)
                total_descontos = descontos.aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
            else:
                messages.error(request, 'O valor do desconto deve ser positivo.')
        except (InvalidOperation, TypeError):
            messages.error(request, 'Insira um valor numérico válido para o desconto.')

    # Update total_juros_recebidos after applying total_descontos
    total_juros_recebidos = total_juros_recebidos - total_descontos
    
    # After calculating total_descontos
    logger.debug(f"Total descontos após aplicação: {total_descontos}")


    # Contexto para o template
    contexto = {
        'emprestimos_inadimplentes': emprestimos_inadimplentes,
        'total_bonus_juros': total_bonus_juros,
        'total_inadimplentes_valor': total_inadimplentes_valor,
        'today': now().date(),
        'descontos': descontos,
        'grupo': grupo,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
        'total_juros_recebidos': total_juros_recebidos,
        'clientes': clientes,
        'emprestimos': emprestimos,
        'total_nv': total_nv,
        'total_ng': total_ng,
        'total_r': total_r,
        'total_ac': total_ac,
        'totais_financeiros': totais_financeiros,
        'total_pix': total_pix,
        'total_dinheiro': total_dinheiro,
        'total_inadimplentes': total_inadimplentes,
        'total_amarelo': total_amarelo,
        'total_vermelho': total_vermelho,
        'total_geral': total_geral,
        'grupo_filtrado': grupo_filtrado,
        'usuario_filtrado': usuario_filtrado,
        'grupos': Group.objects.all(),
        'usuarios': User.objects.all(),
        'total_pagamentos': total_pagamentos,
        'admin_view': admin_view,
        'data_hoje': date.today().strftime('%Y-%m-%d'),
        'status_list': ['R', 'NG', 'AC', 'NV', 'ativo'],  # Para uso no template
        'total_nvc': total_nvc,
        'total_descontos': total_descontos
    }
    return render(request, 'totais.html', contexto)


@login_required
def alterar_status_cliente(request, cpf):
    cliente = get_object_or_404(Cliente, cpf=cpf)
    cliente.bloqueado = not cliente.bloqueado  # Alterna o status
    cliente.save()
    
    status = 'ativado' if not cliente.bloqueado else 'desativado'
    messages.success(request, f'O cliente {cliente.nome} foi {status} com sucesso.')
    
    return redirect('PELFCRED_APP:lista_clientes')