from django.db import models
from django.utils import timezone
from decimal import Decimal
from django.contrib.auth.models import Group, User
from django.db.models import Sum
from django.core.exceptions import ValidationError
from datetime import timedelta
import logging


class Cliente(models.Model):
    cpf = models.CharField(
        max_length=11,
        primary_key=True,
        error_messages={
            'unique': "Cpf já cadastrado."
        }
    )
    nome = models.CharField(max_length=100, null=True, blank=True)  # Nome completo
    apelido = models.CharField(max_length=50, null=True, blank=True)  # Apelido
    documento = models.CharField(max_length=20, null=True, blank=True)  # Documento (opcional)
    cnpj = models.CharField(max_length=14, null=True, blank=True)  # CNPJ (opcional)
    telefone = models.CharField(max_length=11, null=True, blank=True)  # Telefone (opcional)
    telefone2 = models.CharField(max_length=11, null=True, blank=True)  # Telefone 2 (opcional)
    endereco = models.CharField(max_length=200, null=True, blank=True)  # Endereço (opcional)
    numero_endereco = models.CharField(max_length=10, null=True, blank=True)  # Número do Endereço (opcional)
    cep = models.CharField(max_length=8, null=True, blank=True)  # CEP (opcional)
    bairro = models.CharField(max_length=100, null=True, blank=True)  # Bairro (opcional)
    complemento = models.CharField(max_length=100, null=True, blank=True)  # Complemento (opcional)
    uf = models.CharField(max_length=2, null=True, blank=True)  # UF (opcional)
    cidade = models.CharField(max_length=100, null=True, blank=True)  # Cidade (opcional)
    email = models.EmailField(null=True, blank=True)  # E-Mail (opcional)
    bloqueado = models.BooleanField(default=False)  # Bloqueado? (campo booleano)
    data_registro = models.DateTimeField(auto_now_add=True)  # Data de Registro (automático)
    grupo = models.ForeignKey(Group, on_delete=models.CASCADE, null=True, blank=True)  # Associar cada cliente a um grupo
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)  # Associar cada cliente a um usuário
    vinculo_telefone2 = models.CharField(max_length=100, null=True, blank=True)  # Campo para o vínculo ou parentesco
    STATUS_RELATORIO_CHOICES = [
        ('NV', 'Novo'),
        ('R', 'Renovado'),
        ('NG', 'Negociado'),
        ('AC', 'Finalizado'),
    ]
    status_relatorio = models.CharField(max_length=10, choices=STATUS_RELATORIO_CHOICES, default='Outro')
    def save(self, *args, **kwargs):
        # Garantir que o nome completo e o apelido comecem com letra maiúscula
        self.nome = self.nome.title()
        self.apelido = self.apelido.title()
        super(Cliente, self).save(*args, **kwargs)
    def __str__(self):
        return self.nome or self.cpf  # Exibir o CPF se o nome não estiver disponível
def clean(self):
    super().clean()
    # Verifica se já existe um cliente com o mesmo nome, mas diferente CPF
    if Cliente.objects.filter(nome=self.nome).exclude(cpf=self.cpf).exists():
        raise ValidationError('Já existe um cliente com este nome.')
    
class DescontoJuros(models.Model):
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    data = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    data_inicio = models.DateTimeField(null=True, blank=True)
    data_fim = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.valor} em {self.data.strftime('%d/%m/%Y %H:%M')}"
    

