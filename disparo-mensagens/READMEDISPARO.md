# 📲 Campanhas de Mensagens

Sistema de disparo de mensagens em massa via WhatsApp, construído com **Django**, **Celery**, **PostgreSQL**, **Redis** e **Evolution API**, orquestrado com **Docker Compose** em ambientes separados para desenvolvimento e produção.

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-092E20?logo=django&logoColor=white)
![Celery](https://img.shields.io/badge/Celery-37814A?logo=celery&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-DC382D?logo=redis&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white)
![Nginx](https://img.shields.io/badge/Nginx-009639?logo=nginx&logoColor=white)

---

## 📑 Índice

- [Sobre o projeto](#-sobre-o-projeto)
- [Arquitetura e fluxo de subida](#-arquitetura-e-fluxo-de-subida)
- [Pré-requisitos](#-pré-requisitos)
- [Primeira configuração](#-primeira-configuração)
- [Variáveis de ambiente e segredos](#-variáveis-de-ambiente-e-segredos)
- [Ambiente local vs. produção](#-ambiente-local-vs-produção)
- [Estrutura de diretórios](#-estrutura-de-diretórios)
- [Importação de contatos](#-importação-de-contatos)
- [Comandos úteis](#-comandos-úteis)
- [Melhorias de segurança](#-melhorias-de-segurança)
- [Problemas comuns](#-problemas-comuns)
- [Documentação adicional](#-documentação-adicional)
- [Contato e contribuição](#-contato-e-contribuição)

---

## 🧾 Sobre o projeto

O Django concentra as regras da aplicação, as telas e os endpoints. O Celery executa tarefas em segundo plano, como filas e rotinas agendadas. O PostgreSQL guarda os dados, o Redis serve como fila e cache, e o Nginx fica na frente do Django quando o projeto vai para produção.

**Destaques técnicos:**
- Gerenciamento de segredos via **Docker Secrets**, não `.env` puro
- Healthchecks encadeados para inicialização segura dos serviços (Postgres → Redis → Django → Celery → Nginx)
- Importação de contatos por múltiplos canais: admin, upload de arquivo, API JSON ou URL remota
- Processamento assíncrono de campanhas via Celery, com retry e backoff exponencial em webhooks
- Ambientes de dev e produção isolados por arquivos de configuração, sem duplicar código

---

## 🏗️ Arquitetura e fluxo de subida

No Docker, os serviços sobem juntos com `docker-compose`, em ordem:

1. **PostgreSQL** e **Redis** iniciam primeiro.
2. O **Django** espera os dois ficarem prontos (healthcheck).
3. O Django roda **migrações** e coleta **arquivos estáticos**.
4. O **Gunicorn** inicia a aplicação.
5. O **Celery worker** e o **Celery beat** entram depois que o Django está saudável.
6. O **Nginx** entra por último e aponta para o Django.

> Se o Django falhar no boot, os serviços que dependem dele ficam presos em `unhealthy`.

---

## ⚙️ Pré-requisitos

- Docker 20.10 ou superior
- Docker Compose 2.x
- Python 3.11+ *(apenas se for rodar fora do Docker)*


---

## 🚀 Primeira configuração

### 1. Preparar o ambiente

```bash
cd disparo-mensagens
cp .env.dev .env
```

### 2. Ajustar o `.env`

Para teste local, use `.env.dev` como base e copie para `.env`. Use `DJANGO_DEBUG=True` só no ambiente local.

```env
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://localhost:8000
EVOLUTION_INSTANCE_NAME=minha-instancia
POSTGRES_DB=disparo_db
POSTGRES_USER=disparo_user
POSTGRES_HOST=disparo_postgres
POSTGRES_PORT=5432
REDIS_HOST=disparo_redis
REDIS_PORT=6379
```

### 3. Subir os containers

```bash
docker-compose up -d
```

### 4. Verificar se subiu

```bash
docker-compose ps
docker-compose logs -f disparo_django
```

### 5. Acessar a aplicação

| Serviço | URL |
|---|---|
| App Django (dev) | http://localhost:8000 |
| Nginx | http://localhost |
| Admin Django | http://localhost:8000/admin/ |
| API Health | http://localhost:8000/health/ |

---

## 🔐 Variáveis de ambiente e segredos

| Arquivo | Uso |
|---|---|
| `.env.dev` | Base do ambiente local |
| `.env.producao` | Base do ambiente de servidor |
| `.env` | Arquivo que o Docker lê de fato quando o projeto sobe |
| `secrets/` | Arquivos locais com senhas e chaves sensíveis, usados pelo Docker Secrets |

O `.env` guarda apenas configuração **não sensível** — hosts, portas e flags de ambiente. Senhas e chaves ficam em arquivos dentro de `secrets/`, montados pelo Docker Compose:

- `secrets/postgres_password`
- `secrets/redis_password`
- `secrets/django_secret_key`
- `secrets/authentication_api_key`
- `secrets/evolution_webhook_secret`
- `secrets/email_host_password`

**Regra simples:**
- Testando na sua máquina → cp `.env.dev` para `.env`
- Subindo no servidor → cp `.env.producao` para `.env`

---

## 🧪 Ambiente local vs. produção

Não é necessário duplicar todos os arquivos do projeto — o que muda entre local e produção é principalmente configuração.

| Item | Local (dev) | Produção |
|---|---|---|
| Arquivo de env | `.env.dev` → `.env` | `.env.producao` → `.env` |
| `DJANGO_DEBUG` | `True` | `False` |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | domínio real |
| `CSRF_TRUSTED_ORIGINS` | `http://localhost:8000` | domínio real com HTTPS |
| `ENVIRONMENT` | `development` | `production` |
| Porta do Django | exposta (`8000:8000`) | não publicada para o host |
| Nginx | `nginx/nginx.dev.conf` | `nginx/nginx.conf` |
| Comando de subida | `docker-compose up -d` | `docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d` |

**O que não muda entre ambientes:** models, migrations, tarefas do Celery, views, URLs da aplicação, estrutura dos apps, lógica de negócio.

**Ordem prática antes de subir:**
1. Escolha o ambiente: dev ou produção.
2. Copie o arquivo certo para `.env`.
3. Confira os valores de `DJANGO_DEBUG`, hosts e URLs.
4. Rebuild as imagens se alterou dependências ou Dockerfile.
5. Suba os containers.
6. Olhe o log do Django se algo falhar.

---

## 📂 Estrutura de diretórios

```
disparo-mensagens/
├── app/
│   ├── Dockerfile
│   ├── entrypoint.sh
│   ├── manage.py
│   ├── requirements.txt
│   ├── config/
│   │   ├── settings.py
│   │   ├── urls.py
│   │   ├── wsgi.py
│   │   └── celery.py
│   ├── campanhas/
│   ├── contatos/
│   └── envios/
├── nginx/
│   └── nginx.conf
├── docker-compose.yml
├── docker-compose.prod.yml
├── .env.example
└── README.md
```

### Fluxo de execução

O arquivo `app/entrypoint.sh` faz a sequência de inicialização do Django:

1. espera PostgreSQL;
2. espera Redis;
3. roda `migrate`;
4. roda `collectstatic`;
5. inicia o Gunicorn.

Se alguma variável obrigatória estiver faltando ou se uma dependência não carregar, o container do Django para antes do Gunicorn iniciar.

---

## 📥 Importação de contatos

O projeto aceita importação de contatos por três caminhos:

- pelo admin, enviando um CSV ou XLSX;
- pela API, enviando um arquivo em `arquivo`;
- pela API, enviando uma lista JSON em `contatos` ou uma URL remota em `url`.

**Endpoint:** `POST /contatos/api/importar/`

**Exemplo com arquivo local:**

```bash
curl -X POST http://localhost:8000/contatos/api/importar/ \
	-H "Authorization: Token SEU_TOKEN" \
	-F "arquivo=@contatos.xlsx"
```

**Exemplo com lista JSON:**

```bash
curl -X POST http://localhost:8000/contatos/api/importar/ \
	-H "Authorization: Token SEU_TOKEN" \
	-H "Content-Type: application/json" \
	-d '{
		"contatos": [
			{"nome": "Ana", "telefone": "5511999999999", "email": "ana@exemplo.com"},
			{"nome": "Bruno", "telefone": "5511888888888", "email": "bruno@exemplo.com", "ativo": true}
		]
	}'
```

**Exemplo com URL remota:**

```bash
curl -X POST http://localhost:8000/contatos/api/importar/ \
	-H "Authorization: Token SEU_TOKEN" \
	-H "Content-Type: application/json" \
	-d '{"url":"https://exemplo.com/contatos.xlsx"}'
```

**Resposta típica:**

```json
{
	"status": "ok",
	"resumo": {
		"criados": 10,
		"atualizados": 2,
		"ignorados": 0,
		"erros": [],
		"total": 12
	}
}
```

---

## 🛠️ Comandos úteis

### Logs

```bash
docker-compose logs -f
docker-compose logs -f disparo_django
docker-compose logs --tail=50 disparo_django
```

### Django

```bash
docker-compose exec disparo_django python manage.py migrate
docker-compose exec disparo_django python manage.py createsuperuser
docker-compose exec disparo_django python manage.py shell
docker-compose exec disparo_django pytest
```

### Banco de dados

```bash
docker-compose exec disparo_postgres psql -U disparo_user -d disparo_db

docker-compose exec disparo_postgres pg_dump -U disparo_user -d disparo_db > backup.sql
```

### Celery

```bash
docker-compose exec disparo_redis redis-cli -a <REDIS_PASSWORD> keys "*"
docker-compose exec disparo_celery celery -A config purge
```

### Rebuild

```bash
docker-compose build --no-cache
docker-compose restart disparo_django
```

### Limpeza

```bash
docker-compose down
docker-compose down -v
```

### Produção

Antes de subir em servidor, confirme:

- `DJANGO_DEBUG=False`
- `DJANGO_ALLOWED_HOSTS` com o domínio correto
- `CSRF_TRUSTED_ORIGINS` com o domínio correto
- arquivos de `secrets/` preenchidos com valores reais
- Nginx com HTTPS
- rebuild da imagem com as dependências finais

```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

---

## 🔒 Melhorias de segurança

- [ ] Remover `ports: "8000:8000"` do Django no `docker-compose.yml`
- [x] Usar Docker Secrets para senhas e chaves sensíveis (ao invés de `.env`)
- [ ] Configurar SSL/TLS no Nginx
- [ ] Habilitar HTTPS via Let's Encrypt
- [ ] Usar variáveis de ambiente seguras (AWS Secrets Manager, Vault, etc.)
- [ ] Configurar WAF (Web Application Firewall)
- [ ] Implementar rate limiting no Nginx

---

## 🩹 Problemas comuns

**Django aparece como unhealthy**
Normalmente indica que o boot do Django falhou antes do healthcheck responder.
```bash
docker-compose logs -f disparo_django
```

**"Connection refused" ao conectar ao Django**
```bash
docker-compose ps disparo_django
docker-compose logs disparo_django
```

**Migrations não rodaram**
```bash
docker-compose exec disparo_django python manage.py migrate --verbosity=2
```

**Redis ou Postgres não iniciam**
```bash
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

**Celery não processa tarefas**
```bash
docker-compose exec disparo_redis redis-cli -a <REDIS_PASSWORD> PING
docker-compose logs -f disparo_celery
```

---

## 📚 Documentação adicional

- [DOCKER_IMPROVEMENTS.md](DOCKER_IMPROVEMENTS.md) — melhorias do Docker
- [Django Docs](https://docs.djangoproject.com/)
- [Celery Docs](https://docs.celeryproject.org/)
- [Evolution API Docs](https://doc.evoapicloud.com/)

---

## 🤝 Contato e contribuição

Para dúvidas ou contribuições, abra uma issue ou PR.

---

*Última atualização: Julho de 2026*
