#!/bin/bash
set -e

WAIT_TIMEOUT=${WAIT_TIMEOUT_SECONDS:-60}
WAIT_INTERVAL=${WAIT_RETRY_INTERVAL:-2}
START_TIME=$(date +%s)

get_elapsed() { 
    echo $(($(date +%s) - START_TIME))
}

check_timeout() { 
    local elapsed=$(get_elapsed) 
    if [ $elapsed -gt $WAIT_TIMEOUT ]; then 
        echo "❌ Timeout após ${elapsed}s esperando por $1" 
        exit 1 
    fi
}

echo "🔄 Aguardando PostgreSQL (timeout: ${WAIT_TIMEOUT}s)..."
while ! pg_isready -h ${POSTGRES_HOST:-disparo_postgres} -U ${POSTGRES_USER:-disparo_user} -d ${POSTGRES_DB:-disparo_db} > /dev/null 2>&1; do 
    check_timeout "PostgreSQL" 
    sleep $WAIT_INTERVAL
done
echo "✅ PostgreSQL pronto ($(get_elapsed)s)"

echo "🔄 Aguardando Redis (timeout: ${WAIT_TIMEOUT}s)..."
if [ -n "$REDIS_URL" ]; then 
    until redis-cli -u "$REDIS_URL" ping > /dev/null 2>&1; do 
        check_timeout "Redis" 
        sleep $WAIT_INTERVAL 
    done
else 
    REDIS_AUTH="" 
    if [ -n "$REDIS_PASSWORD_FILE" ] && [ -f "$REDIS_PASSWORD_FILE" ]; then 
        REDIS_AUTH="-a $(cat "$REDIS_PASSWORD_FILE")" 
    elif [ -n "$REDIS_PASSWORD" ]; then 
        REDIS_AUTH="-a $REDIS_PASSWORD" 
    fi 
    until redis-cli -h ${REDIS_HOST:-disparo_redis} -p ${REDIS_PORT:-6379} ${REDIS_AUTH} ping > /dev/null 2>&1; do 
        check_timeout "Redis" 
        sleep $WAIT_INTERVAL 
    done
fi
echo "✅ Redis pronto ($(get_elapsed)s)"

echo "🚀 Executando migrações..."
python manage.py migrate --noinput

echo "🚀 Coletando arquivos estáticos..."
python manage.py collectstatic --noinput --clear --verbosity=0

echo "✅ Aplicação pronta para iniciar Gunicorn"
echo "🚀 Iniciando Gunicorn..."

exec gunicorn config.wsgi:application --config gunicorn.conf.py