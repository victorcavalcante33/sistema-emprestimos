from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Sum, F, ExpressionWrapper, DecimalField
from django.contrib import messages
from django.contrib.auth.models import Group, User
from decimal import Decimal, InvalidOperation
from .models import Emprestimo, Pagamento, Cliente, Parcela
from .forms import EmprestimoForm, ClienteForm, ComprovantePIXForm
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
            return redirect('PELFCRED:lista_emprestimos')

        elif 'cancel' in request.POST:
            # Aqui podemos apagar o empréstimo, se desejado
            emprestimo.delete()  # Apaga o empréstimo se o usuário cancelar
            messages.info(request, 'Edição de parcelas cancelada e empréstimo removido.')
            return redirect('PELFCRED:lista_emprestimos')

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
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            form.save()
            return redirect('PELFCRED:lista_clientes')
    else:
        form = ClienteForm(instance=cliente)
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
        data_inicio_dt = datetime.strptime(data_inicio, '%Y-%m-%d')
        clientes = clientes.filter(data_registro__gte=data_inicio_dt)
    
    if data_fim:
        data_fim_dt = datetime.strptime(data_fim, '%Y-%m-%d')
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
    # Filtros da listagem de clientes
    search_query = request.GET.get('search', None)
    grupo_filtrado = request.GET.get('grupo', None)
    usuario_filtrado = request.GET.get('usuario', None)
    status_filtrado = request.GET.get('status', None)
    data_inicio = request.GET.get('data_inicio', None)
    data_fim = request.GET.get('data_fim', None)

    clientes_query = Cliente.objects.all()
    
    # Pega todos os clientes do grupo do usuário logado, ou todos se for admin
    if request.user.is_superuser:
        clientes_query = Cliente.objects.all()
    else:
        clientes_query = Cliente.objects.filter(grupo=request.user.groups.first())
        
            # Aplica os filtros
    clientes_query = aplicar_filtros(request, clientes_query)
    
    if search_query:
        clientes_query = clientes_query.filter(
            Q(nome__icontains=search_query) | 
            Q(apelido__icontains=search_query) | 
            Q(cpf__icontains=search_query) | 
            Q(emprestimo__id__icontains=search_query)  # Adiciona busca por ID de empréstimo
        )

    if grupo_filtrado:
        clientes_query = clientes_query.filter(grupo__name=grupo_filtrado)

    if usuario_filtrado:
        clientes_query = clientes_query.filter(usuario__username=usuario_filtrado)

    if status_filtrado == 'ativo':
        clientes_query = clientes_query.filter(bloqueado=False)
    elif status_filtrado == 'inativo':
        clientes_query = clientes_query.filter(bloqueado=True)

    if data_inicio and data_fim:
        try:
            data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
            data_fim = datetime.strptime(data_fim, '%Y-%m-%d').date()
            clientes_query = clientes_query.filter(data_registro__range=(data_inicio, data_fim))
        except ValueError:
            messages.error(request, 'Formato de data inválido. Use o formato AAAA-MM-DD.')

    emprestimos_query = Emprestimo.objects.filter(cliente__in=clientes_query)

    # Calcula os totais gerais
    total_a_receber = round(sum(
        emprestimo.capital * (emprestimo.taxa_juros / 100)
        for emprestimo in emprestimos_query
    ), 2)

    total_juros_recebidos = round(sum(
        emprestimo.total_juros_recebidos for emprestimo in emprestimos_query
    ), 2)

    total_geral = {
        'total_clientes': clientes_query.count(),
        'total_investido': round(emprestimos_query.aggregate(Sum('capital'))['capital__sum'] or 0, 2),
        'total_recebido': round(emprestimos_query.aggregate(Sum('valor_total'))['valor_total__sum'] or 0, 2),
        'total_a_receber': total_a_receber,
        'total_juros_recebidos': total_juros_recebidos,
        'total_emprestimos': emprestimos_query.count(),
    }

    # Renderiza o template PDF com os dados filtrados
    context = {
        'total_geral': total_geral,
        'clientes': clientes_query,
    }

    template_path = 'clientes_contratos_pdf.html'  # Este é o template que você forneceu
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="clientes_contratos.pdf"'

    template = get_template(template_path)
    html = template.render(context)

    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse(f'Erro ao gerar PDF: {pisa_status.err}')

    return response

