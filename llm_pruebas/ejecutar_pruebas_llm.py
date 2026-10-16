"""Pruebas de Cookiecutter con un LLM (refactorización con un prompt general).

Réplica del experimento hecho sobre PySnooper (../PySnooper_tesis/llm_pruebas).
A diferencia de rope_pruebas/, aquí NO se le indica al modelo qué
refactorización hacer: recibe un prompt general (prompt_v1.md) y decide él
mismo qué cambiar en cada módulo.

Flujo:
  1. Línea base: corre la suite de tests original de Cookiecutter.
  2. Para cada módulo y cada corrida: se envía el prompt + el paquete
     completo como contexto, se extrae el archivo refactorizado, se aplica
     sobre una copia limpia del proyecto, se guarda el diff, se compara la
     API pública (con ast) y se vuelve a correr la suite de tests.
  3. Se escribe un resumen (tests, tipo de fallo, API, tokens, costo,
     determinismo).

El código original en ../cookiecutter NUNCA se modifica. Cada ejecución se
guarda en resultados/<fecha_hora>/ para no sobrescribir corridas pagadas.

Uso (desde la raíz del repositorio, con ANTHROPIC_API_KEY exportada):
    .venv/bin/python llm_pruebas/ejecutar_pruebas_llm.py
    .venv/bin/python llm_pruebas/ejecutar_pruebas_llm.py --corridas 5 --modulos utils main
    .venv/bin/python llm_pruebas/ejecutar_pruebas_llm.py --dry-run
"""
import argparse
import ast
import difflib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import anthropic

AQUI = Path(__file__).resolve().parent
REPO = AQUI.parent
PAQUETE = REPO / 'cookiecutter'
TRABAJO = AQUI / '_trabajo'
RESULTADOS = AQUI / 'resultados'
PYTHON = sys.executable
PROMPT = AQUI / 'prompt_v1.md'

MODULOS = sorted(p.stem for p in PAQUETE.glob('*.py'))

IGNORAR = shutil.ignore_patterns(
    '.git', '.github', '.venv', '.pytest_cache', '*.egg-info', '__pycache__',
    '.ropeproject', 'rope_pruebas', 'llm_pruebas', 'docs', 'logo',
)

# USD por millón de tokens: (input, output, escritura de caché, lectura de caché)
PRECIOS = {
    'claude-opus-5-5': (4.00, 20.00, 5.00, 0.20),
    'claude-sonnet-5-5': (2.00, 10.00, 2.50, 0.20),
    'claude-fable-5-1': (10.00, 50.00, 12.50, 0.25),
}


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


def correr_pytest(carpeta):
    """Corre pytest en `carpeta` y devuelve (resumen, salida completa)."""
    # PYTHONPATH tapa la instalación editable del .venv (que apunta al
    # repositorio original); -o addopts= desactiva el --cov de pyproject.toml.
    env = dict(os.environ, PYTHONPATH=str(carpeta))
    proc = subprocess.run(
        [PYTHON, '-m', 'pytest', 'tests', '-q', '-rs', '-p', 'no:cacheprovider',
         '-o', 'addopts='],
        cwd=carpeta, capture_output=True, text=True, env=env,
    )
    salida = proc.stdout + proc.stderr
    resumen = {'returncode': proc.returncode}
    for clave in ('passed', 'failed', 'skipped', 'error', 'errors'):
        m = re.search(r'(\d+) ' + clave + r'\b', salida)
        resumen[clave] = int(m.group(1)) if m else 0
    resumen['errors'] += resumen.pop('error')
    return resumen, salida


def contexto_paquete():
    """Todos los módulos de cookiecutter/ como bloques <archivo>."""
    partes = []
    for ruta in sorted(PAQUETE.glob('*.py')):
        rel = ruta.relative_to(REPO).as_posix()
        partes.append('<archivo ruta="%s">\n%s\n</archivo>' % (rel, ruta.read_text()))
    return 'Código actual del paquete cookiecutter:\n\n' + '\n\n'.join(partes)


def extraer_codigo(texto):
    """Devuelve el bloque ```python más largo de la respuesta (o None)."""
    bloques = re.findall(r'```(?:python|py)?[ \t]*\n(.*?)```', texto, re.DOTALL)
    return max(bloques, key=len) if bloques else None


def costo(modelo, uso):
    precios = PRECIOS.get(modelo)
    if not precios:
        return None
    p_in, p_out, p_cw, p_cr = precios
    return round((uso['input'] * p_in + uso['output'] * p_out
                  + uso['cache_write'] * p_cw + uso['cache_read'] * p_cr) / 1e6, 4)


