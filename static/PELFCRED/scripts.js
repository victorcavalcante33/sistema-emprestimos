

function calcularValores() {
    var capital = parseFloat(document.getElementById("id_capital").value);
    var taxa_juros = parseFloat(document.getElementById("id_taxa_juros").value);
    var parcelas = parseInt(document.getElementById("id_parcelas").value);

    if (!isNaN(capital) && !isNaN(taxa_juros) && !isNaN(parcelas)) {
        var valor_total = capital * (1 + (taxa_juros / 100));
        var valor_parcelado = valor_total / parcelas;

        document.getElementById("valor_total").innerText = valor_total.toFixed(2);
        document.getElementById("valor_parcelado").innerText = valor_parcelado.toFixed(2);
    }
}

var ctx = document.getElementById('myChart').getContext('2d');

document.querySelector('.filtro-form').addEventListener('submit', function(e) {
    e.preventDefault();

    const formData = new FormData(this);
    const params = new URLSearchParams(formData);

    // Envia a requisição para o servidor com os filtros aplicados
    fetch(`/pelfcred/totais?${params.toString()}`)
        .then(response => response.json())
        .then(data => {
            // Atualiza os gráficos e os totais com os dados filtrados
            atualizarGraficos(data);
        });
});

 