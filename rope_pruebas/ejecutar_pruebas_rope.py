"""Pruebas de Cookiecutter con Rope (refactorización automática).

Réplica del experimento hecho sobre PySnooper (../PySnooper_tesis/rope_pruebas),
con los mismos tipos de refactorización y la misma numeración (02-12), más
tres casos propios de Cookiecutter (13-15).

Flujo:
  1. Línea base: corre la suite de tests original de Cookiecutter.
  2. Análisis estático con Rope (sin modificar código): find_errors,
     find_occurrences y find_definition.
  3. Refactorizaciones: cada una se aplica con la API de Rope sobre una
     copia limpia del proyecto, se guarda el diff y se vuelve a correr la
     suite de tests. Si los tests siguen pasando, la refactorización
     preservó el comportamiento.

El código original en ../cookiecutter NUNCA se modifica.

Uso (desde la raíz del repositorio):
    .venv/bin/python rope_pruebas/ejecutar_pruebas_rope.py
"""
import json
import os
import re
import shutil
import subprocess
import sys
import time
import traceback
from pathlib import Path

import rope
from rope.base.project import Project
from rope.contrib import findit, finderrors
from rope.refactor.extract import ExtractMethod
from rope.refactor.inline import create_inline
from rope.refactor.move import create_move
from rope.refactor.rename import Rename

AQUI = Path(__file__).resolve().parent
REPO = AQUI.parent
TRABAJO = AQUI / '_trabajo'
RESULTADOS = AQUI / 'resultados'
PYTHON = sys.executable

IGNORAR = shutil.ignore_patterns(
    '.git', '.github', '.venv', '.pytest_cache', '*.egg-info', '__pycache__',
    '.ropeproject', 'rope_pruebas', 'llm_pruebas', 'docs', 'logo',
)


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def copia_limpia(nombre):
    """Copia el repositorio (sin .git/.venv/docs) a _trabajo/<nombre>."""
    destino = TRABAJO / nombre
    if destino.exists():
        shutil.rmtree(destino)
    shutil.copytree(REPO, destino, ignore=IGNORAR)
    return destino


def entorno(carpeta):
    """Variables de entorno para que se importe el cookiecutter de la copia.

    El .venv tiene cookiecutter instalado en modo editable apuntando al
    repositorio original; PYTHONPATH va antes en sys.path y lo tapa.
    """
    env = dict(os.environ)
    env['PYTHONPATH'] = str(carpeta)
    return env


def correr_pytest(carpeta):
    """Corre pytest en `carpeta` y devuelve (resumen, salida completa)."""
    # -o addopts= desactiva el --cov que trae pyproject.toml (más rápido y
    # la salida queda limpia para contar resultados).
    proc = subprocess.run(
        [PYTHON, '-m', 'pytest', 'tests', '-q', '-rs', '-p', 'no:cacheprovider',
         '-o', 'addopts='],
        cwd=carpeta, capture_output=True, text=True, env=entorno(carpeta),
    )
    salida = proc.stdout + proc.stderr
    resumen = {'returncode': proc.returncode}
    for clave in ('passed', 'failed', 'skipped', 'error', 'errors'):
        m = re.search(r'(\d+) ' + clave + r'\b', salida)
        resumen[clave] = int(m.group(1)) if m else 0
    resumen['errors'] += resumen.pop('error')
    return resumen, salida


def verificar_import(carpeta):
    """Confirma que se importa el cookiecutter de la copia, no otro."""
    proc = subprocess.run(
        [PYTHON, '-c', 'import cookiecutter; print(cookiecutter.__file__)'],
        cwd=carpeta, capture_output=True, text=True, env=entorno(carpeta),
    )
    ruta = proc.stdout.strip()
    assert ruta.startswith(str(carpeta)), ruta
    return ruta


def abrir_proyecto(carpeta):
    """Abre la copia como proyecto Rope.

    tests/ contiene ~19 archivos .py que en realidad son plantillas Jinja
    (por ejemplo `{% if cookiecutter.abort_pre_gen == "yes" %}`) y no son
    Python válido. Sin ignore_syntax_errors, Rope aborta con ModuleSyntaxError
    en cuanto una operación recorre todo el proyecto (find_occurrences,
    Rename, Move...).
    """
    return Project(str(carpeta), ignore_syntax_errors=True)


def offset_de(recurso, marcador, desplazamiento=0):
    """Offset (en caracteres) de `marcador` dentro del archivo."""
    codigo = recurso.read()
    assert codigo.count(marcador) == 1, 'marcador ambiguo o ausente: %r' % marcador
    return codigo.index(marcador) + desplazamiento


def inicio_de_linea(recurso, marcador):
    codigo = recurso.read()
    return codigo.rfind('\n', 0, offset_de(recurso, marcador)) + 1


