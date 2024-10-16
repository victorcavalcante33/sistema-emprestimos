from django import forms
from .models import Cliente, Emprestimo, ComprovantePIX, Pagamento
from datetime import date, timedelta
import re
from django import forms
from django.utils import timezone
from unidecode import unidecode
from django.contrib.auth.models import Group, User
class ClienteForm(forms.ModelForm):
    grupo = forms.ModelChoiceField(queryset=Group.objects.all(), required=False)
    usuario = forms.ModelChoiceField(queryset=User.objects.all(), required=False)

    class Meta:
        model = Cliente
        fields = [
            'cpf',
            'cnpj',
            'nome',
            'apelido',
            'documento',
            'telefone',
            'telefone2',
            'vinculo_telefone2',
            'cep',
            'endereco',
            'numero_endereco',
            'bairro',
            'complemento', 
            'uf', 
            'cidade', 
            'email',
            'grupo',
        ]    
       
        error_messages = {
            'cpf': {
                'required': 'Este campo é obrigatório',
                'invalid': 'Insira um CPF válido',
            },
            'nome': {
                'required': 'Este campo é obrigatório',
            },
            'apelido': {
                'required': 'Este campo é obrigatório',
                'invalid': 'Número de telefone inválido',
            },
            # Continue para outros campos...
        }
                
        labels = {
            'cpf': 'CPF*',
            'nome': 'Nome Completo',
            'documento': 'Documento',
            'cnpj': 'CNPJ',
            'telefone': 'Telefone',
            'telefone2': 'Telefone 2',
            'vinculo_telefone2': 'Parentesco ou Vínculo',
            'apelido': 'Apelido',
            'cep': 'CEP',
            'endereco': 'Endereço',
            'uf': 'UF',
            'cidade': 'Cidade',
            'numero_endereco': 'Número',
            'email': 'E-Mail',
            'grupo': 'Grupo'
        }
            
        vinculo_telefone2 = forms.CharField(
        required=False,
        label="Parentesco ou Vínculo",
        widget=forms.TextInput()
    )
        
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')  # Pega o usuário do kwargs
        super(ClienteForm, self).__init__(*args, **kwargs)

        # Mostra grupo e usuário apenas se o usuário for admin
        if not self.user.is_superuser:
            self.fields['grupo'].widget = forms.HiddenInput()
            self.fields['usuario'].widget = forms.HiddenInput()
        
            # Inicializa o CPF como readonly
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            if self.instance and self.instance.pk:
             self.fields['cpf'].disabled = True  # Desativa o campo CPF na edição

    # Validação do campo CPF (Apenas na criação)
    def clean_cpf(self):
        if self.instance and self.instance.pk:
            return self.instance.cpf  # Retorna o CPF atual sem validar se já existe
        cpf = self.cleaned_data.get('cpf')
        if not re.match(r'^\d{11}$', cpf):
            raise forms.ValidationError("CPF inválido. Deve conter 11 dígitos.")
        if Cliente.objects.filter(cpf=cpf).exists():
            raise forms.ValidationError("CPF Cadastrado")
        return cpf
      


    # Validação do campo nome
    def clean_nome(self):
        nome = self.cleaned_data.get('nome').strip()
        nome_normalizado = unidecode(nome.lower())  # Remover acentuação e normalizar

        # Verificar manualmente no banco de dados, mas sem destruir a lógica já existente
        for cliente in Cliente.objects.all():
            if Cliente.objects.filter(nome__iexact=nome_normalizado).exclude(pk=self.instance.pk).exists():
                raise forms.ValidationError("Nome Cadastrado.")
        return nome

    # Validação do campo apelido
    def clean_apelido(self):
        apelido = self.cleaned_data.get('apelido').strip()
        apelido_normalizado = unidecode(apelido.lower())  # Remover acentuação e normalizar

        # Verificar manualmente no banco de dados
        for cliente in Cliente.objects.all():
            if Cliente.objects.filter(apelido__iexact=apelido_normalizado).exclude(pk=self.instance.pk).exists():
                raise forms.ValidationError("Apelido Cadastrado.")
        return apelido

    def clean_cnpj(self):
        cnpj = self.cleaned_data.get('cnpj')
        if cnpj and not re.match(r'^\d{14}$', cnpj):
            raise forms.ValidationError("CNPJ inválido. Deve conter 14 dígitos.")
        return cnpj

def clean_telefone(self):
     telefone = self.cleaned_data.get('telefone')
     if telefone:  # Verifica se telefone não é None
        telefone = re.sub(r'\D', '', telefone)  # Remove todos os caracteres não numéricos
        if len(telefone) != 10 and len(telefone) != 11:
            raise forms.ValidationError("Número de telefone inválido. Deve conter 10 ou 11 dígitos.")
     return telefone  # Retorna o telefone sem formatação para armazenamento

