document.addEventListener("DOMContentLoaded", function() {
    const form = document.querySelector("form");
    const cepInput = document.getElementById('id_cep');
    const cnpjInput = document.getElementById('id_cnpj');
    const cpfInput = document.getElementById('id_cpf');
    const emailInput = document.getElementById('id_email');


    // Validação do CEP e preenchimento automático do endereço
cepInput.addEventListener('blur', function() {
    const cep = this.value.replace(/\D/g, ''); // Remove caracteres não numéricos
    if (cep.length === 8) {
        fetch(`https://viacep.com.br/ws/${cep}/json/`)
            .then(response => {
                if (!response.ok) {
                    throw new Error("Erro ao buscar o CEP");
                }
                return response.json();
            })
            .then(data => {
                if (!data.erro) {
                    // Preenche os campos de endereço com os dados retornados pela API
                    document.getElementById('id_endereco').value = data.logradouro || "";
                    document.getElementById('id_bairro').value = data.bairro || "";
                    document.getElementById('id_cidade').value = data.localidade || "";
                    document.getElementById('id_uf').value = data.uf || "";
                } else {
                    alert("CEP não encontrado.");
                }
            })
            .catch(error => {
                console.error(error);
                alert("Erro ao buscar o CEP.");
            });
    }
});

    // Função para validar o formulário ao submeter
    form.addEventListener("submit", function(event) {
        let formValid = true;



        // Validação do CPF
        const cpf = cpfInput.value.replace(/\D/g, '');
        if (!validarCPF(cpf)) {
            formValid = false;
            alert('CPF inválido. Verifique os dígitos.');
        }

        // Validação do CNPJ
        const cnpj = cnpjInput.value.replace(/\D/g, '');
        if (!validarCNPJ(cnpj)) {
            formValid = false;
            alert('CNPJ inválido. O formato correto é XX.XXX.XXX/XXXX-XX.');
        }

        // Validação do Email
        const email = emailInput.value;
        if (!validarEmail(email)) {
            formValid = false;
            alert('Email inválido. Verifique o formato.');
        }

        // Se o formulário não for válido, cancelar o envio
        if (!formValid) {
            event.preventDefault(); // Impede o envio do formulário
        }
    });
});

// Função de validação de Email
function validarEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

// Função de validação de CNPJ
function validarCNPJ(cnpj) {
    const cnpjRegex = /^\d{14}$/; // Aqui removemos a formatação e validamos os 14 dígitos
    if (!cnpjRegex.test(cnpj)) return false;

    // Adicionar lógica para validar os dígitos verificadores do CNPJ
    return true; // Placeholder, adicione a validação completa de CNPJ se necessário
}

// Função de validação de CPF aprimorada
function validarCPF(cpf) {
    // Verifica se o CPF contém 11 dígitos
    if (cpf.length !== 11) return false;

    // Verifica se todos os dígitos são iguais, o que é inválido
    if (/^(\d)\1+$/.test(cpf)) return false;

    // Lista de CPFs conhecidos como inválidos (mesmo que sigam a regra dos dígitos verificadores)
    const cpfsInvalidos = [
        "00000000000",
        "11111111111",
        "22222222222",
        "33333333333",
        "44444444444",
        "55555555555",
        "66666666666",
        "77777777777",
        "88888888888",
        "99999999999"
    ];

    if (cpfsInvalidos.includes(cpf)) {
        return false; // CPF inválido por estar na lista de CPFs fictícios
    }

    // Cálculo do primeiro dígito verificador
    let soma = 0;
    for (let i = 0; i < 9; i++) {
        soma += parseInt(cpf.charAt(i)) * (10 - i);
    }
    let resto = 11 - (soma % 11);
    let digitoVerificador1 = resto === 10 || resto === 11 ? 0 : resto;

    // Cálculo do segundo dígito verificador
    soma = 0;
    for (let i = 0; i < 10; i++) {
        soma += parseInt(cpf.charAt(i)) * (11 - i);
    }
    resto = 11 - (soma % 11);
    let digitoVerificador2 = resto === 10 || resto === 11 ? 0 : resto;

    // Retorna true se os dois dígitos verificadores estiverem corretos
    return digitoVerificador1 === parseInt(cpf.charAt(9)) && digitoVerificador2 === parseInt(cpf.charAt(10));
}