def linea_anterior(recurso, offset):
    """Inicio de la línea anterior a `offset` (para excluir una línea en blanco)."""
    return recurso.read().rfind('\n', 0, offset - 1) + 1


# ---------------------------------------------------------------------------
# 1. Línea base
# ---------------------------------------------------------------------------

def linea_base():
    carpeta = copia_limpia('00_linea_base')
    ruta = verificar_import(carpeta)
    resumen, salida = correr_pytest(carpeta)
    (RESULTADOS / '00_linea_base_pytest.txt').write_text(salida)
    print('[linea base] %s  (cookiecutter importado desde %s)' % (resumen, ruta))
    return resumen


# ---------------------------------------------------------------------------
# 2. Análisis estático
# ---------------------------------------------------------------------------

SIMBOLOS = [
    # (archivo, marcador, desplazamiento hasta el nombre)
    ('cookiecutter/utils.py', 'def create_env_with_context', 4),
    ('cookiecutter/repository.py', 'def expand_abbreviations', 4),
    ('cookiecutter/environment.py', 'def _read_extensions', 4),
    ('cookiecutter/exceptions.py', 'class CookiecutterException', 6),
    ('cookiecutter/vcs.py', 'def is_vcs_installed', 4),
]


def analisis_estatico():
    carpeta = copia_limpia('01_analisis')
    proyecto = abrir_proyecto(carpeta)
    lineas = ['# Análisis estático con Rope %s' % rope.VERSION, '']

    lineas += ['## find_errors (rope.contrib.finderrors)', '',
               '| Módulo | Errores reportados |', '|---|---|']
    errores_totales = []
    for archivo in sorted((carpeta / 'cookiecutter').glob('*.py')):
        rel = archivo.relative_to(carpeta).as_posix()
        errores = finderrors.find_errors(proyecto, proyecto.get_resource(rel))
        errores_totales += [(rel, e.lineno, e.error) for e in errores]
        lineas.append('| `%s` | %d |' % (rel, len(errores)))
    lineas.append('')
    for rel, lineno, error in errores_totales:
        lineas.append('- `%s:%d` — %s' % (rel, lineno, error))
    if errores_totales:
        lineas.append('')

    lineas += ['## find_occurrences (rope.contrib.findit)', '']
    ocurrencias = {}
    for rel, marcador, desp in SIMBOLOS:
        recurso = proyecto.get_resource(rel)
        offset = offset_de(recurso, marcador, desp)
        nombre = re.match(r'\w+', recurso.read()[offset:]).group(0)
        encontradas = findit.find_occurrences(proyecto, recurso, offset)
        ocurrencias[nombre] = len(encontradas)
        lineas.append('### `%s` (%d ocurrencias)' % (nombre, len(encontradas)))
        lineas.append('')
        for o in encontradas:
            lineas.append('- `%s:%d`%s' % (o.resource.path, o.lineno,
                                          ' (dudosa)' if o.unsure else ''))
        lineas.append('')

    lineas += ['## find_definition (rope.contrib.findit)', '']
    recurso = proyecto.get_resource('cookiecutter/generate.py')
    offset = offset_de(recurso, 'env = create_env_with_context(context)', 6)
    definicion = findit.find_definition(proyecto, recurso.read(), offset, recurso)
    lineas.append('Desde `cookiecutter/generate.py` (`create_env_with_context(context)`) '
                  'Rope resuelve la definición en `%s:%d`.'
                  % (definicion.resource.path, definicion.lineno))
    lineas.append('')

    proyecto.close()
    (RESULTADOS / '01_analisis_estatico.md').write_text('\n'.join(lineas))
    print('[analisis] errores=%d ocurrencias=%s' % (len(errores_totales), ocurrencias))
    return {'errores': len(errores_totales), 'ocurrencias': ocurrencias,
            'definicion': '%s:%d' % (definicion.resource.path, definicion.lineno)}


# ---------------------------------------------------------------------------
# 3. Refactorizaciones
# ---------------------------------------------------------------------------
# Cada función recibe el proyecto Rope y devuelve un objeto ChangeSet.

def ref_rename_funcion(p):
    r = p.get_resource('cookiecutter/utils.py')
    return Rename(p, r, offset_de(r, 'def create_env_with_context', 4)).get_changes('create_jinja_env')


def ref_rename_funcion_usada_en_tests(p):
    r = p.get_resource('cookiecutter/repository.py')
    return Rename(p, r, offset_de(r, 'def expand_abbreviations', 4)).get_changes('expand_template_abbreviations')


def ref_rename_metodo(p):
    r = p.get_resource('cookiecutter/environment.py')
    return Rename(p, r, offset_de(r, 'def _read_extensions', 4)).get_changes('_extensions_from_context')


def ref_rename_clase(p):
    r = p.get_resource('cookiecutter/exceptions.py')
    return Rename(p, r, offset_de(r, 'class CookiecutterException', 6)).get_changes('CookiecutterError')


