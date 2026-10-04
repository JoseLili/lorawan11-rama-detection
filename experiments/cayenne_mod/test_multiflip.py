from itertools import combinations
from math import comb

import numpy as np
import pandas as pd

from experiments.cayenne_mod.multiflip import (
    GRUPO_8, TIPOS, construir_efectos, enumerar, tabla_decodificada,
    validar_mascaras_cifradas,
)
from experiments.cayenne_mod.selectiva_red import codificar, decodificar
from src.decision.nom172 import banda_o3
from src.detect.red import contexto_diario


def recibido(original, bits, formato="B"):
    p = bytearray(codificar(original, formato))
    for bit in bits:
        p[3-bit//8] ^= 1 << (bit % 8)
    return decodificar(bytes(p), formato)


def contexto():
    m = pd.DataFrame({"CCA": [60.,28.], "AJM": [45.,45.]},
                     index=pd.to_datetime(["2025-01-01","2025-01-02"]))
    c = contexto_diario(m)
    c["base_ppb"] = c["perfil_ppb"] = 0.
    c["predicho_ppb"] = [40.,45.,32.,45.]
    c["umbral_ppb"] = 15.
    c["evaluable"] = True
    return c


def test_cancelacion_depende_del_original_y_de_las_posiciones():
    assert recibido(28,(3,11)) == 28
    assert recibido(60,(3,11)) == 44
    assert recibido(60,(5,9,10,11)) == 28
    assert sum(recibido(28,bits)==28 for bits in combinations(GRUPO_8,2)) == 12
    for n in range(1,8):
        for bits in combinations(GRUPO_8,n):
            assert recibido(60,bits) == 60-8*n
            if n % 2:
                assert recibido(28,bits) != 28


def test_lookup_coincide_con_decodificacion_incluso_fragmentos_parciales():
    for formato in ("base","A","B"):
        lookup = tabla_decodificada(formato)
        for palabra, valor in enumerate(lookup):
            assert decodificar(bytes([1,2])+palabra.to_bytes(2,"big"),formato) == valor


def test_compresion_coincide_con_ataques_individuales_y_maximo_diario():
    c = contexto()
    h,f,_ = construir_efectos(c,True)
    posiciones = (3,5,11)
    resumen = enumerar(h,f,(("prueba","B",posiciones),))["resumen"]
    for row in resumen.itertuples():
        cuentas = dict.fromkeys(h,0)
        cancelaciones = alertas_canceladas = 0
        for bits in combinations(posiciones,row.n_flips):
            for msg in c.itertuples():
                r = recibido(int(msg.original_ppb),bits)
                nuevo_max = max(msg.maximo_otros_ppb,r)
                alerta = abs(r-msg.predicho_ppb)>msg.umbral_ppb
                dano = {
                    "cambio_banda_red": banda_o3(np.array([nuevo_max]))[0] != banda_o3(np.array([msg.maximo_original_ppb]))[0],
                    "falsa_fase1": msg.maximo_original_ppb<155<=nuevo_max,
                    "anulada_fase1": nuevo_max<155<=msg.maximo_original_ppb,
                }
                for t in TIPOS:
                    cuentas[t] += int(dano[t])
                    cuentas[t+"_no_detectado"] += int(dano[t] and not alerta)
                grande = abs(r-msg.original_ppb)>msg.umbral_ppb
                cuentas["alertas"] += int(alerta)
                cuentas["amplitud_supera_p95"] += int(grande)
                cuentas["amplitud_supera_p95_sin_alerta"] += int(grande and not alerta)
                cancelaciones += int(r==msg.original_ppb)
                alertas_canceladas += int(r==msg.original_ppb and alerta)
        for nombre, cuenta in cuentas.items():
            assert getattr(row,nombre) == cuenta
        assert row.cancelaciones == cancelaciones
        assert row.alertas_sin_cambio_valor == alertas_canceladas
        assert row.n_escenarios == len(c)*comb(len(posiciones),row.n_flips)
        assert row.cambio_banda_red_esperados == cuentas["cambio_banda_red"]/row.n_mascaras


def test_rechazos_no_se_cuentan_como_alertas_ni_cancelaciones():
    h,f,_ = construir_efectos(contexto(),True)
    r = enumerar(h,f)["resumen"]
    for row in r.query("alcance == 'campo_16'").itertuples():
        activos = {"base":8,"A":10,"B":12}[row.formato]
        assert row.mascaras_aceptadas == comb(activos,row.n_flips)
        assert row.rechazos == row.n_mensajes*(comb(16,row.n_flips)-comb(activos,row.n_flips))
        if row.n_flips>activos:
            assert row.pct_rechazos==100
            assert row.alertas==row.cancelaciones==0
            assert np.isnan(row.pct_alerta_aceptados)
            assert np.isnan(row.cambio_banda_red_escape_pct_aceptados)


def test_cifrado_enumerado():
    assert validar_mascaras_cifradas() == 9*65535