@login_required
def exportar_csv(request):
    # Filtros da listagem de clientes
    search_query = request.GET.get('search', None)
    grupo_filtrado = request.GET.get('grupo', None)
    usuario_filtrado = request.GET.get('usuario', None)
    status_filtrado = request.GET.get('status', None)
    data_inicio = request.GET.get('data_inicio', None)
    data_fim = request.GET.get('data_fim', None)

    clientes_query = Cliente.objects.all()
    
    # Pega todos os clientes do grupo do usuário logado, ou todos se for admin
    if request.user.is_superuser:
        clientes_query = Cliente.objects.all()
    else:
        clientes_query = Cliente.objects.filter(grupo=request.user.groups.first())
        
            # Aplica os filtros usando a função `aplicar_filtros`
    clientes_query = aplicar_filtros(request, clientes_query)

    if search_query:
        clientes_query = clientes_query.filter(
            Q(nome__icontains=search_query) | 
            Q(apelido__icontains=search_query) | 
            Q(cpf__icontains=search_query) | 
            Q(emprestimo__id__icontains=search_query)  # Adiciona busca por ID de empréstimo
        )


    if grupo_filtrado:
        clientes_query = clientes_query.filter(grupo__name=grupo_filtrado)

    if usuario_filtrado:
        clientes_query = clientes_query.filter(usuario__username=usuario_filtrado)

    if status_filtrado == 'ativo':
        clientes_query = clientes_query.filter(bloqueado=False)
    elif status_filtrado == 'inativo':
        clientes_query = clientes_query.filter(bloqueado=True)

    if data_inicio and data_fim:
        try:
            data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
            data_fim = datetime.strptime(data_fim, '%Y-%m-%d').date()
            clientes_query = clientes_query.filter(data_registro__range=(data_inicio, data_fim))
        except ValueError:
            messages.error(request, 'Formato de data inválido. Use o formato AAAA-MM-DD.')

    emprestimos_query = Emprestimo.objects.filter(cliente__in=clientes_query)

    total_a_receber = round(sum(
        emprestimo.capital * (emprestimo.taxa_juros / 100)
        for emprestimo in emprestimos_query
    ), 2)

    total_juros_recebidos = round(sum(
        emprestimo.total_juros_recebidos for emprestimo in emprestimos_query
    ), 2)

    total_geral = {
        'total_clientes': clientes_query.count(),
        'total_investido': round(emprestimos_query.aggregate(Sum('capital'))['capital__sum'] or 0, 2),
        'total_recebido': round(emprestimos_query.aggregate(Sum('valor_total'))['valor_total__sum'] or 0, 2),
        'total_a_receber': total_a_receber,
        'total_juros_recebidos': total_juros_recebidos,
        'total_emprestimos': emprestimos_query.count(),
    }

    # Gera o CSV com base nos filtros aplicados
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="clientes_com_contratos.csv"'

    writer = csv.writer(response)

    # Cabeçalho do CSV
    writer.writerow(['Nome Cliente', 'Apelido', 'CPF', 'Data de Registro', 'Status', 
                     'Contrato ID', 'Capital', 'Taxa de Juros', 'Juros', 'Total', 'Saldo Devedor', 
                     'Data de Início', 'Data de Vencimento', 'Renovado', 'Data de Renovação'])

    # Loop pelos clientes e seus contratos
    for cliente in clientes_query:
        contratos = Emprestimo.objects.filter(cliente=cliente)
        for contrato in contratos:
            writer.writerow([
                cliente.nome,
                cliente.apelido,
                cliente.cpf,
                cliente.data_registro.strftime("%d/%m/%Y"),
                'Ativo' if not cliente.bloqueado else 'Inativo',
                contrato.id,
                contrato.capital,
                contrato.taxa_juros,
                contrato.calcular_valor_juros(),
                contrato.valor_total,
                contrato.saldo_devedor,
                contrato.data_inicio.strftime("%d/%m/%Y"),
                contrato.data_vencimento.strftime("%d/%m/%Y"),
                'Sim' if contrato.renovado else 'Não',
                contrato.data_renovacao.strftime("%d/%m/%Y H:%M") if contrato.renovado else 'N/A'
            ])

    # Adiciona os totais no final do CSV
    writer.writerow([])
    writer.writerow(['Totais Gerais:'])
    writer.writerow(['Total Clientes:', total_geral['total_clientes']])
    writer.writerow(['Total Investido:', total_geral['total_investido']])
    writer.writerow(['Total Recebido:', total_geral['total_recebido']])
    writer.writerow(['Total a Receber:', total_geral['total_a_receber']])
    writer.writerow(['Total Juros Recebidos:', total_geral['total_juros_recebidos']])
    writer.writerow(['Total Contratos:', total_geral['total_emprestimos']])

    return response


