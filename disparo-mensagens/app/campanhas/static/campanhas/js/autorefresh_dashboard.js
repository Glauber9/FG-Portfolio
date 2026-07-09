(function () {
    var INTERVALO_MS = 5000;
    var base = window.location.pathname;
    if (!base.endsWith('/')) {
        base += '/';
    }
    var urls = [
        base + 'campanhas/campanha/status-atualizacao/',
        base + 'envios/envio/status-atualizacao/',
    ];
    var ultimaConhecida = null;
    var checando = false;

    function maiorData(a, b) {
        if (!a) return b;
        if (!b) return a;
        return a > b ? a : b;
    }

    function verificar() {
        if (checando) return;
        checando = true;

        Promise.all(urls.map(function (url) {
            return fetch(url, { credentials: 'same-origin' })
                .then(function (resp) { return resp.ok ? resp.json() : { ultima_atualizacao: null }; })
                .catch(function () { return { ultima_atualizacao: null }; });
        })).then(function (resultados) {
            var atual = null;
            resultados.forEach(function (r) {
                atual = maiorData(atual, r.ultima_atualizacao);
            });

            if (ultimaConhecida === null) {
                ultimaConhecida = atual;
                return;
            }
            if (atual !== ultimaConhecida) {
                window.location.reload();
            }
        }).finally(function () {
            checando = false;
        });
    }

    setInterval(verificar, INTERVALO_MS);
})();
