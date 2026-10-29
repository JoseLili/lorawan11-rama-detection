"""Supervisor remoto autónomo: prueba breve, dos inferencias paralelas y ZIP.

Lanzar mediante subprocess.Popen desde el kernel; no mantiene ocupado colab exec.
No entrena modelos, no relanza fallos y no reanuda carpetas parciales.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import traceback

COMPARE = r'''
import json,sys
from pathlib import Path
import pandas as pd
root=Path(sys.argv[1])
a=root/'corrida1';b=root/'corrida2'
for name in ['resultados.csv','metricas_por_calendario.csv','intervalos_exploratorios.csv','dias_comunes.csv']:
    pd.testing.assert_frame_equal(pd.read_csv(a/name),pd.read_csv(b/name),check_exact=True)
for name in ['umbrales.json','control_L0.json','LISTO.json','fuentes_matrices.json']:
    assert json.loads((a/name).read_text())==json.loads((b/name).read_text()),name
pa=sorted(p.name for p in a.glob('*_dias.csv.gz'))
pb=sorted(p.name for p in b.glob('*_dias.csv.gz'))
assert pa==pb and len(pa)==62,'Deben existir 31 matrices por dos detectores'
for name in pa:
    pd.testing.assert_frame_equal(pd.read_csv(a/name),pd.read_csv(b/name),check_exact=True)
(root/'REPRODUCIBLE.json').write_text(json.dumps({'dos_evaluaciones_identicas':True,'archivos_diarios_comparados':len(pa)},indent=2)+'\n')
print('Resultados, umbrales, controles, bootstrap y 62 puntajes diarios idénticos.',flush=True)
'''


def write(path,data):
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
    tmp.replace(path)


def utc():return time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())


def runtime_env():
    env=os.environ.copy()
    env.update(CUDA_VISIBLE_DEVICES='-1',TF_ENABLE_ONEDNN_OPTS='1',TF_NUM_INTRAOP_THREADS='2',
        TF_NUM_INTEROP_THREADS='1',OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',
        NUMEXPR_NUM_THREADS='1',MPLCONFIGDIR='/tmp/tinto-mpl')
    return env


def states(sal,processes):
    rows=[]
    for name in ['corrida1','corrida2']:
        process=processes.get(name)
        code=process.poll() if process else None
        marker=(sal/name/'LISTO.json').exists()
        log=sal/f'{name}.log'
        text=log.read_text(errors='replace') if log.exists() else ''
        complete=marker and process is not None and code==0
        failed=process is not None and code is not None and not complete
        row=dict(corrida=name,pid=process.pid if process else None,
            estado='fallida' if failed else 'completa' if complete else 'en_curso' if process else 'no_lanzada',
            codigo_salida=code,matrices_con_puntajes=text.count(': puntajes diarios guardados'),matrices_esperadas=31)
        if failed:row['ultimas_lineas_log']=text[-2500:]
        rows.append(row)
    return rows


def stop_children(processes):
    terminated=[]
    for name,process in processes.items():
        if process.poll() is None:
            process.terminate()
            try:process.wait(timeout=10)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=10)
            terminated.append(name)
    return terminated


def make_zip(sal):
    base=Path('/content/tinto_evaluacion_2022_resultados_20261029')
    if base.with_suffix('.zip').exists():
        base=base.with_name(base.name+'_'+str(os.getpid()))
    return Path(shutil.make_archive(str(base),'zip',root_dir=sal))


def archive_report(path,**extra):
    digest=hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda:source.read(1024*1024),b''):digest.update(chunk)
    return dict(archivo=str(path),bytes=path.stat().st_size,sha256=digest.hexdigest(),**extra)


def supervise(root,sal,python,interval):
    # Reserva atómica: un supervisor repetido no modifica ni relanza la ejecución previa.
    sal.mkdir(parents=True,exist_ok=False)
    processes={};phase='preparacion';started=utc();zip_path=None
    write(sal/'SUPERVISOR.json',dict(pid=os.getpid(),inicio_UTC=started,script=str(Path(__file__).resolve()),
        root=str(root),salida=str(sal),intervalo_segundos=interval,python=str(python)))
    def update(fase,**extra):
        data=dict(fase=fase,actualizado_UTC=utc(),inicio_UTC=started,supervisor_pid=os.getpid(),
            corridas=states(sal,processes),**extra)
        write(sal/'ESTADO_EVALUACION.json',data)
        return data
    try:
        setup=json.loads((root/'PREPARACION_COLAB_OK.json').read_text())
        assert setup['solo_CPU'] and setup['paquete_sha256']=='41b46b9c2adb386e7683c9848d4c5c0cd7974c8c6dca6073f1d5506542121a54'
        assert python.exists(),'Falta el entorno Python preparado'
        script=root/'experiments/exploracion_tinto/evaluar_2022.py'
        env=runtime_env()
        phase='prueba_breve';update(phase)
        with (sal/'prueba.log').open('w') as log:
            result=subprocess.run([str(python),'-u',str(script),'--prueba','--salida',str(sal/'prueba')],
                cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT)
        assert result.returncode==0,'Falló la prueba breve; revisar prueba.log'
        test=json.loads((sal/'prueba/PRUEBA_OK.json').read_text())
        assert test.get('solo_flujo') and test.get('modelos_cargados') and test.get('sin_metricas')
        phase='evaluacion_paralela'
        for name in ['corrida1','corrida2']:
            assert not (sal/name).exists(),'No se reutilizan carpetas parciales'
            with (sal/f'{name}.log').open('w') as log:
                processes[name]=subprocess.Popen([str(python),'-u',str(script),'--salida',str(sal/name),
                    '--batch','512','--bootstrap','2000'],cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT)
        while True:
            report=update(phase)
            print(json.dumps(report,ensure_ascii=False),flush=True)
            if any(r['estado']=='fallida' for r in report['corridas']):
                raise RuntimeError('Falló una evaluación; no se relanza automáticamente')
            if all(r['estado']=='completa' for r in report['corridas']):break
            time.sleep(interval)
        phase='comparacion_exacta';update(phase)
        with (sal/'comparacion.log').open('w') as log:
            result=subprocess.run([str(python),'-u','-c',COMPARE,str(sal)],cwd=root,env=env,
                stdout=log,stderr=subprocess.STDOUT)
        assert result.returncode==0,'No se verificó reproducibilidad; revisar comparacion.log'
        phase='completa'
        update(phase,reproducible=True)
        write(sal/'FINAL.json',dict(estado='completa',reproducible=True,fin_UTC=utc(),modelos_entrenados=False))
        zip_path=make_zip(sal)
        write(sal/'DESCARGA.json',archive_report(zip_path))
        print('FINAL_OK',str(zip_path),flush=True)
        return 0
    except BaseException as error:
        terminated=stop_children(processes)
        details=dict(estado='error',fase=phase,error=str(error),tipo=type(error).__name__,
            fin_UTC=utc(),procesos_terminados_por_fallo=terminated,traceback=traceback.format_exc()[-7000:])
        write(sal/'ERROR_EVALUACION.json',details)
        update('error',error=str(error),fase_fallida=phase)
        try:
            zip_path=make_zip(sal)
            write(sal/'DESCARGA.json',archive_report(zip_path,solo_avances=True))
        except Exception as zip_error:
            write(sal/'ERROR_ZIP.json',dict(error=str(zip_error)))
        print('FINAL_ERROR',json.dumps(details,ensure_ascii=False),str(zip_path),flush=True)
        return 1


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path('/content/tinto_evaluacion'))
    p.add_argument('--salida',type=Path,default=Path('/content/tinto_evaluacion/results/exploracion_tinto_2022/evaluacion_colab_20261029'))
    p.add_argument('--python',type=Path,default=Path('/content/tinto_eval_env/bin/python'))
    p.add_argument('--intervalo',type=int,default=300)
    a=p.parse_args()
    if a.intervalo<1:p.error('Intervalo debe ser positivo')
    try:code=supervise(a.root,a.salida,a.python,a.intervalo)
    except FileExistsError:
        print('NO_RELANZAR: la carpeta de salida ya existe; conservar y revisar su estado.',file=sys.stderr)
        code=2
    raise SystemExit(code)