@login_required
def home(request):
    # Verifica se o usuário está no grupo 'admin' ou é superusuário
    is_admin = request.user.is_superuser or request.user.groups.filter(name='admin').exists()
    
    return render(request, 'base.html', {'is_admin': is_admin})



@login_required
@user_passes_test(lambda u: u.is_superuser)
def cadastrar_cliente(request):
    if request.method == 'POST':
        form = ClienteForm(request.POST, user=request.user)  # Passa o usuário ao formulário
        if form.is_valid():
            cliente = form.save(commit=False)
            # Atribui o grupo e o usuário ao cliente, caso seja admin
            cliente.grupo = form.cleaned_data.get('grupo')
            cliente.usuario = form.cleaned_data.get('usuario')
            cliente.save()
            
            # Verifica se o cliente tem empréstimos ativos
            tem_emprestimo_ativo = Emprestimo.objects.filter(cliente=cliente, status='ativo').exists()

            # Define o status do relatório
            status_relatorio = 'NV' if not tem_emprestimo_ativo else 'Outro'
            cliente.status_relatorio = status_relatorio  # Atualize o campo correspondente

            # Salva o cliente com o status atualizado
            cliente.save()

            messages.success(request, "Cliente cadastrado com sucesso!")
            return redirect('PELFCRED:lista_clientes')
    else:
        form = ClienteForm(user=request.user)  # Passa o usuário ao formulário

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
    logger.info(f"Tentando marcar o empréstimo {id_emprestimo} como inadimplente.")
    
    if request.method == 'POST':
        logger.info("Requisição POST recebida com sucesso.")
        
        try:
            emprestimo = get_object_or_404(Emprestimo, id=id_emprestimo)
            logger.info(f"Empréstimo {id_emprestimo} encontrado: {emprestimo}")
            
            emprestimo.status = 'inadimplentes'
            emprestimo.save()
            logger.info(f"Status do empréstimo {id_emprestimo} atualizado para inadimplentes.")
            
            messages.success(request, 'Empréstimo marcado como inadimplente com sucesso.')
        except Exception as e:
            logger.error(f"Erro ao marcar o empréstimo {id_emprestimo} como inadimplente: {e}")
            messages.error(request, 'Ocorreu um erro ao tentar marcar o empréstimo como inadimplente.')
    else:
        logger.warning("A requisição não foi do tipo POST.")
    
    return redirect('PELFCRED:detalhes_cliente', cpf=emprestimo.cliente.cpf)