def ref_rename_parametro(p):
    r = p.get_resource('cookiecutter/hooks.py')
    return Rename(p, r, offset_de(r, "def run_script(script_path: str, cwd", 33)).get_changes('working_dir')


def ref_extract_newline(p):
    # Bloque de generate_file que decide el carácter de fin de línea.
    r = p.get_resource('cookiecutter/generate.py')
    inicio = inicio_de_linea(r, "    if context['cookiecutter'].get('_new_lines', False):")
    fin = linea_anterior(r, inicio_de_linea(r, "    logger.debug('Writing contents to file %s', outfile)"))
    return ExtractMethod(p, r, inicio, fin).get_changes('_detect_newline')


def ref_extract_contexto(p):
    # Bloque if/else de cookiecutter() que arma el contexto (2 valores de salida:
    # context y context_for_prompting).
    r = p.get_resource('cookiecutter/main.py')
    inicio = inicio_de_linea(r, '    if replay:\n        context = generate_context(')
    fin = inicio_de_linea(r, '    # preserve the original cookiecutter options')
    return ExtractMethod(p, r, inicio, fin).get_changes('_build_context')


def ref_extract_con_continue(p):
    # Bloque dentro del for de generate_files que termina en `continue`:
    # caso límite (flujo de control que salta fuera del bloque).
    r = p.get_resource('cookiecutter/generate.py')
    inicio = inicio_de_linea(r, '                if is_copy_only_path(infile, context):')
    fin = inicio_de_linea(r, '                try:\n                    generate_file(')
    return ExtractMethod(p, r, inicio, fin).get_changes('_copy_file_without_rendering')


def ref_extract_bucle(p):
    # Bucle de copia de directorios sin renderizar (lee 5 variables locales,
    # no produce valores de salida).
    r = p.get_resource('cookiecutter/generate.py')
    inicio = inicio_de_linea(r, '            for copy_dir in copy_dirs:')
    fin = linea_anterior(r, inicio_de_linea(r, '            # We mutate ``dirs``'))
    return ExtractMethod(p, r, inicio, fin).get_changes('_copy_dirs_without_rendering')


def ref_inline_funcion(p):
    r = p.get_resource('cookiecutter/config.py')
    return create_inline(p, r, offset_de(r, 'def _expand_path', 4)).get_changes()


def ref_move_funcion(p):
    r = p.get_resource('cookiecutter/utils.py')
    destino = p.get_resource('cookiecutter/hooks.py')
    return create_move(p, r, offset_de(r, 'def make_executable', 4)).get_changes(destino)


def ref_rename_parcheada(p):
    # Los tests hacen mocker.patch('cookiecutter.vcs.is_vcs_installed', ...):
    # la referencia está en un string y Rope no la ve.
    r = p.get_resource('cookiecutter/vcs.py')
    return Rename(p, r, offset_de(r, 'def is_vcs_installed', 4)).get_changes('is_vcs_available')


def ref_rename_parcheada_docs(p):
    # Igual que 13, pero con docs=True: Rope también renombra en strings y
    # comentarios.
    r = p.get_resource('cookiecutter/vcs.py')
    return Rename(p, r, offset_de(r, 'def is_vcs_installed', 4)).get_changes('is_vcs_available', docs=True)


def ref_rename_espiada(p):
    # Los tests hacen mocker.spy(replay, 'get_file_name'): nombre en un string.
    r = p.get_resource('cookiecutter/replay.py')
    return Rename(p, r, offset_de(r, 'def get_file_name', 4)).get_changes('get_replay_file_path')


REFACTORIZACIONES = [
    ('02_rename_funcion', 'Rename', 'utils.create_env_with_context -> create_jinja_env (usada en 3 módulos y en tests)', ref_rename_funcion),
    ('03_rename_funcion_importada', 'Rename', 'repository.expand_abbreviations -> expand_template_abbreviations (también importada por los tests)', ref_rename_funcion_usada_en_tests),
    ('04_rename_metodo', 'Rename', 'ExtensionLoaderMixin._read_extensions -> _extensions_from_context', ref_rename_metodo),
    ('05_rename_clase', 'Rename', 'exceptions.CookiecutterException -> CookiecutterError (clase base de 17 subclases)', ref_rename_clase),
    ('06_rename_parametro', 'Rename', 'parámetro cwd de hooks.run_script -> working_dir', ref_rename_parametro),
    ('07_extract_newline', 'Extract Method', 'bloque de detección de fin de línea de generate_file -> _detect_newline', ref_extract_newline),
    ('08_extract_contexto', 'Extract Method', 'bloque if/else que arma el contexto en main.cookiecutter -> _build_context (2 valores de salida)', ref_extract_contexto),
    ('09_extract_con_continue', 'Extract Method', 'bloque que termina en `continue` dentro del for de generate_files -> _copy_file_without_rendering (caso límite)', ref_extract_con_continue),
    ('10_extract_bucle', 'Extract Method', 'bucle de copia de directorios de generate_files -> _copy_dirs_without_rendering', ref_extract_bucle),
    ('11_inline_funcion', 'Inline', 'inline de config._expand_path en get_config (2 llamadas)', ref_inline_funcion),
    ('12_move_funcion', 'Move', 'mover utils.make_executable a hooks', ref_move_funcion),
    ('13_rename_parcheada', 'Rename', "vcs.is_vcs_installed -> is_vcs_available (los tests la parchean con mocker.patch('cookiecutter.vcs.is_vcs_installed'))", ref_rename_parcheada),
    ('14_rename_parcheada_docs', 'Rename', 'igual que 13 pero con docs=True (renombra también en strings y comentarios)', ref_rename_parcheada_docs),
    ('15_rename_espiada', 'Rename', "replay.get_file_name -> get_replay_file_path (los tests usan mocker.spy(replay, 'get_file_name'))", ref_rename_espiada),
]


