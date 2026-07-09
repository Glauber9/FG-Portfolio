import logging
import mimetypes
import base64
from typing import Optional
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

class EvolutionAPIException(Exception):
    pass

class EvolutionAPIService:
    def __init__(self):
        self.base_url = settings.EVOLUTION_API_URL
        self.api_key = settings.EVOLUTION_API_KEY
        self.instance = settings.EVOLUTION_INSTANCE_NAME
        self.session = requests.Session()
        self.session.headers.update({'apikey': self.api_key})

    def _url(self, endpoint: str) -> str:
        return f'{self.base_url}/{endpoint}'

    def _request(self, method: str, endpoint: str, **kwargs) -> dict:
        url = self._url(endpoint)
        try:
            headers = dict(self.session.headers)
            request_headers = kwargs.pop('headers', None)
            if request_headers:
                headers.update(request_headers)
            if kwargs.get('files'):
                headers.pop('Content-Type', None)
            kwargs['headers'] = headers
            response = self.session.request(method, url, timeout=30, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            raise EvolutionAPIException(f"Timeout: {url}")
        except requests.exceptions.ConnectionError:
            raise EvolutionAPIException(f"Erro de conexão: {url}")
        except requests.exceptions.HTTPError as exc:
            raise EvolutionAPIException(f"Erro HTTP {exc.response.status_code}: {exc.response.text}")

    def _normalizar_telefone(self, telefone: str) -> str:
        telefone_limpo = ''.join(filter(str.isdigit, telefone))
        if not telefone_limpo.startswith('55'):
            telefone_limpo = f'55{telefone_limpo}'
        return telefone_limpo

    def enviar_mensagem(self, telefone: str, mensagem: str) -> str:
        telefone_limpo = self._normalizar_telefone(telefone)
        payload = {'number': telefone_limpo, 'text': mensagem}
        response = self._request('POST', f'message/sendText/{self.instance}', json=payload)
        mensagem_id = response.get('key', {}).get('id', '')
        if not mensagem_id:
            raise EvolutionAPIException("Evolution API não retornou ID")
        return mensagem_id

    def enviar_midia(self, telefone: str, media_bytes: bytes, media_nome: str, media_tipo: str, legenda: Optional[str] = None) -> str:
        telefone_limpo = self._normalizar_telefone(telefone)
        mimetype = mimetypes.guess_type(media_nome)[0]
        if not mimetype:
            mimetype = 'video/mp4' if media_tipo == 'video' else 'image/jpeg'
        media_base64 = base64.b64encode(media_bytes).decode('utf-8')
        payload = {
            'number': telefone_limpo,
            'mediatype': media_tipo,
            'media': media_base64,
            'mimetype': mimetype,
            'fileName': media_nome,
        }
        if legenda:
            payload['caption'] = legenda
        response = self._request('POST', f'message/sendMedia/{self.instance}', json=payload)
        mensagem_id = response.get('key', {}).get('id', '')
        if not mensagem_id:
            raise EvolutionAPIException("Evolution API não retornou ID")
        return mensagem_id

    def enviar_botoes_opt_out(self, telefone: str, texto: str, titulo: str = "", rodape: str = "") -> str:
        telefone_limpo = self._normalizar_telefone(telefone)
        payload = {
            'number': telefone_limpo,
            'title': titulo,
            'description': texto,
            'footer': rodape,
            'buttons': [
                {
                    'type': 'reply',
                    'displayText': 'Descadastrar',
                    'id': 'opt_out',
                }
            ],
        }
        response = self._request('POST', f'message/sendButtons/{self.instance}', json=payload)
        mensagem_id = response.get('key', {}).get('id', '')
        if not mensagem_id:
            raise EvolutionAPIException("Evolution API não retornou ID")
        return mensagem_id

    def verificar_instancia(self) -> bool:
        try:
            response = self._request('GET', 'instance/fetchInstances')
            instancias = response if isinstance(response, list) else []
            return any(i.get('instance', {}).get('instanceName') == self.instance for i in instancias)
        except EvolutionAPIException:
            return False

    def status_conexao(self) -> dict:
        try:
            response = self._request('GET', f'instance/connectionState/{self.instance}')
            return {
                'conectado': response.get('instance', {}).get('state') == 'open',
                'estado': response.get('instance', {}).get('state', 'desconhecido'),
            }
        except EvolutionAPIException as exc:
            return {'conectado': False, 'estado': str(exc)}