@login_required
def editar_emprestimo(request, id):
    emprestimo = get_object_or_404(Emprestimo, id=id)
    if request.method == 'POST':
        form = EmprestimoForm(request.POST, instance=emprestimo)
        if form.is_valid():
            emprestimo = form.save(commit=False)
            emprestimo.valor_total_calculado = emprestimo.capital + (emprestimo.capital * emprestimo.taxa_juros / 100)
            emprestimo.valor_parcelado = emprestimo.valor_total_calculado / emprestimo.numero_parcelas
            emprestimo.save()
            messages.success(request, 'Contrato atualizado com sucesso.')
            return redirect('PELFCRED:lista_emprestimos')
        else:
            messages.error(request, f'Erro ao editar o contrato: {form.errors}')
    else:
        form = EmprestimoForm(instance=emprestimo)
    
    return render(request, 'editar_emprestimo.html', {'form': form, 'emprestimo': emprestimo})
@login_required
def cadastrar_emprestimo(request, cpf=None):
    cliente = get_object_or_404(Cliente, cpf=cpf)

    if request.method == 'POST':
        form = EmprestimoForm(request.POST)
        if form.is_valid():
            emprestimo = form.save(commit=False)
            emprestimo.cliente = cliente  # Vincular o cliente ao empréstimo
            emprestimo.grupo = request.user.groups.first()
            emprestimo.usuario = request.user
            
            
            # Definir o capital_inicial
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

            else:
                messages.success(request, 'Empréstimo cadastrado com sucesso.')
                logger.info("Redirecionando para lista de empréstimos.")
                return redirect('PELFCRED:detalhes_cliente', cpf=cliente.cpf)
        else:
            logger.error(f"Erro ao cadastrar o empréstimo: {form.errors}")
            messages.error(request, f'Erro ao cadastrar o empréstimo: {form.errors}')
    else:
        form = EmprestimoForm(initial={'cliente': cliente})
        logger.info("Formulário de empréstimo inicializado.")
        

    return render(request, 'cadastrar_emprestimo.html', {'form': form, 'cliente': cliente})



@login_required
def renovar_emprestimo(request, id):
    emprestimo = get_object_or_404(Emprestimo, id=id)
    
    if request.method == 'POST':
        # Capturar os valores de entrada de forma segura
        nova_taxa_juros_input = request.POST.get('nova_taxa_juros', '').strip()
        capital_adicional_input = request.POST.get('capital_adicional', '').strip()
        numero_parcelas_input = request.POST.get('parcelas', '').strip()
        frequencia = request.POST.get('frequencia')
        
        # Processar os dias da semana selecionados
        dias_semana = request.POST.getlist('dias_semana')  # Captura como lista
        dias_semana_str = ','.join(dias_semana)
        emprestimo.dias_semana = dias_semana_str

        # Validar e converter os valores para Decimal
        try:
            nova_taxa_juros = Decimal(nova_taxa_juros_input) if nova_taxa_juros_input else emprestimo.taxa_juros
            capital_adicional = Decimal(capital_adicional_input) if capital_adicional_input else Decimal('0')
            numero_parcelas = int(numero_parcelas_input) if numero_parcelas_input else emprestimo.numero_parcelas
        except (InvalidOperation, ValueError):
            messages.error(request, 'Valores inválidos fornecidos. Por favor, verifique os dados inseridos.')
            return redirect('PELFCRED:renovar_emprestimo', id=emprestimo.id)

        try:
            with transaction.atomic():
                # Atualizar os campos do empréstimo atual
                emprestimo.numero_parcelas = numero_parcelas
                emprestimo.frequencia = frequencia
                
                # Chamar o método renovar no modelo Emprestimo
                renovou = emprestimo.renovar(
                    nova_taxa_juros=nova_taxa_juros,
                    capital_adicional=capital_adicional
                )
                
                if renovou:
                    # Atualizar o status com base no capital adicional
                    if capital_adicional > 0:
                        emprestimo.status = 'R'  # Renovação
                    else:
                        emprestimo.status = 'NG'  # Negociação
                    emprestimo.save()
                    
                    logger.info(f"Empréstimo {emprestimo.id} renovado com sucesso por {request.user.username}.")
                    messages.success(request, 'Empréstimo renovado com sucesso!')
                    
                    # Redirecionar conforme o fluxo original
                    return redirect('PELFCRED:detalhes_cliente', cpf=emprestimo.cliente.cpf)
                else:
                    logger.error(f"Falha na renovação do empréstimo {emprestimo.id} por {request.user.username}.")
                    messages.error(request, 'Erro ao renovar empréstimo. Verifique os logs para mais detalhes.')
        except Exception as e:
            logger.error(f"Erro na transação de renovação do empréstimo {emprestimo.id}: {e}")
            messages.error(request, 'Erro ao renovar empréstimo. Operação revertida.')

    saldo_devedor = emprestimo.calcular_saldo_devedor()

    return render(request, 'renovar_emprestimo.html', {
        'emprestimo': emprestimo,
        'saldo_devedor': saldo_devedor,
        'juros_atual': emprestimo.taxa_juros,
        'capital_atual': emprestimo.capital,
        'dias_semana': emprestimo.dias_semana.split(',') if emprestimo.dias_semana else [],
    })
