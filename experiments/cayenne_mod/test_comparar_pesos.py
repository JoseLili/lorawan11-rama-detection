"""Comprobaciones del protocolo y de la equivalencia con los formatos previos."""

from itertools import combinations
import numpy as np
import pytest

from experiments.cayenne_mod.comparar_pesos import (
    FORMATOS, PESOS, codificar, decodificar, evaluar, mascaras,
)
from src.encoding.cayenne import encode_o3, decode_o3, flip_bit


@pytest.mark.parametrize("formato", FORMATOS)
def test_recuperacion_y_equivalencia_con_formato_previo(formato):
    for valor in range(256):
        palabra = codificar(valor, formato)
        assert decodificar(palabra, formato) == valor
        if formato == "actual":
            assert palabra == int.from_bytes(encode_o3(valor)[2:], "big")
            for bit in range(16):
                assert decodificar(palabra ^ (1 << bit), formato) == decode_o3(flip_bit(encode_o3(valor), bit))
        if formato == "v1":
            assert palabra == valor | (((valor >> 5) & 1) << 8)


@pytest.mark.parametrize("formato", ("v1", "v2"))
def test_peso_de_cada_flip_y_reservados(formato):
    for valor in range(256):
        palabra = codificar(valor, formato)
        for bit, peso in enumerate(PESOS[formato]):
            assert abs(decodificar(palabra ^ (1 << bit), formato) - valor) == peso
        for bit in range(len(PESOS[formato]), 16):
            assert decodificar(palabra ^ (1 << bit), formato) is None
    # Los patrones discordantes son válidos; se suman, no se corrigen.
    assert decodificar(1 << 8, formato) == 16


def test_ejemplos_y_dos_flips_no_se_cancelan():
    for valor, esperado in [(147, 163), (160, 144), (175, 159)]:
        assert decodificar(codificar(valor, "v1") ^ (1 << 5), "v1") == esperado
    assert decodificar(codificar(160, "v1") ^ (1 << 5) ^ (1 << 8), "v1") == 128
    assert decodificar(32768, "actual") == -32768
    assert decodificar(32768, "binario_8_control") is None
    assert decodificar(256, "binario_8_control") is None


@pytest.mark.parametrize("formato", FORMATOS)
@pytest.mark.parametrize("presupuesto", (1, 2))
def test_conteos_agrupados_contra_mensajes_individuales(formato, presupuesto):
    # Duplicados, frontera exacta y ambos sentidos. El oráculo enumera mensajes,
    # no agrupa histogramas como la implementación.
    mensajes = [0, 147, 147, 154, 155, 160, 175, 255]
    hist = np.bincount(mensajes, minlength=256)
    resultado, detalle = evaluar(hist, formato, presupuesto)
    arriba = abajo = rechazados = 0
    for valor in mensajes:
        for bits in combinations(range(16), presupuesto):
            recibido = decodificar(codificar(valor, formato) ^ sum(1 << b for b in bits), formato)
            if recibido is None:
                rechazados += 1
            else:
                arriba += valor < 155 <= recibido
                abajo += recibido < 155 <= valor
    assert resultado["cruces_arriba"] == arriba
    assert resultado["cruces_abajo"] == abajo
    assert resultado["rechazos"] == rechazados
    assert resultado["n_sobre_umbral"] == 4
    assert resultado["n_escenarios"] == len(mensajes) * (16 if presupuesto == 1 else 120)
    assert resultado["pct_cruces_peor_mascara_fija"] == detalle.pct_cruces.max()


def test_presupuestos_distintos_y_denominador_sin_eventos_altos():
    assert len(mascaras(1)[1]) == 16
    assert len(set(mascaras(2)[1])) == 120
    assert all(int(m).bit_count() == 2 for m in mascaras(2)[1])
    resultado, _ = evaluar(np.bincount([0, 1], minlength=256), "v2", 1)
    assert np.isnan(resultado["pct_abajo_dado_alto"])
    with pytest.raises(ValueError):
        codificar(256, "v2")
    with pytest.raises(ValueError):
        evaluar(np.zeros(256), "v2", 1)
