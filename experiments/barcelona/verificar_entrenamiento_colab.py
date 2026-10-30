"""Auditoría local de entrenamiento descargado; no abre calibración ni examen."""
import hashlib
import json
from pathlib import Path
import tarfile

import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'results/barcelona_paraad/colab_20261029'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def entrada_esperada(detector):
    paquete=BASE/('barcelona_entrenamiento.tar.gz' if detector=='l0' else 'barcelona_limpio_entrenamiento.tar.gz')
    esperado=json.loads((BASE/f'partes_{detector}/registro.json').read_text())['sha256']
    assert sha(paquete)==esperado
    with tarfile.open(paquete) as t:
        meta=json.load(t.extractfile('entrada/registro_paquete.json'))
    extra=json.loads((BASE/'suplemento_fuentes.json').read_text())
    for n,h in extra.items():
        assert sha(ROOT/n)==h
        meta['archivos'][n]=h
    return hashlib.sha256((json.dumps(meta,ensure_ascii=False,indent=2)+'\n').encode()).hexdigest()


def main():
    filas=[]; hashes={}; pares=0
    for d,esperados in [('l0',2),('v4',26),('paraad',4)]:
        carpeta=BASE/d
        estado=json.loads((carpeta/'estado_supervisor.json').read_text())
        assert estado['estado']['estado']=='completo' and estado['sesion_liberada']
        assert sha(carpeta/'snapshot_ultimo.tar.gz')==estado['sha256_snapshot']
        root=carpeta/'recuperado/salidas'/d
        congelado=root/'congelado.json'; c=json.loads(congelado.read_text())
        assert c['igual'] and not c['smoke'] and len(c['verificados'])==esperados
        assert c['entrada']['sha256_entrada']==entrada_esperada(d)
        assert c['entrada']['sha256_script']==sha(ROOT/'experiments/barcelona/entrenar_colab.py')
        assert c['entrada']['semilla']==42 and c['entrada']['threads']==1
        for n,h in c['verificados'].items():
            verificado=root/n;assert sha(verificado)==h
            assert all(json.loads(verificado.read_text())[k] for k in ['igual','historias','pesos','optimizador','prediccion_control'])
            a,b=verificado.parent/'r1',verificado.parent/'r2'
            for r in [a,b]:
                for nombre,h2 in json.loads((r/'completo.json').read_text())['sha256'].items():
                    assert sha(r/nombre)==h2
            pd.testing.assert_frame_equal(pd.read_csv(a/'historia.csv',float_precision='round_trip'),
                                          pd.read_csv(b/'historia.csv',float_precision='round_trip'),check_exact=True)
            np.testing.assert_array_equal(np.load(a/'prediccion_control.npy'),np.load(b/'prediccion_control.npy'))
            x,y=np.load(a/'pesos_control.npz'),np.load(b/'pesos_control.npz');assert x.files==y.files
            for k in x.files:np.testing.assert_array_equal(x[k],y[k])
            pares+=1
        selecciones=list(root.glob('*/seleccion.json')) if d=='v4' else [root/'seleccion.json']
        for sel in sorted(selecciones):
            meta=json.loads(sel.read_text())
            elegido=meta['elegido'] if d=='paraad' else meta
            epocas=elegido['epocas']
            hist=pd.read_csv(sel.parent/'definitivo/r1/historia.csv',float_precision='round_trip')
            assert len(hist)==epocas
            modelo=sel.parent/'definitivo/r1/modelo.keras'
            filas.append(dict(detector=d,estacion=sel.parent.name if d=='v4' else 'compartido',
                               epocas=epocas,dropout=elegido.get('dropout',.2),
                               val_loss=elegido['val_loss'],sha256_modelo=sha(modelo)))
        hashes[d]=sha(congelado)
    assert pares==32 and len(filas)==15
    tabla=BASE/'seleccion_modelos_verificada.csv';pd.DataFrame(filas).to_csv(tabla,index=False,float_format='%.17g')
    resultado=dict(completo=True,pares_verificados=pares,repeticiones_cientificas=pares*2,
                    modelos_definitivos=15,vm_liberadas=3,historias_iguales=True,pesos_y_optimizador_iguales=True,
                    prediccion_control_igual=True,paquetes_y_respaldos_verificados=True,
                    origen='Modelos nuevos entrenados en Colab CPU; no cargados de RAMA',
                    sha256_congelados=hashes,sha256_tabla=sha(tabla),sha256_verificador=sha(Path(__file__)),
                    alcance='Sin calibración2017 ni examen2018–2019; no métricas de detección')
    (BASE/'verificacion_entrenamiento.json').write_text(json.dumps(resultado,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(resultado,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
