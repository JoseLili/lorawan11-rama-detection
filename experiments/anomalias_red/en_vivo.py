"""Monitor en vivo de los entrenamientos del LSTM supervisado. No cambia el entrenamiento.

Un callback de Keras escribe `estado.json` en una carpeta, e `index.html`, en la misma carpeta,
lo lee cada 2 segundos y dibuja las curvas. Para verlo, servir la carpeta sólo en esta máquina y
abrir http://127.0.0.1:8765/ en el navegador:

    .venv/bin/python -m http.server 8765 --bind 127.0.0.1 --directory results/anomalias_red_v1/en_vivo

No usa bibliotecas externas. Las predicciones de validación que hace al final de cada época no
alteran el entrenamiento (se comprobó con el diagnóstico de la revisión 6: mismas pérdidas por
época con y sin ellas).
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import numpy as np
from sklearn.metrics import roc_auc_score
from tensorflow import keras

CARPETA = Path(__file__).resolve().parents[2] / 'results/anomalias_red_v1/en_vivo'


def deteccion_fa(y, s, fa=0.05) -> float:
    """% de etiquetas 1 sobre el umbral que deja `fa` de falsas alarmas en las etiquetas 0."""
    u = np.quantile(s[y == 0], 1 - fa)
    return 100 * float((s[y == 1] > u).mean())


class EnVivo(keras.callbacks.Callback):
    """Registra pérdida por lote y, al final de cada época, pérdida, detección y AUC de validación."""

    def __init__(self, corrida: str, fase: str, val=None, cada: int = 50, carpeta: Path = CARPETA):
        super().__init__()
        self.carpeta, self.cada, self.val = Path(carpeta), cada, val
        self.carpeta.mkdir(parents=True, exist_ok=True)
        (self.carpeta / 'index.html').write_text(PAGINA, encoding='utf-8')
        previo = self._leer()
        self.estado = previo if previo.get('corrida') == corrida else dict(corrida=corrida, fases=[], notas=[])
        self.fase = dict(nombre=fase, cada=cada, epocas_max=None, lotes_por_epoca=None, inicio=time.time(),
                         epoca=0, lote=0, terminada=False, lotes=[], epocas=[])
        self.estado['fases'] = [f for f in self.estado['fases'] if f['nombre'] != fase] + [self.fase]

    def _leer(self) -> dict:
        try:
            return json.loads((self.carpeta / 'estado.json').read_text())
        except (OSError, ValueError):
            return {}

    def _guardar(self):
        self.estado['actualizado'] = time.time()
        tmp = self.carpeta / 'estado.json.tmp'
        tmp.write_text(json.dumps(self.estado), encoding='utf-8')
        os.replace(tmp, self.carpeta / 'estado.json')           # el navegador nunca lee a medias

    def nota(self, texto: str):
        self.estado['notas'].append(texto)
        self._guardar()

    def on_train_begin(self, logs=None):
        self.fase['epocas_max'], self.fase['lotes_por_epoca'] = self.params.get('epochs'), self.params.get('steps')
        self._guardar()

    def on_epoch_begin(self, epoch, logs=None):
        self.fase['epoca'], self._t_epoca = epoch + 1, time.time()

    def on_train_batch_end(self, batch, logs=None):
        self.fase['lote'] = batch + 1
        if (batch + 1) % self.cada == 0 and logs and 'loss' in logs:
            pasos = self.fase['lotes_por_epoca'] or 1
            self.fase['lotes'].append([round(self.fase['epoca'] - 1 + (batch + 1) / pasos, 4), float(logs['loss'])])
            self._guardar()

    def on_epoch_end(self, epoch, logs=None):
        logs = logs or {}
        fila = dict(epoca=epoch + 1, loss=float(logs['loss']), segundos=round(time.time() - self._t_epoca, 1))
        if 'val_loss' in logs:
            fila['val_loss'] = float(logs['val_loss'])
        if self.val is not None:
            Xva, yva = self.val
            s = self.model.predict(Xva, batch_size=4096, verbose=0).ravel()
            fila['deteccion_val_fa5_pct'], fila['auc_val'] = deteccion_fa(yva, s), float(roc_auc_score(yva, s))
        self.fase['epocas'].append(fila)
        self._guardar()

    def on_train_end(self, logs=None):
        self.fase['terminada'] = True
        self._guardar()


PAGINA = r"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Entrenamiento en vivo</title>
<style>
:root{--fondo:#fafaf7;--texto:#1f2328;--tenue:#6b7075;--rejilla:#e3e3de;--a:#2563eb;--b:#d9480f;--c:#2f9e44}
@media (prefers-color-scheme:dark){:root{--fondo:#16181b;--texto:#e6e6e3;--tenue:#9aa0a6;--rejilla:#2c2f33;--a:#6ea8fe;--b:#ff8a50;--c:#69db7c}}
body{margin:0;background:var(--fondo);color:var(--texto);font:15px/1.45 system-ui,sans-serif}
main{max-width:1000px;margin:0 auto;padding:20px 16px}
h1{font-size:20px;margin:0 0 4px}.tenue{color:var(--tenue)}
.fase{margin:22px 0 8px;font-weight:600}.estado{font-variant-numeric:tabular-nums}
.graficas{display:grid;grid-template-columns:repeat(auto-fit,minmax(420px,1fr));gap:14px}
figure{margin:0}figcaption{font-size:13px;color:var(--tenue);margin-bottom:2px}
svg{width:100%;height:auto;display:block}
.barra{height:6px;background:var(--rejilla);border-radius:3px;overflow:hidden;margin:6px 0}
.barra>div{height:100%;background:var(--a)}
ul{margin:6px 0 0;padding-left:18px}
</style></head><body><main>
<h1>Entrenamiento en vivo</h1><div class="tenue" id="corrida">Esperando datos…</div>
<div id="fases"></div><ul id="notas" class="tenue"></ul>
</main><script>
const css=n=>getComputedStyle(document.documentElement).getPropertyValue(n).trim();
function grafica(series,etqX,etqY,entero){
  const W=460,H=240,m={l:52,r:12,t:26,b:36};const pts=series.flatMap(s=>s.p);
  if(!pts.length)return '<div class="tenue">Sin datos todavía</div>';
  let x0=Math.min(...pts.map(p=>p[0])),x1=Math.max(...pts.map(p=>p[0])),y0=Math.min(...pts.map(p=>p[1])),y1=Math.max(...pts.map(p=>p[1]));
  if(x1===x0)x1=x0+1;if(y1===y0){y1+=Math.abs(y1)*0.1||1;y0-=Math.abs(y0)*0.1||1}
  const X=v=>m.l+(v-x0)/(x1-x0)*(W-m.l-m.r),Y=v=>H-m.b-(v-y0)/(y1-y0)*(H-m.t-m.b);
  let s=`<svg viewBox="0 0 ${W} ${H}" role="img">`;
  for(let i=0;i<=4;i++){const v=y0+(y1-y0)*i/4,y=Y(v);s+=`<line x1="${m.l}" x2="${W-m.r}" y1="${y}" y2="${y}" stroke="${css('--rejilla')}"/><text x="${m.l-6}" y="${y+4}" font-size="11" text-anchor="end" fill="${css('--tenue')}">${+v.toPrecision(3)}</text>`}
  const tx=entero?[...new Set(Array.from({length:5},(_,i)=>Math.round(x0+(x1-x0)*i/4)))]:Array.from({length:5},(_,i)=>x0+(x1-x0)*i/4);
  for(const v of tx){const x=X(v);s+=`<text x="${x}" y="${H-m.b+16}" font-size="11" text-anchor="middle" fill="${css('--tenue')}">${entero?v:+v.toFixed((x1-x0)<2?2:1)}</text>`}
  s+=`<text x="${(W+m.l)/2}" y="${H-4}" font-size="11" text-anchor="middle" fill="${css('--tenue')}">${etqX}</text>`;
  series.forEach((se,k)=>{if(!se.p.length)return;const d=se.p.map(p=>`${X(p[0]).toFixed(1)},${Y(p[1]).toFixed(1)}`).join(' ');
    s+=`<polyline fill="none" stroke="${se.c}" stroke-width="2" points="${d}"/>`;
    if(se.p.length<80)se.p.forEach(p=>{s+=`<circle cx="${X(p[0])}" cy="${Y(p[1])}" r="3" fill="${se.c}"/>`});
    s+=`<rect x="${m.l+k*150}" y="8" width="12" height="3" fill="${se.c}"/><text x="${m.l+16+k*150}" y="13" font-size="11" fill="${css('--texto')}">${se.n}</text>`});
  return s+'</svg>'}
function min(s){return s<60?`${s.toFixed(0)} s`:`${(s/60).toFixed(1)} min`}
async function actualizar(){
  let e;try{e=await (await fetch('estado.json?'+Date.now())).json()}catch{return}
  document.getElementById('corrida').textContent=`${e.corrida} · actualizado hace ${min(Date.now()/1000-e.actualizado)}`;
  let h='';for(const f of e.fases){
    const ep=f.epocas,ult=ep[ep.length-1],trans=Date.now()/1000-f.inicio,pasos=f.lotes_por_epoca||1;
    const avance=f.terminada?1:((f.epoca-1)+f.lote/pasos)/(f.epocas_max||1);
    const nombre={seleccion:'1. Selección de épocas (entrena 2020–2021, valida 2022)',definitivo:'2. Modelo definitivo (2020–2022, E épocas)'}[f.nombre]||f.nombre;
    h+=`<div class="fase">${nombre}${f.terminada?' — terminada':''}</div>
      <div class="estado tenue">Época ${f.epoca} de ${f.epocas_max} como máximo · lote ${f.lote} de ${pasos} · ${min(trans)} transcurridos${ult?` · última época: ${ult.segundos} s`:''}</div>
      <div class="barra"><div style="width:${(100*avance).toFixed(1)}%"></div></div><div class="graficas">
      <figure><figcaption>Pérdida de entrenamiento cada ${f.cada} lotes (promedio acumulado dentro de la época)</figcaption>${grafica([{n:'entrenamiento',c:css('--a'),p:f.lotes}],'época','pérdida')}</figure>
      <figure><figcaption>Pérdida por época (más baja es mejor)</figcaption>${grafica([{n:'entrenamiento',c:css('--a'),p:ep.map(r=>[r.epoca,r.loss])},{n:'validación 2022',c:css('--b'),p:ep.filter(r=>'val_loss' in r).map(r=>[r.epoca,r.val_loss])}],'época','pérdida',true)}</figure>
      ${ep.some(r=>'deteccion_val_fa5_pct' in r)?`<figure><figcaption>Validación 2022: horas anómalas detectadas con 5 % de falsas alarmas (más alto es mejor)</figcaption>${grafica([{n:'detección (%)',c:css('--c'),p:ep.map(r=>[r.epoca,r.deteccion_val_fa5_pct])}],'época','%',true)}</figure>
      <figure><figcaption>Validación 2022: AUC (0.5 = azar, 1 = perfecto)</figcaption>${grafica([{n:'AUC',c:css('--c'),p:ep.map(r=>[r.epoca,r.auc_val])}],'época','AUC',true)}</figure>`:''}</div>`}
  document.getElementById('fases').innerHTML=h;
  document.getElementById('notas').innerHTML=(e.notas||[]).map(t=>`<li>${t}</li>`).join('')}
actualizar();setInterval(actualizar,2000);
</script></body></html>
"""