def aplicar(nombre, tipo, descripcion, funcion, base):
    carpeta = copia_limpia(nombre)
    proyecto = abrir_proyecto(carpeta)
    fila = {'id': nombre, 'tipo': tipo, 'descripcion': descripcion}
    t0 = time.perf_counter()
    try:
        cambios = funcion(proyecto)
        proyecto.do(cambios)
    except Exception as e:
        fila['tiempo_rope_s'] = round(time.perf_counter() - t0, 3)
        fila['estado_rope'] = 'error: %s: %s' % (type(e).__name__, e)
        fila['veredicto'] = 'RECHAZADA POR ROPE'
        (RESULTADOS / (nombre + '_error.txt')).write_text(traceback.format_exc())
        proyecto.close()
        print('[%s] Rope rechazó: %s' % (nombre, fila['estado_rope']))
        return fila
    fila['tiempo_rope_s'] = round(time.perf_counter() - t0, 3)
    fila['estado_rope'] = 'aplicada'
    fila['archivos_modificados'] = sorted(r.path for r in cambios.get_changed_resources())
    proyecto.close()
    (RESULTADOS / (nombre + '.diff')).write_text(cambios.get_description())

    resumen, salida = correr_pytest(carpeta)
    (RESULTADOS / (nombre + '_pytest.txt')).write_text(salida)
    fila['tests'] = resumen
    igual = (resumen['passed'] == base['passed'] and resumen['failed'] == 0
             and resumen['errors'] == 0)
    fila['veredicto'] = 'COMPORTAMIENTO PRESERVADO' if igual else 'ROMPE TESTS'
    print('[%s] %s  %s' % (nombre, fila['veredicto'], resumen))
    return fila


# ---------------------------------------------------------------------------
# Reporte
# ---------------------------------------------------------------------------

def escribir_resumen(base, analisis, filas):
    lineas = [
        '# Resumen de pruebas con Rope (Cookiecutter)', '',
        '- Python: `%s`' % sys.version.split()[0],
        '- Rope: `%s`' % rope.VERSION,
        '- Fecha: %s' % time.strftime('%Y-%m-%d %H:%M'), '',
        '## Línea base', '',
        '%(passed)d passed, %(failed)d failed, %(skipped)d skipped, %(errors)d errors' % base, '',
        '## Refactorizaciones', '',
        '| # | Tipo | Descripción | Rope | Tiempo (s) | Tests (passed/failed/errors) | Veredicto |',
        '|---|---|---|---|---|---|---|',
    ]
    for f in filas:
        t = f.get('tests')
        tests = '%d / %d / %d' % (t['passed'], t['failed'], t['errors']) if t else '—'
        lineas.append('| %s | %s | %s | %s | %s | %s | **%s** |' % (
            f['id'], f['tipo'], f['descripcion'], f['estado_rope'],
            f['tiempo_rope_s'], tests, f['veredicto']))
    lineas.append('')
    (RESULTADOS / 'resumen.md').write_text('\n'.join(lineas))
    (RESULTADOS / 'resumen.json').write_text(json.dumps(
        {'python': sys.version.split()[0], 'rope': rope.VERSION,
         'linea_base': base, 'analisis': analisis, 'refactorizaciones': filas},
        indent=2, ensure_ascii=False))


def main():
    RESULTADOS.mkdir(exist_ok=True)
    for viejo in RESULTADOS.iterdir():
        viejo.unlink()
    base = linea_base()
    analisis = analisis_estatico()
    filas = [aplicar(*r, base=base) for r in REFACTORIZACIONES]
    escribir_resumen(base, analisis, filas)
    print('\nResultados en %s' % RESULTADOS)


if __name__ == '__main__':
    main()
