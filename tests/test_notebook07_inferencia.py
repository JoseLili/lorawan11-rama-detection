"""Run All del notebook piloto no debe entrenar con su configuracion por defecto."""

import ast
import json
from pathlib import Path


def celdas():
    path = Path(__file__).resolve().parents[1] / 'notebooks/07_multiestacion.ipynb'
    notebook = json.loads(path.read_text())
    return [''.join(c['source']) for c in notebook['cells'] if c['cell_type'] == 'code']


def test_flags_opt_in():
    asignaciones = {
        t.id: node.value.value
        for node in ast.walk(ast.parse(celdas()[0]))
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant)
        for t in node.targets if isinstance(t, ast.Name)
    }
    for nombre in ['REENTRENAR', 'EJECUTAR_HISTORICOS',
                   'EJECUTAR_MULTIESTACION', 'GENERAR_FIGURAS_HISTORICAS']:
        assert asignaciones[nombre] is False


def test_todos_los_entrenamientos_requieren_flag():
    llamadas = []

    def exige_reentrenar(test):
        return (isinstance(test, ast.Name) and test.id == 'REENTRENAR') or (
            isinstance(test, ast.BoolOp) and isinstance(test.op, ast.And)
            and any(exige_reentrenar(v) for v in test.values))

    def visitar(node, protegido=False):
        if isinstance(node, ast.If):
            visitar(node.test, protegido)
            for child in node.body:
                visitar(child, protegido or exige_reentrenar(node.test))
            for child in node.orelse:
                visitar(child, protegido)
            return
        if isinstance(node, ast.Call):
            nombre = (node.func.id if isinstance(node.func, ast.Name)
                      else node.func.attr if isinstance(node.func, ast.Attribute) else '')
            if nombre in ('construir_modelo', 'entrenar', 'fit', 'save', 'savez_compressed'):
                llamadas.append(nombre)
                assert protegido, f'{nombre} no protegido por REENTRENAR'
        for child in ast.iter_child_nodes(node):
            visitar(child, protegido)

    for source in celdas():
        visitar(ast.parse(source))
    assert 'entrenar' in llamadas and 'save' in llamadas


def test_carga_explicita_y_umbral_guardado():
    source = '\n'.join(celdas())
    assert "keras.models.load_model('../results/modelo4_lstm.keras', compile=False)" in source
    assert "Path('../results/umbral_p95_cca.txt').read_text()" in source
    assert 'No se reentrena automaticamente' in source
