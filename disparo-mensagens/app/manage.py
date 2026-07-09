#!/usr/bin/env python
import os
import sys
import time
import warnings


def main() -> None:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

    if sys.version_info < (3, 12):
        warnings.warn(
            f'Python 3.12+ é recomendado, mas você está usando Python '
            f'{sys.version_info.major}.{sys.version_info.minor}.',
            RuntimeWarning,
            stacklevel=2,
        )

    if not os.environ.get('DJANGO_SETTINGS_MODULE'):
        print(
            '[manage] AVISO: DJANGO_SETTINGS_MODULE não definido, '
            'usando config.settings como padrão.',
            file=sys.stderr,
        )

    start = time.perf_counter()

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Não foi possível importar o Django. "
            "Verifique se está instalado e disponível no PYTHONPATH. "
            "O ambiente virtual está ativado?"
        ) from exc

    execute_from_command_line(sys.argv)

    elapsed = time.perf_counter() - start
    if elapsed > 1 and os.getenv('DJANGO_DEBUG', '').lower() == 'true':
        print(f'[manage] Comando concluído em {elapsed:.2f}s', file=sys.stderr)


if __name__ == '__main__':
    main()