@login_required
def relatorio_emprestimos(request):
    user_group = request.user.groups.first()
    emprestimos_abertos = Emprestimo.objects.filter(grupo=user_group, saldo_devedor__gt=0)
    emprestimos_quitados = Emprestimo.objects.filter(grupo=user_group, saldo_devedor=0)

    context = {
        'emprestimos_abertos': emprestimos_abertos,
        'emprestimos_quitados': emprestimos_quitados,
    }
    return render(request, 'relatorio_emprestimos.html', context)


@login_required
def excluir_emprestimo(request, id):
    emprestimo = get_object_or_404(Emprestimo, id=id)
    if request.method == 'POST':
        emprestimo.delete()
        return redirect('PELFCRED:lista_emprestimos')
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
        pagamentos = Pagamento.objects.all()  # Admin pode ver todos os pagamentos
    else:
        pagamentos = Pagamento.objects.filter(usuario=request.user)  # Usuário comum vê apenas seus pagamentos
    
    # Calcular os totais de PIX e Dinheiro
    total_pix = pagamentos.filter(tipo_pagamento='PIX').aggregate(Sum('valor_pago'))['valor_pago__sum'] or 0
    total_dinheiro = pagamentos.filter(tipo_pagamento='DINHEIRO').aggregate(Sum('valor_pago'))['valor_pago__sum'] or 0
        # Calcular o total de pagamentos filtrados
    total_pagamentos = pagamentos.aggregate(total=Sum('valor_pago'))['total'] or 0
    
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
        # Filtrar os pagamentos que pertencem a empréstimos com saldo devedor negativo
        pagamentos = pagamentos.filter(emprestimo__saldo_devedor__lt=0)



    # Paginação
    paginator = Paginator(pagamentos, 10)  # Mostra 10 pagamentos por página
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
        'total_pagamentos': total_pagamentos,  # Passa o total para o template
        'total_pix': total_pix,
        'total_dinheiro': total_dinheiro,
    }

    return render(request, 'analisar_pagamentos.html', context)

@login_required
def rejeitar_pagamento(request, pagamento_id):
    if request.method == 'POST':
        # Busque o pagamento a ser rejeitado
        pagamento = get_object_or_404(Pagamento, id=pagamento_id)
        
        # Lógica para rejeitar o pagamento (pode ser ajustar o status, deletar, etc.)
        pagamento.delete()  # Exemplo: deletando o pagamento rejeitado
        
        return JsonResponse({'success': True})
    
    return JsonResponse({'success': False, 'error': 'Método não permitido'}, status=405)

@login_required
def importar_comprovante_pix(request):
    if request.method == 'POST':
        form = ComprovantePIXForm(request.POST, request.FILES)
        if form.is_valid():
            comprovante_pix = form.save(commit=False)
            comprovante_pix.usuario = request.user
            comprovante_pix.save()

            messages.success(request, 'Comprovante PIX importado com sucesso!')
            return redirect('PELFCRED:analisar_pagamentos')
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

        return redirect('PELFCRED:analisar_pagamentos')

