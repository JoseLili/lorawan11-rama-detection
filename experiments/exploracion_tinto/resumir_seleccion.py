"""Resumen de avance o verificación final; no entrena ni modifica modelos."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd


def resumen(root):
    rows=[];histories=[];done=[]
    for name in ['corrida_cpu1','corrida_cpu2']:
        p=root/name
        item={'corrida':name}
        if (p/'progreso.json').exists():
            try:item.update(json.loads((p/'progreso.json').read_text()))
            except json.JSONDecodeError:item['fase']='actualizando avance'
        h=p/'historia_en_curso.csv'
        frame=pd.read_csv(h) if h.exists() and h.stat().st_size else pd.DataFrame()
        histories.append(frame)
        item['epocas_completas']=len(frame)
        if len(frame):
            item['mejor_epoca_provisional']=int(frame.val_loss.to_numpy().argmin())+1
            item['mejor_val_loss_provisional']=float(frame.val_loss.min())
        r=p/'resultado.json'
        if r.exists():
            item['resultado']=json.loads(r.read_text());done.append(name)
        rows.append(item)
    n=min(len(f) for f in histories)
    prefix_equal=bool(n and histories[0].iloc[:n].equals(histories[1].iloc[:n]))
    result={'corridas':rows,'epocas_completas_comunes':n,'historias_comunes_identicas':prefix_equal,'terminadas':len(done)}
    if len(done)==2:
        a=root/'corrida_cpu1';b=root/'corrida_cpu2'
        x=json.loads((a/'resultado.json').read_text());y=json.loads((b/'resultado.json').read_text())
        assert x==y,'Diferencia en pesos o configuración final'
        pd.testing.assert_frame_equal(pd.read_csv(a/'historia.csv'),pd.read_csv(b/'historia.csv'))
        np.testing.assert_array_equal(np.load(a/'probabilidades_control.npy'),np.load(b/'probabilidades_control.npy'))
        result['verificacion_final']={'pesos_identicos':True,'historias_identicas':True,'probabilidades_identicas':True,
            'E':x['E'],'epocas_ejecutadas':x['epocas'],'sha256_pesos':x['pesos_sha256']}
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--raiz',type=Path,required=True)
    p.add_argument('--guardar',action='store_true')
    a=p.parse_args();r=resumen(a.raiz)
    if a.guardar:
        assert r['terminadas']==2,'Todavía no finalizaron ambas corridas'
        (a.raiz/'reproducibilidad_final.json').write_text(json.dumps(r,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps(r,indent=2,ensure_ascii=False))
