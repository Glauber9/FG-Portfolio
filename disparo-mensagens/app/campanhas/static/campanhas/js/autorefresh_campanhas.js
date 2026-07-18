(function () {
    var INTERVALO_MS = 5000;

    var ultimaConhecida = null;
    var checando = false;

    function verificar() {
        if (checando) return;
        checando = true;
        fetch('status-atualizacao/', { credentials: 'same-origin' })
            .then(function (resp) {
                if (!resp.ok) throw new Error('Resposta não OK');
                return resp.json();
            })
            .then(function (data) {
                if (ultimaConhecida === null) {
                    ultimaConhecida = data.ultima_atualizacao;
                    return;
                }
                if (data.ultima_atualizacao !== ultimaConhecida) {
                    window.location.reload();
                }
            })
            .catch(function () {
            })
            .finally(function () {
                checando = false;
            });
    }

    document.addEventListener('visibilitychange', function () {
        if (!document.hidden) verificar();
    });

    if (document.body.classList.contains('change-list')) {
        setInterval(verificar, INTERVALO_MS);
    }
})();