def clasificar_fallo(codigo, salida_pytest):
    try:
        compile(codigo, '<llm>', 'exec')
    except SyntaxError as e:
        return 'sintaxis: %s' % e
    if re.search(r'ImportError|cannot import name|has no attribute|'
                 r'error(s)? during collection', salida_pytest):
        return 'API rota (import/atributo)'
    return 'comportamiento'


def api_publica(codigo):
    """Nombres públicos de nivel de módulo y firmas de funciones/métodos públicos.

    Devuelve {nombre: firma} donde firma es la lista de parámetros (o 'valor'
    para asignaciones e imports, 'clase' para clases).
    """
    def firma(nodo):
        a = nodo.args
        partes = [p.arg for p in a.posonlyargs] + ['/'] * bool(a.posonlyargs)
        partes += [p.arg for p in a.args]
        partes += ['*' + a.vararg.arg] if a.vararg else (['*'] if a.kwonlyargs else [])
        partes += [p.arg for p in a.kwonlyargs]
        partes += ['**' + a.kwarg.arg] if a.kwarg else []
        return '(%s)' % ', '.join(partes)

    api = {}
    for nodo in ast.parse(codigo).body:
        if isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef)):
            api[nodo.name] = firma(nodo)
        elif isinstance(nodo, ast.ClassDef):
            api[nodo.name] = 'clase'
            for hijo in nodo.body:
                if (isinstance(hijo, (ast.FunctionDef, ast.AsyncFunctionDef))
                        and (not hijo.name.startswith('_') or hijo.name.startswith('__'))):
                    api['%s.%s' % (nodo.name, hijo.name)] = firma(hijo)
        elif isinstance(nodo, (ast.Assign, ast.AnnAssign)):
            objetivos = nodo.targets if isinstance(nodo, ast.Assign) else [nodo.target]
            for t in objetivos:
                if isinstance(t, ast.Name):
                    api[t.id] = 'valor'
        elif isinstance(nodo, (ast.Import, ast.ImportFrom)):
            for alias in nodo.names:
                api[(alias.asname or alias.name).split('.')[0]] = 'import'
    return {k: v for k, v in api.items() if not k.split('.')[0].startswith('_')}


def cambios_api(original, nuevo):
    """Lista de cambios en la API pública: eliminados y firmas distintas."""
    try:
        antes, despues = api_publica(original), api_publica(nuevo)
    except SyntaxError:
        return ['(no se pudo analizar: error de sintaxis)']
    cambios = []
    for nombre, f in sorted(antes.items()):
        if nombre not in despues:
            cambios.append('eliminado %s %s' % (f, nombre))
        elif despues[nombre] != f:
            cambios.append('firma %s: %s -> %s' % (nombre, f, despues[nombre]))
    return cambios


# ---------------------------------------------------------------------------
# Llamada al LLM
# ---------------------------------------------------------------------------

def es_error_de_red(e):
    # Un corte a mitad del streaming llega como excepción cruda de httpx, sin
    # envolver en anthropic.APIConnectionError.
    return (isinstance(e, (anthropic.APIConnectionError, OSError))
            or type(e).__module__.split('.')[0].startswith('httpx'))


def pedir_con_reintentos(cliente, args, sistema, contexto, modulo, intentos=4):
    """Como pedir_refactorizacion, pero reintenta ante errores de red."""
    for intento in range(1, intentos + 1):
        try:
            texto, meta = pedir_refactorizacion(cliente, args, sistema, contexto, modulo)
            meta['intentos'] = intento
            return texto, meta
        except Exception as e:
            if not es_error_de_red(e) or intento == intentos:
                raise
            espera = 30 * intento
            print('[%s] error de red (%s: %s), reintento %d en %ds'
                  % (modulo, type(e).__name__, e, intento, espera))
            time.sleep(espera)


def pedir_refactorizacion(cliente, args, sistema, contexto, modulo):
    """Envía el prompt general para `modulo` y devuelve (texto, metadatos)."""
    t0 = time.perf_counter()
    with cliente.beta.messages.stream(
        model=args.modelo,
        max_tokens=64000,
        system=sistema,
        output_config={'effort': args.effort},
        # Si el modelo rechaza la petición, la API la reintenta con otro
        # modelo; se registra en `modelo_respuesta` para poder detectarlo.
        betas=['server-side-fallback-2026-07-01'],
        fallbacks='default',
        messages=[{'role': 'user', 'content': [
            # Prefijo idéntico en todas las llamadas -> se reutiliza la caché.
            {'type': 'text', 'text': contexto, 'cache_control': {'type': 'ephemeral'}},
            {'type': 'text', 'text': 'Refactoriza el archivo `cookiecutter/%s.py`.' % modulo},
        ]}],
    ) as stream:
        respuesta = stream.get_final_message()
    texto = ''.join(b.text for b in respuesta.content if b.type == 'text')
    u = respuesta.usage
    uso = {
        'input': u.input_tokens,
        'output': u.output_tokens,
        'cache_write': u.cache_creation_input_tokens or 0,
        'cache_read': u.cache_read_input_tokens or 0,
    }
    meta = {
        'modelo_respuesta': respuesta.model,
        'stop_reason': respuesta.stop_reason,
        'message_id': respuesta.id,
        'tiempo_llm_s': round(time.perf_counter() - t0, 1),
        'tokens': uso,
        'costo_usd': costo(respuesta.model, uso),
    }
    return texto, meta


