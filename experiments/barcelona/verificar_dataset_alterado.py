"""Verifica los artefactos ya escritos, sin inferencia ni métricas de detección."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    base = ROOT / 'results/barcelona_paraad'
    out, w = base / 'ataques_proporcionales_v1', base / 'ventanas_v1'
    reg = json.loads((out / 'registro.json').read_text())
    assert reg['unidades'] == len(reg['sha256_completos']) == 150
    assert sha(out / 'resumen.csv') == reg['sha256_resumen']
    for nombre, h in reg['entrada']['sha256_entradas'].items():
        assert sha(ROOT / nombre) == h
    assert sha(w / 'mascara_comun.csv') == reg['mascara_comun_sha256']
    limpio = pd.read_parquet(w / 'valores.parquet')
    soporte = pd.read_parquet(w / 'estacion_dias.parquet')
    resumen = pd.read_csv(out / 'resumen.csv')
    for nombre, h in reg['sha256_completos'].items():
        completo = out / nombre
        assert sha(completo) == h
        registro = json.loads(completo.read_text())
        carpeta = completo.parent
        for archivo, esperado in registro['sha256_salidas'].items():
            assert sha(carpeta / archivo) == esperado
        info = registro['resumen']
        a = pd.read_parquet(carpeta / 'valores_alterados.parquet')
        y = pd.read_parquet(carpeta / 'etiquetas_hora.parquet')
        ep = pd.read_parquet(carpeta / 'episodio_hora.parquet')
        original = limpio.loc[a.index]
        assert a.index.equals(limpio.index[info['offset_global']:info['offset_global'] + len(a)])
        assert a.notna().equals(original.notna())
        cambiado = original.notna() & a.ne(original)
        pd.testing.assert_frame_equal(y, cambiado, check_exact=True)
        assert not (y & ~ep).any().any()
        pd.testing.assert_frame_equal(a.where(~ep), original.where(~ep), check_exact=True)
        assert np.equal(a.to_numpy()[y.to_numpy()] % 1, 0).all()
        sd = pd.read_parquet(carpeta / 'estacion_dias.parquet')
        ref = soporte.set_index(['dia_utc', 'estacion']).loc[pd.MultiIndex.from_frame(sd[['dia_utc', 'estacion']])]
        np.testing.assert_array_equal(sd.comun, ref.comun)
        np.testing.assert_array_equal(sd.inicio_pos + info['offset_global'], ref.inicio_pos)
        np.testing.assert_array_equal(sd.fin_pos + info['offset_global'], ref.fin_pos)
        z = np.load(carpeta / 'z.npy', allow_pickle=False)
        F = np.load(carpeta / 'l0_features.npy', allow_pickle=False)
        assert z.shape == (len(a), 13) and F.shape == (len(a), 41)
        assert np.isfinite(z).all() and np.isfinite(F).all()
        np.testing.assert_array_equal(F[:, 13:26], a.notna().to_numpy(np.float32))
    # Las fechas/etiquetas programadas y el universo permanecen pareados entre δ.
    for _, g in resumen.groupby('calendario'):
        assert g.estacion_dias_comunes.nunique() == g.estacion_dias_positivos_comunes.nunique() == 1
    assert set(resumen[resumen.uso.str.contains('2018|2019')].delta) == {1., .5, .2, .1, .05}
    assert set(resumen[~resumen.uso.str.contains('2018|2019')].delta) == {.5}
    resultado = dict(unidades_verificadas=150, hashes_correctos=True, faltantes_intactos=True,
                     cambios_solo_en_episodios=True, etiquetas_coinciden_con_cambios=True,
                     mascara_comun_intacta=True, entradas_finitas=True, soportes_pareados=True,
                     sha256_registro=sha(out / 'registro.json'), sha256_verificador=sha(Path(__file__)))
    (out / 'verificacion_final.json').write_text(json.dumps(resultado, indent=2) + '\n')
    print(json.dumps(resultado, indent=2))


if __name__ == '__main__':
    main()
