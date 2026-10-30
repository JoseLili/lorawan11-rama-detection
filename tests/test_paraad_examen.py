"""Pruebas sintéticas de unidades comunes e intervalos pareados; sin examen."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

pytest.importorskip('tensorflow')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'experiments/anomalias_red'))
from evaluar_paraad_revision20 import intervalo,mascara_comun,DET
from src.detect.paraad import OBJETIVOS


def test_intervalo_pareado_identico_es_cero_y_repetible():
    y=np.tile([True,False,True,False],10)
    a=np.tile([True,False,False,True],10)
    b=np.repeat(np.arange(10),4)
    uno=intervalo(y,a,b,[42,20,2024,0],a)
    assert uno==intervalo(y,a,b,[42,20,2024,0],a)
    for f in uno:assert f['estimacion']==f['ic_bajo']==f['ic_alto']==0


def test_mascara_interseccion_se_fija_con_limpio():
    dias=pd.date_range('2023-01-01',periods=2)
    partes=[]
    for det in DET:
        t=pd.DataFrame(1.,index=dias,columns=OBJETIVOS)
        if det=='V4':t.iloc[0,0]=np.nan
        partes.append(t.assign(detector=det,conjunto='limpia_2023').rename_axis('dia').reset_index())
    tabla=pd.concat(partes)
    ok=mascara_comun(tabla,'limpia_2023',dias)
    assert not ok.iloc[0,0] and ok.to_numpy().sum()==len(OBJETIVOS)*2-1
    tabla=pd.concat([tabla,tabla.iloc[:1]])
    with pytest.raises(ValueError,match='duplicados'):mascara_comun(tabla,'limpia_2023',dias)