logger = logging.getLogger(__name__)
class Emprestimo(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    valor_total = models.DecimalField(max_digits=10, decimal_places=2)
    capital = models.DecimalField(max_digits=10, decimal_places=2)
    capital_inicial = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    capital_adicional = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    capital_adicional_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_juros_recebidos = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    data_renovacao = models.DateTimeField(null=True, blank=True)
    taxa_juros = models.DecimalField(max_digits=5, decimal_places=2)
    data_inicio = models.DateField()
    data_vencimento = models.DateField()
    total_recebido = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_recebido_dinheiro = models.DecimalField(max_digits=10, decimal_places=2, default=0)
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
    }
    FREQUENCIA_CHOICES = [
        ('diaria', 'Diária'),
        ('semanal', 'Semanal'),
        ('quinzenal', 'Quinzenal'),
        ('mensal', 'Mensal')
    ]
    frequencia = models.CharField(max_length=10, choices=FREQUENCIA_CHOICES, default='mensal')
    numero_parcelas = models.IntegerField(default=12)
    valor_parcelado = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    valor_total_calculado = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    status_anterior = models.CharField(max_length=20, blank=True, null=True)
    
    def salvar_status_anterior(self):
        if self.status != 'finalizado':
            self.status_anterior = self.status  # Armazena o status atual como o status anterior
    
    
    def parcelas_info(self):
        return f"{self.numero_parcelas}x{self.valor_parcelado:.0f}"
    grupo = models.ForeignKey(Group, on_delete=models.CASCADE, null=True, blank=True)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)  
    renovado = models.BooleanField(default=False)
    saldo_devedor = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    data_renovacao = models.DateTimeField(null=True, blank=True)  # Agora com data e hora
    capital_adicional = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    juros_recebidos = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal(0))
    total_juros_recebidos = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal(0))
    dias_semana = models.CharField(max_length=100, blank=True, null=True)
    
    
    STATUS_CHOICES = [
        ('ativo', 'Ativo'),
        ('R', 'R'),
        ('NG', 'NG'),
        ('finalizado', 'AC'),
        ('inadimplentes', 'Inadimplente'),
    ]

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ativo')
    
    DIAS_DA_SEMANA = [
        ('seg', 'Segunda'),
        ('ter', 'Terça'),
        ('qua', 'Quarta'),
        ('qui', 'Quinta'),
        ('sex', 'Sexta'),
        ('sab', 'Sábado'),
    ]
    
    def save(self, *args, **kwargs):
        super(Emprestimo, self).save(*args, **kwargs)

    def total_pago(self):
        return self.pagamentos.aggregate(Sum('valor_pago'))['valor_pago__sum'] or Decimal('0.00')
    
    def verificar_finalizacao(self):
        if self.saldo_devedor <= 0 and self.status != 'finalizado':
            total_pago = self.total_pago()
            total_investido = self.capital_inicial + self.capital_adicional_total
            juros_recebido = max(Decimal('0.00'), total_pago - total_investido)

            self.total_juros_recebidos = juros_recebido
            self.status = 'finalizado'
            self.saldo_devedor = Decimal('0.00')
            self.save()
    
    def get_dias_semana_display(self):
        """Retorna uma lista com os dias da semana armazenados"""
        if self.dias_semana:
            dias = self.dias_semana.split(',')
            return [dict(self.DIAS_DA_SEMANA).get(dia) for dia in dias]
        return []

    def calcular_saldo_devedor(self):
        try:
            # Inicializa o total de pagamentos
            total_pagamentos = Decimal(0)

            # Verifica se o empréstimo foi renovado
            if self.renovado and self.data_renovacao:
                # Considera apenas os pagamentos feitos após a data e hora da renovação
                total_pagamentos = self.pagamentos.filter(data_pagamento__gt=self.data_renovacao).aggregate(Sum('valor_pago'))['valor_pago__sum'] or Decimal(0)
                logger.debug(f"Empréstimo {self.id}: Considerando apenas pagamentos após renovação. Total pagos: {total_pagamentos}")
            else:
                # Considera todos os pagamentos se não houve renovação
                total_pagamentos = self.pagamentos.aggregate(Sum('valor_pago'))['valor_pago__sum'] or Decimal(0)
                logger.debug(f"Empréstimo {self.id}: Considerando todos os pagamentos. Total pagos: {total_pagamentos}")

            # Cálculo do saldo devedor atual com base no capital e capital adicional
            saldo_devedor_atual = (self.capital + self.capital_adicional) * (1 + (self.taxa_juros / 100))

            # Subtrai o total dos pagamentos realizados
            saldo_devedor_atual -= total_pagamentos

            logger.debug(f"Empréstimo {self.id}: Saldo devedor calculado após ajuste: {saldo_devedor_atual}")
            return saldo_devedor_atual
        except Exception as e:
            logger.error(f"Erro ao calcular saldo devedor para empréstimo {self.id}: {e}")
            return Decimal(0)
        
    import logging
    logger = logging.getLogger(__name__)
    def renovar(self, nova_taxa_juros=None, capital_adicional=0):
        try:
            if nova_taxa_juros is None:
                nova_taxa_juros = self.taxa_juros

            # Calcula os juros acumulados não recebidos até o momento
            juros_acumulados_anteriores = self.calcular_juros()

            # Atualiza o total de juros recebidos
            self.total_juros_recebidos += juros_acumulados_anteriores

            # Registra o lucro (juros recebidos)
            JurosRecebido.objects.create(
                emprestimo=self,
                valor=juros_acumulados_anteriores,
                data_hora=timezone.now()
            )

            # Atualiza o capital adicional total
            if capital_adicional > 0:
                self.capital_adicional_total += capital_adicional
                # Cria um registro de saída para o capital adicional
                Saida.objects.create(
                    emprestimo=self,
                    valor=capital_adicional,
                    data_hora=timezone.now()
                )

            # Calcula o novo capital (saldo devedor atual + capital adicional)
            saldo_atual = self.saldo_devedor
            self.capital = saldo_atual + capital_adicional

            # Atualiza a taxa de juros
            self.taxa_juros = nova_taxa_juros

            # Recalcula o valor total do empréstimo
            novos_juros = self.capital * (nova_taxa_juros / 100)
            self.valor_total = self.capital + novos_juros

            # Atualiza o saldo devedor
            self.saldo_devedor = self.valor_total

            # Atualiza as datas
            self.data_inicio = timezone.now()
            self.data_renovacao = None  # Reiniciamos a data de renovação

            # Salva as alterações
            self.save()

            # Recria as parcelas
            self.parcelas_emprestimo.all().delete()
            dias_frequencia = {
                'diaria': 1,
                'semanal': 7,
                'quinzenal': 15,
                'mensal': 30
            }
            for i in range(self.numero_parcelas):
                data_vencimento = self.data_inicio + timedelta(days=dias_frequencia[self.frequencia] * i)
                Parcela.objects.create(
                    emprestimo=self,
                    data_vencimento=data_vencimento,
                    pago=False
                )

            logger.debug(f"Empréstimo {self.id}: Renovado em {timezone.now().strftime('%d/%m/%Y %H:%M')}")
            return True
        except Exception as e:
            logger.error(f"Erro ao renovar empréstimo {self.id}: {e}")
            return False


    def calcular_juros(self):
        """Calcula os juros acumulados não recebidos até o momento."""
    # Determina a data de início para o cálculo dos juros
        if self.data_renovacao:
            data_inicio_calculo = self.data_renovacao
        else:
            data_inicio_calculo = self.data_inicio


        # Calcula o tempo decorrido em meses
        tempo_decorrido = (timezone.now().date() - data_inicio_calculo).days / 30

        taxa_juros_mensal = Decimal(self.taxa_juros) / Decimal(100)
        tempo_decorrido = Decimal(tempo_decorrido)

        # Calcula os juros acumulados com base no tempo decorrido
        juros_acumulados = self.capital * taxa_juros_mensal * tempo_decorrido

        # Subtrai os juros já recebidos desde a última renovação
        juros_acumulados -= self.total_juros_recebidos

        # Garante que o valor não seja negativo
        if juros_acumulados < 0:
            juros_acumulados = Decimal('0.00')

        return juros_acumulados
    


    def calcular_valor_total(self):
        """Calcula o valor total do empréstimo com base no capital e taxa de juros."""
        try:
            valor_juros = self.capital * (self.taxa_juros / 100)
            self.valor_total = self.capital + valor_juros
            return self.valor_total
        except Exception as e:
            logger.error(f"Erro ao calcular valor total do empréstimo {self.id}: {e}")
            return Decimal(0.00)

    def calcular_valor_juros(self):
        """Calcula o valor dos juros acumulados"""
        
        return self.valor_total - self.capital

        
