import numpy as np
import pandas as pd
import pytest

from experiments.cayenne_mod.selectiva_red import (
    FORMATOS, PESOS, codificar, decodificar, tabla_recibidos,
    evaluar_posicion, resumir, validar_cifrado,
)
from src.encoding.cayenne import encode_o3
from src.detect.red import contexto_diario
from src.decision.nom172 import banda_o3


@pytest.mark.parametrize("formato", FORMATOS)
def test_recuperacion_y_peso_exhaustivo(formato):
    tabla = tabla_recibidos(formato)
    for valor in range(256):
        p = codificar(valor, formato)
        assert len(p) == 4 and decodificar(p, formato) == valor
        if formato == "base":
            assert p == encode_o3(valor)
        for bit, peso in enumerate(PESOS[formato]):
            assert abs(tabla[valor, bit] - valor) == peso
        assert np.isnan(tabla[valor, len(PESOS[formato]):]).all()


def test_propuestas_exactas_y_fragmentos_discordantes():
    assert codificar(16, "A")[2:] == bytes.fromhex("01 10")
    assert codificar(32, "A")[2:] == bytes.fromhex("02 20")
    assert codificar(32, "B")[2:] == bytes.fromhex("0e 20")
    # Patrón parcial tras ataque admitido; no se incorpora otra contramedida.
    assert decodificar(bytes.fromhex("01 02 00 20"), "A") == 16
    assert decodificar(bytes.fromhex("01 02 00 20"), "B") == 8
    for formato in FORMATOS:
        assert PESOS[formato][6:8] == (64, 128)


def test_cadena_cifrada_completa():
    assert validar_cifrado() == 3 * 256 * 16


def contexto():
    m = pd.DataFrame({"CCA": [160., 100., 154., 70.], "AJM": [159., 90., 80., 72.]},
                     index=pd.to_datetime(["2025-01-01 00:00", "2025-01-01 01:00",
                                           "2025-01-02 00:00", "2025-01-02 01:00"]))
    c = contexto_diario(m)
    c["base_ppb"] = c["perfil_ppb"] = 0.
    c["predicho_ppb"] = c.original_ppb
    c["umbral_ppb"] = 12.
    c["evaluable"] = True
    return m, c


@pytest.mark.parametrize("formato", FORMATOS)
def test_dano_y_deteccion_contra_reemplazo_literal(formato):
    m, c = contexto()
    for bit in range(16):
        e = evaluar_posicion(c, tabla_recibidos(formato), bit, True)
        for i, r in c.iterrows():
            rec = e.loc[i, "recibido_ppb"]
            if np.isnan(rec):
                assert not e.loc[i, ["aceptado", "detectado", "cambio_banda_red", "falsa_fase1", "anulada_fase1"]].any()
                continue
            dia = m.loc[m.index.normalize() == r.fecha].copy()
            dia.loc[r.timestamp, r.estacion] = rec
            nuevo = float(dia.max().max())
            assert e.loc[i, "cambio_banda_red"] == (banda_o3(nuevo) != banda_o3(r.maximo_original_ppb))
            assert e.loc[i, "falsa_fase1"] == (r.maximo_original_ppb < 155 <= nuevo)
            assert e.loc[i, "anulada_fase1"] == (nuevo < 155 <= r.maximo_original_ppb)
            assert e.loc[i, "detectado"] == (abs(rec-r.original_ppb) > 12)


def test_union_diaria_y_comparacion_pareada():
    _, c = contexto()
    resultados = resumir(c, True)
    for formato in FORMATOS:
        for tipo in ["cambio_banda_red", "falsa_fase1", "anulada_fase1"]:
            s = resultados["resumen"].query("formato == @formato and tipo_dano == @tipo").iloc[0]
            p = resultados["pareados"].query("formato == @formato and tipo_dano == @tipo")
            assert s.n_escenarios == 16 * len(c)
            assert s.daninos_no_detectados == p.escapan_candidata.sum()
            assert (p.escapan_candidata == p.escapan_base - p.eliminados + p.nuevos).all()
            d = resultados["por_dia"].query("formato == @formato and tipo_dano == @tipo")
            assert s.dias_escape_union == d.groupby("fecha").escape.any().sum()


def test_validaciones_y_ausencia_de_modelo():
    with pytest.raises(ValueError):
        codificar(256, "B")
    with pytest.raises(ValueError):
        codificar(-1, "A")
    _, c = contexto()
    c.loc[0, "evaluable"] = False
    with pytest.raises(ValueError, match="sin modelo"):
        evaluar_posicion(c, tabla_recibidos("A"), 4, True)
    c.loc[0, "original_ppb"] = 256
    with pytest.raises(ValueError, match="Originales"):
        evaluar_posicion(c, tabla_recibidos("A"), 4, False)