# ---------------------------------------------------------------------------
# Una corrida
# ---------------------------------------------------------------------------

def corrida(cliente, args, sistema, contexto, modulo, n, base, salida_dir):
    nombre = '%s_run%d' % (modulo, n)
    fila = {'id': nombre, 'modulo': modulo, 'corrida': n}
    try:
        texto, meta = pedir_con_reintentos(cliente, args, sistema, contexto, modulo)
    except anthropic.APIStatusError as e:
        fila['veredicto'] = 'ERROR API %s' % e.status_code
        fila['detalle'] = str(e.message)
        print('[%s] %s' % (nombre, fila['veredicto']))
        return fila
    fila.update(meta)
    (salida_dir / (nombre + '_respuesta.md')).write_text(texto)

    if meta['stop_reason'] == 'refusal':
        fila['veredicto'] = 'RECHAZADA POR EL MODELO'
        print('[%s] %s' % (nombre, fila['veredicto']))
        return fila
    codigo = extraer_codigo(texto)
    if codigo is None:
        fila['veredicto'] = 'SIN CÓDIGO EN LA RESPUESTA'
        print('[%s] %s' % (nombre, fila['veredicto']))
        return fila

    rel = 'cookiecutter/%s.py' % modulo
    original = (REPO / rel).read_text()
    (salida_dir / (nombre + '.py')).write_text(codigo)
    diff = ''.join(difflib.unified_diff(
        original.splitlines(True), codigo.splitlines(True),
        'a/' + rel, 'b/' + rel))
    (salida_dir / (nombre + '.diff')).write_text(diff)
    fila['lineas_agregadas'] = sum(1 for l in diff.splitlines()
                                   if l.startswith('+') and not l.startswith('+++'))
    fila['lineas_eliminadas'] = sum(1 for l in diff.splitlines()
                                    if l.startswith('-') and not l.startswith('---'))
    fila['sin_cambios'] = not diff
    fila['cambios_api_publica'] = cambios_api(original, codigo)

    carpeta = copia_limpia(nombre)
    (carpeta / rel).write_text(codigo)
    resumen, salida = correr_pytest(carpeta)
    (salida_dir / (nombre + '_pytest.txt')).write_text(salida)
    fila['tests'] = resumen
    igual = (resumen['passed'] == base['passed'] and resumen['failed'] == 0
             and resumen['errors'] == 0)
    if igual:
        fila['veredicto'] = 'COMPORTAMIENTO PRESERVADO'
    else:
        fila['veredicto'] = 'ROMPE TESTS'
        fila['tipo_fallo'] = clasificar_fallo(codigo, salida)
    if meta['stop_reason'] == 'max_tokens':
        fila['veredicto'] += ' (respuesta truncada)'
    print('[%s] %s  %s  %ss  $%s  api=%s' % (
        nombre, fila['veredicto'], resumen, meta['tiempo_llm_s'], meta['costo_usd'],
        fila['cambios_api_publica'] or 'sin cambios'))
    return fila


# ---------------------------------------------------------------------------
# Reporte
# ---------------------------------------------------------------------------

def determinismo(filas, salida_dir):
    """Cuántos diffs distintos produjo cada módulo entre sus corridas."""
    res = {}
    for modulo in sorted({f['modulo'] for f in filas}):
        diffs = [(salida_dir / (f['id'] + '.diff')).read_text()
                 for f in filas if f['modulo'] == modulo
                 and (salida_dir / (f['id'] + '.diff')).exists()]
        res[modulo] = {'corridas': len(diffs), 'diffs_distintos': len(set(diffs))}
    return res