class Pagamento(models.Model):
    emprestimo = models.ForeignKey(Emprestimo, on_delete=models.CASCADE, related_name='pagamentos')
    data_pagamento = models.DateTimeField()
    valor_pago = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    tipo_pagamento = models.CharField(max_length=50, choices=[('pix', 'PIX'), ('dinheiro', 'Dinheiro'), ('banco_outro', 'Banco de Outra Pessoa')], null=True, blank=True)
    cpf_pagador = models.CharField(max_length=11, null=True, blank=True)
    nome_pagador = models.CharField(max_length=200, null=True, blank=True)
    comprovante_pix = models.ImageField(upload_to='comprovantes_pix/', null=True, blank=True)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    grupo = models.ForeignKey(Group, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f'Pagamento em {self.data_pagamento} - Parcela'
    
class Parcela(models.Model):
    emprestimo = models.ForeignKey(Emprestimo, on_delete=models.CASCADE, related_name='parcelas_emprestimo')
    data_vencimento = models.DateField()  # Apenas a data de vencimento, sem valor
    pago = models.BooleanField(default=False)  # Campo para indicar se a parcela foi paga
    data_pagamento = models.DateField(null=True, blank=True)  # Data real de pagamento, se pago

    def __str__(self):
        return f'Parcela com vencimento em {self.data_vencimento}'

class ComprovantePIX(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    arquivo = models.ImageField(upload_to='comprovantes_pix/')
    identificador = models.CharField(max_length=255, null=True, blank=True)
    data_upload = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Comprovante de {self.usuario.username} - {self.data_upload.strftime("%d-%m-%Y")}'


class Saida(models.Model):
    emprestimo = models.ForeignKey(Emprestimo, on_delete=models.CASCADE, related_name='saidas')
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    data_hora = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Saída de R$ {self.valor:.2f} em {self.data_hora.strftime('%d/%m/%Y %H:%M')} para o empréstimo {self.emprestimo.id}"
    

class JurosRecebido(models.Model):
    emprestimo = models.ForeignKey(
        Emprestimo,
        on_delete=models.CASCADE,
        related_name='jurosrecebidos'  # Alterado o related_name para evitar conflito
    )
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    data_hora = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Juros de R$ {self.valor:.2f} recebidos em {self.data_hora.strftime('%d/%m/%Y %H:%M')}"

