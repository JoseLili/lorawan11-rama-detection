"""Inspección remota de solo lectura para heartbeat; no relanza procesos."""
from pathlib import Path
import argparse
import json
import os


def process_status(pid):
    """Un zombie conserva PID, pero ya no puede avanzar ni escribir markers."""
    if not pid:return dict(pid=None,vivo=False,estado='sin_pid')
    try:
        stat=Path(f'/proc/{int(pid)}/stat').read_text()
        state=stat.rsplit(')',1)[1].split()[0]
        return dict(pid=pid,vivo=state not in {'Z','X'},estado=state)
    except FileNotFoundError:return dict(pid=pid,vivo=False,estado='ausente')
    except (OSError,ValueError,IndexError):
        try:os.kill(int(pid),0)
        except ProcessLookupError:return dict(pid=pid,vivo=False,estado='ausente')
        except PermissionError:return dict(pid=pid,vivo=None,estado='sin_permiso')
        return dict(pid=pid,vivo=True,estado='pid_presente')


def inspect(sal):
    report={'salida':str(sal),'existe':sal.exists()}
    for name in ['SUPERVISOR.json','ESTADO_EVALUACION.json','FINAL.json','ERROR_EVALUACION.json','DESCARGA.json','REPRODUCIBLE.json']:
        p=sal/name
        if p.exists():
            try:report[name]=json.loads(p.read_text())
            except (OSError,json.JSONDecodeError):report[name]={'estado':'actualizando'}
    pid=report.get('SUPERVISOR.json',{}).get('pid')
    supervisor=process_status(pid)
    report['supervisor_proceso']=supervisor
    terminal='FINAL.json' in report or 'ERROR_EVALUACION.json' in report
    report['posible_interrupcion']=sal.exists() and not terminal and supervisor['vivo'] is False
    if report['posible_interrupcion']:
        report['diagnostico']='El supervisor no está vivo y no dejó marker terminal. Conservar VM y revisar logs; no relanzar.'
    saved_runs={r.get('corrida'):r for r in report.get('ESTADO_EVALUACION.json',{}).get('corridas',[])}
    progress=[]
    for name in ['corrida1','corrida2']:
        out=sal/name
        log=sal/f'{name}.log'
        text=log.read_text(errors='replace') if log.exists() else ''
        progress.append(dict(corrida=name,proceso=process_status(saved_runs.get(name,{}).get('pid')),
            matrices_con_puntajes=text.count(': puntajes diarios guardados'),
            bootstrap_listo=(out/'intervalos_exploratorios.csv').exists(),
            marcador_listo=(out/'LISTO.json').exists(),ultimas_lineas_log=text[-2000:]))
    report['inspeccion_corridas']=progress
    download=report.get('DESCARGA.json',{})
    archive=Path(download['archivo']) if 'archivo' in download else None
    report['zip_disponible']=bool(archive and archive.is_file() and archive.stat().st_size==download.get('bytes') and download.get('sha256'))
    report['lista_para_descargar']=bool(terminal and report['zip_disponible'])
    test=sal/'prueba.log'
    if test.exists():report['prueba_log_final']=test.read_text(errors='replace')[-1800:]
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--salida',type=Path,default=Path('/content/tinto_evaluacion/results/exploracion_tinto_2022/evaluacion_colab_20261029'))
    a=p.parse_args();print(json.dumps(inspect(a.salida),indent=2,ensure_ascii=False))