def escribir_resumen(args, base, filas, salida_dir):
    det = determinismo(filas, salida_dir)
    total = sum(f.get('costo_usd') or 0 for f in filas)
    lineas = [
        '# Resumen de pruebas con LLM (prompt general) — Cookiecutter', '',
        '- Python: `%s`' % sys.version.split()[0],
        '- SDK anthropic: `%s`' % anthropic.__version__,
        '- Modelo solicitado: `%s` (effort `%s`)' % (args.modelo, args.effort),
        '- Prompt: `%s`' % PROMPT.name,
        '- Corridas por módulo: %d' % args.corridas,
        '- Fecha: %s' % time.strftime('%Y-%m-%d %H:%M'),
        '- Costo total estimado: US$ %.2f' % total, '',
        '## Línea base', '',
        '%(passed)d passed, %(failed)d failed, %(skipped)d skipped, %(errors)d errors' % base, '',
        '## Corridas', '',
        '| Corrida | Modelo | +/− líneas | Tests (passed/failed/errors) | Veredicto | Tipo de fallo | Cambios API pública | Tiempo (s) | Costo (US$) |',
        '|---|---|---|---|---|---|---|---|---|',
    ]
    for f in filas:
        t = f.get('tests')
        tests = '%d / %d / %d' % (t['passed'], t['failed'], t['errors']) if t else '—'
        lineas_diff = ('+%d / −%d' % (f['lineas_agregadas'], f['lineas_eliminadas'])
                       if 'lineas_agregadas' in f else '—')
        api = '; '.join(f.get('cambios_api_publica') or []) or '—'
        lineas.append('| %s | %s | %s | %s | **%s** | %s | %s | %s | %s |' % (
            f['id'], f.get('modelo_respuesta', '—'), lineas_diff, tests,
            f['veredicto'], f.get('tipo_fallo', ''), api, f.get('tiempo_llm_s', '—'),
            f.get('costo_usd', '—')))
    lineas += ['', '## Determinismo', '',
               '| Módulo | Corridas | Diffs distintos |', '|---|---|---|']
    for modulo, d in det.items():
        lineas.append('| %s | %d | %d |' % (modulo, d['corridas'], d['diffs_distintos']))
    lineas += ['', 'Las refactorizaciones que el modelo dice haber aplicado están al final '
               'de cada `<corrida>_respuesta.md`.', '']
    (salida_dir / 'resumen.md').write_text('\n'.join(lineas))
    (salida_dir / 'resumen.json').write_text(json.dumps(
        {'python': sys.version.split()[0], 'anthropic': anthropic.__version__,
         'modelo': args.modelo, 'effort': args.effort, 'prompt': PROMPT.read_text(),
         'linea_base': base, 'determinismo': det, 'costo_total_usd': round(total, 4),
         'corridas': filas},
        indent=2, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--modelo', default='claude-opus-5-5')
    parser.add_argument('--effort', default='high',
                        choices=['low', 'medium', 'high', 'xhigh', 'max'])
    parser.add_argument('--corridas', type=int, default=3)
    parser.add_argument('--modulos', nargs='+', default=MODULOS, choices=MODULOS)
    parser.add_argument('--dry-run', action='store_true',
                        help='muestra el prompt sin llamar a la API')
    parser.add_argument('--reanudar', metavar='CARPETA',
                        help='continúa una ejecución interrumpida en resultados/CARPETA, '
                             'sin repetir (ni volver a pagar) las corridas ya hechas')
    args = parser.parse_args()

    sistema = PROMPT.read_text()
    contexto = contexto_paquete()
    if args.dry_run:
        print('=== SYSTEM ===\n%s\n=== USER ===\n%s\n\nRefactoriza el archivo '
              '`cookiecutter/%s.py`.' % (sistema, contexto, args.modulos[0]))
        return

    cliente = anthropic.Anthropic()
    filas = []
    if args.reanudar:
        salida_dir = RESULTADOS / args.reanudar
        previo = json.loads((salida_dir / 'resumen.json').read_text())
        assert previo['prompt'] == sistema, 'el prompt cambió desde la ejecución original'
        assert (previo['modelo'], previo['effort']) == (args.modelo, args.effort)
        filas = [f for f in previo['corridas'] if not f['veredicto'].startswith('ERROR')]
        print('[reanudar] %d corridas ya hechas en %s' % (len(filas), salida_dir))
    else:
        salida_dir = RESULTADOS / time.strftime('%Y%m%d_%H%M%S')
        salida_dir.mkdir(parents=True)
        (salida_dir / 'prompt.md').write_text(sistema)
    hechas = {f['id'] for f in filas}

    carpeta = copia_limpia('00_linea_base')
    base, salida = correr_pytest(carpeta)
    (salida_dir / '00_linea_base_pytest.txt').write_text(salida)
    print('[linea base] %s' % base)

    for modulo in args.modulos:
        for n in range(1, args.corridas + 1):
            if '%s_run%d' % (modulo, n) in hechas:
                continue
            filas.append(corrida(cliente, args, sistema, contexto, modulo, n, base, salida_dir))
            escribir_resumen(args, base, filas, salida_dir)
    print('\nResultados en %s' % salida_dir)


if __name__ == '__main__':
    main()