@login_required
def registrar_pagamento(request, id_emprestimo=None):
    emprestimo = get_object_or_404(Emprestimo, id=id_emprestimo)

    # Somar os pagamentos feitos até o momento usando o nome correto do related_name
    valor_pago_total = emprestimo.pagamentos.aggregate(Sum('valor_pago'))['valor_pago__sum'] or Decimal(0)
    logger.debug(f"Empréstimo {emprestimo.id}: Total pago até agora: {valor_pago_total}")

    # O saldo devedor será o valor total do empréstimo menos o total pago
    saldo_devedor = emprestimo.calcular_saldo_devedor()
    logger.debug(f"Empréstimo {emprestimo.id}: Saldo devedor antes do pagamento: {saldo_devedor}")

    if request.method == 'POST':
        valor_pago = Decimal(request.POST.get('valor_pago', 0))
        comprovante = request.FILES.get('comprovante')
        tipo_pagamento = request.POST.get('tipo_pagamento')

        # Verifica o tipo de pagamento e atualiza o campo correspondente
        if tipo_pagamento == 'DINHEIRO':
            emprestimo.total_recebido_dinheiro += valor_pago
        elif tipo_pagamento == 'PIX':
            emprestimo.total_recebido += valor_pago
        
        # Certifique-se de que o valor pago é maior que 0
        if valor_pago > 0:
            # Registrar o pagamento com o tipo de pagamento correto
            pagamento = Pagamento.objects.create(
                emprestimo=emprestimo,
                data_pagamento=timezone.now(),  # Garante que a data seja a atual (com hora)
                valor_pago=valor_pago,
                tipo_pagamento=tipo_pagamento,  # Aqui associamos o tipo de pagamento ao pagamento
                cpf_pagador=emprestimo.cliente.cpf,
                nome_pagador=emprestimo.cliente.nome,
                comprovante_pix=comprovante,
                usuario=request.user
            )
            logger.debug(f"Pagamento {pagamento.id} registrado para o empréstimo {emprestimo.id} com valor {valor_pago} em {pagamento.data_pagamento}")

            # Atualizar o saldo devedor
            emprestimo.saldo_devedor = emprestimo.calcular_saldo_devedor()
            emprestimo.save()
            logger.debug(f"Empréstimo {emprestimo.id}: Saldo devedor após pagamento: {emprestimo.saldo_devedor}")
            
            # Verifica se o empréstimo deve ser finalizado
            emprestimo.verificar_finalizacao()
            
            messages.success(request, 'Pagamento registrado com sucesso!')
            return redirect('PELFCRED:detalhes_cliente', cpf=emprestimo.cliente.cpf)
        else:
            logger.warning(f"Empréstimo {emprestimo.id}: Tentativa de registrar pagamento com valor inválido: {valor_pago}")
            messages.error(request, 'Erro ao registrar pagamento. O valor deve ser maior que zero.')

    return render(request, 'registrar_pagamento.html', {
        'emprestimo': emprestimo,
        'valor_pago_total': valor_pago_total,  # Exibe o total pago até agora
        'saldo_devedor': saldo_devedor,  # Exibe o saldo devedor correto
    })
    
@login_required
def finalizar_contrato(request, id_emprestimo):
    emprestimo = get_object_or_404(Emprestimo, id=id_emprestimo)

    # Acessando o total pago usando o método dinamicamente
    total_pago = emprestimo.total_pago()

    # Verificar se o total pago cobre o valor total do empréstimo
    if total_pago < emprestimo.valor_total:
        messages.error(request, "O contrato não pode ser finalizado. O valor total ainda não foi pago.")
        return redirect('PELFCRED:detalhes_cliente', cpf=emprestimo.cliente.cpf)

    # Calcular os juros recebidos e atualizar o campo total_juros_recebidos
    juros_recebido = emprestimo.total_juros_recebidos + max(0, total_pago - emprestimo.capital_inicial - emprestimo.capital_adicional)
    
    emprestimo.total_juros_recebidos = juros_recebido
    emprestimo.status = 'finalizado'
    emprestimo.save()

    messages.success(request, f"Contrato finalizado com sucesso. Juros recebidos: R$ {juros_recebido:.2f}.")
    return redirect('PELFCRED:detalhes_cliente', cpf=emprestimo.cliente.cpf)