def clean_telefone2(self):
    telefone2 = self.cleaned_data.get('telefone2')
    if telefone2:  # Verifica se telefone2 não é None
        telefone2 = re.sub(r'\D', '', telefone2)  # Remove todos os caracteres não numéricos
        if len(telefone2) != 10 and len(telefone2) != 11:
            raise forms.ValidationError("Número de telefone inválido. Deve conter 10 ou 11 dígitos.")
    return telefone2  # Retorna o telefone sem formatação para armazenamento

class EmprestimoForm(forms.ModelForm):
    DIAS_DA_SEMANA_CHOICES = [
        
        ('seg', 'Segunda'),
        ('ter', 'Terça'),
        ('qua', 'Quarta'),
        ('qui', 'Quinta'),
        ('sex', 'Sexta'),
        ('sab', 'Sábado'),
    ]
    dias_semana = forms.MultipleChoiceField(
        choices=DIAS_DA_SEMANA_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Dias da Semana",
    )
    
    class Meta:
        model = Emprestimo
        fields = ['cliente', 'capital', 'taxa_juros', 'data_inicio','dias_semana', 'frequencia', 'data_vencimento', 'parcelas', 'valor_parcelado', 'valor_total_calculado']
    data_inicio = forms.DateField(
        initial=date.today,  # Define a data de hoje como valor padrão
        widget=forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'})
    )
    data_vencimento = forms.DateField(
        widget=forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
        required=False  # Deixe opcional, pois vamos calcular isso manualmente
    )
    frequencia = forms.ChoiceField(
        choices=[
            ('diaria', 'Diária'),
            ('semanal', 'Semanal'),
            ('quinzenal', 'Quinzenal'),
            ('mensal', 'Mensal')
        ],
        label='Frequência'
    )
    parcelas = forms.IntegerField(
        label='Parcelas',
        min_value=1,
    )
    valor_parcelado = forms.DecimalField(
        label='Valor Parcelado',
        max_digits=10,
        decimal_places=2,
        widget=forms.TextInput(attrs={'readonly': 'readonly'})
    )
    valor_total_calculado = forms.DecimalField(
        label='Valor Total',
        max_digits=10,
        decimal_places=2,
        widget=forms.TextInput(attrs={'readonly': 'readonly'})
    )

    

    def clean_data_vencimento(self):
        data_inicio = self.cleaned_data.get('data_inicio')
        frequencia = self.cleaned_data.get('frequencia')

        if not data_inicio:
            raise forms.ValidationError("Data de início é obrigatória.")

        if frequencia == 'mensal':
            data_vencimento = data_inicio + timedelta(days=30)
        elif frequencia == 'quinzenal':  # Lógica para frequência quinzenal
            data_vencimento = data_inicio + timedelta(days=15)
        elif frequencia == 'semanal':
            data_vencimento = data_inicio + timedelta(weeks=1)
        elif frequencia == 'diaria':
            data_vencimento = data_inicio + timedelta(days=1)
        else:
            raise forms.ValidationError("Frequência inválida.")

        return data_vencimento

    def clean(self):
        cleaned_data = super().clean()
        cleaned_data['data_vencimento'] = self.clean_data_vencimento()  # Calcula e adiciona data_vencimento a cleaned_data
        return cleaned_data

class ComprovantePIXForm(forms.ModelForm):
    class Meta:
        model = ComprovantePIX
        fields = ['arquivo', 'identificador']
        identificador = forms.CharField(required=False, label="Identificador de API (opcional)")

class PagamentoForm(forms.ModelForm):
    class Meta:
        model = Pagamento
        fields = ['emprestimo', 
                  'valor_pago',
                  'tipo_pagamento',
                  'cpf_pagador',
                  'nome_pagador',
                  'data_pagamento']
        
        widgets = {
            'data_pagamento': forms.DateInput(attrs={'type': 'date'}),
            'emprestimo': forms.Select(),
            'valor_pago': forms.NumberInput(attrs={'step': '0.01'}),
            'tipo_pagamento': forms.Select(choices=[
                ('pix', 'Pix'),
                ('dinheiro', 'Dinheiro'),
                ('banco', 'Banco')
            ]),
            'cpf_pagador': forms.TextInput(attrs={'placeholder': 'CPF do Pagador'}),
            'nome_pagador': forms.TextInput(attrs={'placeholder': 'Nome do Pagador'}),
        }
        
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
        # Definindo a data de pagamento para a data atual se não estiver definida
            if not self.instance.data_pagamento:
                self.fields['data_pagamento'].initial = timezone.now().date()
                
