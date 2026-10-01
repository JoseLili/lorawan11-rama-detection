"""Regresion de atacar_serie al trasladarla desde el notebook piloto CCA."""

import numpy as np
import pytest

from src.attack import blind


@pytest.mark.parametrize('bit', range(16))
@pytest.mark.parametrize('tasa', [0.0, 0.05, 1.0])
def test_muestreo_original_y_flip_con_signo(bit, tasa):
    valores = np.tile([np.nan, 0, 43, 128, 155, np.nan, 160, 168], 30)
    original = valores.copy()
    esperado = valores.copy()
    etiquetas = np.zeros(len(valores), dtype=int)
    rng = np.random.default_rng(42)
    # Oraculo independiente: el muestreo omite NaN; XOR sobre el entero
    # debe equivaler a la cadena de cifrado real usada por la funcion.
    for i, valor in enumerate(valores):
        if np.isnan(valor) or rng.random() >= tasa:
            continue
        recibido = int(valor) ^ (1 << bit)
        esperado[i] = recibido if recibido < 32768 else recibido - 65536
        etiquetas[i] = 1

    atacada, observadas = blind.atacar_serie(valores, bit, tasa=tasa, seed=42)
    np.testing.assert_array_equal(atacada, esperado)
    np.testing.assert_array_equal(observadas, etiquetas)
    np.testing.assert_array_equal(valores, original)


def test_cadena_criptografica_y_contadores_no_se_omiten(monkeypatch):
    llamadas = []
    encrypt_real, decrypt_real = blind.encrypt, blind.decrypt

    def encrypt(trama, key, devaddr, fcnt):
        llamadas.append(('encrypt', key, devaddr, fcnt))
        return encrypt_real(trama, key, devaddr, fcnt)

    def decrypt(trama, key, devaddr, fcnt):
        llamadas.append(('decrypt', key, devaddr, fcnt))
        return decrypt_real(trama, key, devaddr, fcnt)

    monkeypatch.setattr(blind, 'encrypt', encrypt)
    monkeypatch.setattr(blind, 'decrypt', decrypt)
    recibidos, etiquetas = blind.atacar_serie(
        np.array([np.nan, 160., np.nan, 128.]), 5, tasa=1.0)
    np.testing.assert_array_equal(recibidos, [np.nan, 128., np.nan, 160.])
    np.testing.assert_array_equal(etiquetas, [0, 1, 0, 1])
    assert llamadas == [
        (operacion, blind.APPSKEY, blind.DEVADDR, fcnt)
        for fcnt in (2, 4) for operacion in ('encrypt', 'decrypt')
    ]