logger = logging.getLogger(__name__)


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, 'Login realizado com sucesso!')
            return redirect('PELFCRED:home')
        else:
            messages.error(request, 'Usuário ou senha inválidos.')
    return render(request, 'PELFCRED/login.html')
@login_required
def totais(request):
    # Obtenção dos parâmetros de filtro
    grupo_filtrado = request.GET.get('grupo', '')
    usuario_filtrado = request.GET.get('usuario', '')
    data_inicio = request.GET.get('data_inicio', '')
    data_fim = request.GET.get('data_fim', '')
    status_filtro = request.GET.get('status', 'NV')

    # Obtenção do usuário atual e seu grupo
    user = request.user
    grupo = user.groups.first()

    # Definir se o usuário é administrador
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

    # Inicializar as queries
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

    # Salvar os conjuntos de dados base para os totais
    clientes_base = clientes
    emprestimos_base = emprestimos
    pagamentos_base = pagamentos

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
        
            # Aplicação dos filtros por data de status e pagamentos
    if data_inicio and data_fim:
        emprestimos = emprestimos.filter(Q(data_inicio__gte=data_inicio) & Q(data_vencimento__lte=data_fim))
        pagamentos = pagamentos.filter(Q(data_pagamento__date__range=[data_inicio, data_fim]))
        emprestimos_query = emprestimos_query.filter(data_inicio__range=[data_inicio, data_fim])

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

    # Filtrar clientes e empréstimos para exibição na tabela
    clientes = clientes.filter(
        Q(status_relatorio='NV') |
        Q(emprestimo__status__in=['R', 'NG', 'inadimplentes', 'finalizado', 'ativo'])
    ).distinct()

    emprestimos = emprestimos.filter(
        status__in=['R', 'NG', 'inadimplentes', 'finalizado', 'ativo']
    )

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
    total_r = emprestimos_base.filter(status='R', capital__gt=0).count()
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

    totais_financeiros = {
        'total_capital': total_investido,
        'total_saldo_devedor': emprestimos_base.aggregate(total=Sum('saldo_devedor'))['total'] or Decimal(0),
    }

    # Calcular o total de juros recebidos
    total_juros_recebidos = emprestimos_todos.aggregate(
        total=Sum('total_juros_recebidos')
    )['total'] or Decimal(0)

    # Cálculo do total geral
    total_geral = {
        'total_clientes': clientes_base.count(),
        'total_emprestimos': emprestimos_base.count(),
        'total_investido': total_investido,
        'total_juros_recebidos': total_juros_recebidos,
    }

    # Contexto para o template
    contexto = {
        'total_juros_recebidos': total_juros_recebidos,
        'clientes': clientes,
        'emprestimos': emprestimos,
        'emprestimos': emprestimos_base,
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
        'data_inicio': data_inicio,
        'data_fim': data_fim,
        'grupos': Group.objects.all(),
        'usuarios': User.objects.all(),
        'total_pagamentos': total_pagamentos,
        'admin_view': admin_view,
        'data_hoje': date.today().strftime('%Y-%m-%d'),
        'status_list': ['R', 'NG', 'AC', 'NV', 'ativo'],  # Para uso no template
        'total_nvc':total_nvc
    }

    return render(request, 'totais.html', contexto)

@login_required
def alterar_status_cliente(request, cpf):
    cliente = get_object_or_404(Cliente, cpf=cpf)
    cliente.bloqueado = not cliente.bloqueado  # Alterna o status
    cliente.save()
    
    status = 'ativado' if not cliente.bloqueado else 'desativado'
    messages.success(request, f'O cliente {cliente.nome} foi {status} com sucesso.')
    
    return redirect('PELFCRED:lista_clientes')