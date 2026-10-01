"""Figuras de revisión: reutiliza predicciones V4; nunca importa TensorFlow.

El riesgo compuesto conserva su definición de indicador (días × fracción de
ataques no detectados). NO se presenta como frecuencia conjunta observada.
"""
from pathlib import Path
import hashlib
import json
import sys

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from src.attack.blind import atacar_serie
from src.detect.red import contexto_diario, efectos_red
from src.ingest.rama import load_wide, to_long

BITS = list(range(8))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verificar_fuentes(raiz):
    carpeta = raiz / 'results/multiestacion_v4_p95_2025'
    config = json.loads((carpeta / 'configuracion.json').read_text())
    assert sha(raiz / 'data/raw/2025O3.xls') == config['dataset_sha256']
    for nombre, esperado in config['codigo_sha256'].items():
        assert sha(raiz / nombre) == esperado, f'Código distinto al evaluado: {nombre}'
    firma = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
    predicciones = []
    fuentes = {}
    for estado_path in sorted(carpeta.glob('*/estado.json')):
        estado = json.loads(estado_path.read_text())
        assert estado['firma'] == firma
        for nombre, esperado in estado['sha256'].items():
            path = estado_path.parent / nombre
            assert sha(path) == esperado, f'Checkpoint alterado: {path}'
        fuentes[str(estado_path.relative_to(raiz))] = sha(estado_path)
        predicciones.append(pd.read_csv(estado_path.parent / 'predicciones.csv'))
    assert len(predicciones) == 27
    for nombre in ['configuracion.json', 'cobertura_mensajes.csv.gz', 'eventos_aislados.csv.gz']:
        fuentes[str((carpeta / nombre).relative_to(raiz))] = sha(carpeta / nombre)
    fuentes['data/raw/2025O3.xls'] = config['dataset_sha256']
    base = pd.read_csv(carpeta / 'cobertura_mensajes.csv.gz', parse_dates=['fecha'])
    campos = ['timestamp', 'estacion', 'predicho_ppb', 'base_ppb', 'perfil_ppb', 'umbral_ppb']
    guardadas = pd.concat(predicciones, ignore_index=True)[campos].sort_values(campos[:2]).reset_index(drop=True)
    referencia = base[campos].sort_values(campos[:2]).reset_index(drop=True)
    # La consolidación histórica leyó y volvió a escribir el perfil float64;
    # ese segundo paso CSV puede cambiar sus últimos decimales. Predicciones,
    # bases float32, umbrales y claves deben coincidir exactamente.
    pd.testing.assert_frame_equal(guardadas.drop(columns='perfil_ppb'),
                                  referencia.drop(columns='perfil_ppb'), check_exact=True)
    np.testing.assert_allclose(guardadas.perfil_ppb, referencia.perfil_ppb, rtol=0, atol=1e-12)
    assert base.evaluable.all() and not base.duplicated(['timestamp', 'estacion']).any()
    return carpeta, base, fuentes


def resumir(eventos):
    """Conteos empíricos y producto descriptivo, explícitamente separados."""
    filas = []
    for bit, bloque in eventos.groupby('bit', sort=True):
        assert bloque.evaluable.all(), 'No se asume detección para mensajes sin modelo.'
        n = len(bloque)
        dias = bloque.fecha.nunique()
        no_detectados = int((~bloque.detectado).sum())
        for tipo in ['falsa_fase1', 'anulada_fase1']:
            daninos = bloque[tipo]
            escapan = daninos & ~bloque.detectado
            dv = bloque.loc[daninos, 'fecha'].nunique()
            de = bloque.loc[escapan, 'fecha'].nunique()
            nd, ne = int(daninos.sum()), int(escapan.sum())
            oportunidad = 100 * dv / dias
            no_deteccion = 100 * no_detectados / n
            filas.append(dict(bit=int(bit), delta_ppb=2**int(bit), tipo_dano=tipo,
                n_dias=int(dias), n_ataques=n, detectados=n-no_detectados,
                no_detectados=no_detectados, recall_pct=100-no_deteccion,
                dias_vulnerables=int(dv), dias_vulnerables_pct=oportunidad,
                no_deteccion_pct=no_deteccion,
                riesgo_compuesto_indicador_pct=oportunidad * no_deteccion / 100,
                ataques_daninos=nd, ataques_daninos_no_detectados=ne,
                no_deteccion_condicionada_dano_pct=100*ne/nd if nd else np.nan,
                dias_dano_no_detectado=int(de), dias_dano_no_detectado_pct=100*de/dias))
    return pd.DataFrame(filas)


def construir_tablas(raiz=RAIZ):
    carpeta, base, fuentes = verificar_fuentes(raiz)
    anteriores = pd.read_csv(carpeta / 'eventos_aislados.csv.gz', parse_dates=['fecha'])
    assert set(anteriores.bit) == set(range(1, 8))
    # Bit 0: nueva evaluación real con la misma cadena de cifrado. La predicción
    # guardada se reutiliza: cada ataque es aislado y el objetivo no entra en X.
    nuevos = base.copy()
    recibidos, etiquetas = atacar_serie(base.original_ppb.to_numpy(), 0, tasa=1., seed=42)
    assert etiquetas.all()
    np.testing.assert_array_equal(recibidos, base.original_ppb.to_numpy(dtype=int) ^ 1)
    nuevos['bit'], nuevos['recibido_ppb'] = 0, recibidos
    recibidos_modelo = (base.base_ppb.to_numpy(dtype=np.float32)
                       + (recibidos-base.perfil_ppb.to_numpy()).astype(np.float32))
    nuevos['detectado'] = np.abs(recibidos_modelo-base.predicho_ppb.to_numpy()) > base.umbral_ppb.to_numpy()
    nuevos = pd.concat([nuevos, efectos_red(base, recibidos)], axis=1)
    campos = ['fecha', 'timestamp', 'estacion', 'bit', 'evaluable', 'detectado',
              'falsa_fase1', 'anulada_fase1']
    for bit, bloque in anteriores.groupby('bit'):
        assert bloque[campos[:3]].reset_index(drop=True).equals(base[campos[:3]])
        assert len(bloque) == len(base)
        # Verificación del cálculo de detección previo, sin volver a predecir.
        recibido = (bloque.base_ppb.to_numpy(dtype=np.float32)
                    + (bloque.recibido_ppb.to_numpy()-bloque.perfil_ppb.to_numpy()).astype(np.float32))
        np.testing.assert_array_equal(bloque.detectado,
            np.abs(recibido-bloque.predicho_ppb.to_numpy()) > bloque.umbral_ppb.to_numpy())
    todos = pd.concat([nuevos[campos], anteriores[campos]], ignore_index=True)
    tabla = resumir(todos)
    # Contraste con conteos aceptados: no altera resultados de bits 1-7.
    previo = pd.read_csv(carpeta / 'resumen_red_por_bit.csv')
    for fila in tabla[tabla.bit > 0].itertuples():
        r = previo[(previo.bit == fila.bit) & (previo.tipo_dano == fila.tipo_dano)].iloc[0]
        assert fila.dias_vulnerables == r.dias_vulnerables_evaluables
        assert fila.dias_dano_no_detectado == r.dias_dano_no_detectado
        assert fila.ataques_daninos == r.ataques_daninos_evaluables
    # Daño anual SIN LSTM: todos los mensajes, reemplazados de uno en uno.
    matriz = (to_long(load_wide(raiz / 'data/raw/2025O3.xls'), 'O3')
              .pivot(index='timestamp', columns='station', values='value').sort_index()
              .dropna(axis=1, how='all'))
    anual = contexto_diario(matriz)
    filas, detalle = [], []
    originales = anual.original_ppb.to_numpy(dtype=int)
    np.testing.assert_array_equal(originales, anual.original_ppb)
    unicos = np.unique(originales)
    for bit in BITS:
        # El XOR anual se valida exhaustivamente por valor distinto contra la
        # cadena real CayenneLPP/cifrado/flip/descifrado. No implica sumar siempre.
        real, _ = atacar_serie(unicos.astype(float), bit, tasa=1., seed=42)
        np.testing.assert_array_equal(real, unicos ^ (1 << bit))
        efectos = efectos_red(anual, originales ^ (1 << bit))
        por_dia = pd.DataFrame({'fecha': anual.fecha,
            'falsa_fase1': efectos.falsa_fase1, 'anulada_fase1': efectos.anulada_fase1})
        por_dia = por_dia.groupby('fecha').any().reset_index()
        por_dia['bit'] = bit
        detalle.append(por_dia)
        filas.append(dict(bit=bit, delta_ppb=2**bit, n_dias=len(por_dia),
            dias_falsas_activaciones=int(por_dia.falsa_fase1.sum()),
            dias_contingencias_ocultadas=int(por_dia.anulada_fase1.sum()),
            falsas_activaciones_pct=100*por_dia.falsa_fase1.mean(),
            contingencias_ocultadas_pct=100*por_dia.anulada_fase1.mean()))
    info = dict(fuentes=fuentes, n_modelos=27, n_estaciones_candidatas=33,
        test_inicio=str(base.fecha.min().date()), test_fin=str(base.fecha.max().date()),
        test_n_dias=base.fecha.nunique(), test_mensajes=len(base),
        fpr_limpio_pct=float(100*base.alerta_limpia.mean()),
        maximo_test_ppb=float(base.maximo_original_ppb.max()),
        anual_n_dias=anual.fecha.nunique(), anual_mensajes=len(anual),
        anual_dias_excedencia=int(anual.groupby('fecha').maximo_original_ppb.first().ge(155).sum()),
        modelo='Predicciones persistidas verificadas por hash; no entrenamiento ni nueva inferencia.',
        bits=BITS, umbral='p95 propio por estación, sin recalibrar',
        riesgo='Indicador días vulnerables (%) × no detección global (%) / 100; no frecuencia conjunta.',
        escenario='Un mensaje por escenario; máximo diario recalculado conservando todos los demás.')
    return tabla, pd.DataFrame(filas), pd.concat(detalle, ignore_index=True), nuevos, info


def figuras(tabla, anual, info, destino):
    destino.mkdir(parents=True, exist_ok=True)
    t = tabla[tabla.tipo_dano == 'falsa_fase1'].sort_values('bit')
    archivos = []
    for compuesto in [True, False]:
        fig, ax = plt.subplots(figsize=(10, 7.5))
        ax.plot(t.bit, t.dias_vulnerables_pct, 'o-', color='crimson', lw=2, label='Días vulnerables')
        ax.plot(t.bit, t.no_deteccion_pct, 's--', color='seagreen', lw=2, label='No detección')
        if compuesto:
            ax.plot(t.bit, t.riesgo_compuesto_indicador_pct, 'D-', color='royalblue', lw=2,
                    label='Riesgo compuesto')
            for r in t.itertuples():
                ax.annotate(f'{r.riesgo_compuesto_indicador_pct:.1f}%',
                            (r.bit, r.riesgo_compuesto_indicador_pct),
                            xytext=(0, 10), textcoords='offset points', ha='center',
                            color='royalblue', fontsize=9)
        titulo = 'Riesgo compuesto por bit' if compuesto else 'Días vulnerables y no detección'
        ax.set_title(titulo+'\nFalsas excedencias de O₃ — umbral 155 ppb', fontsize=14)
        configurar_ejes(ax, 'Porcentaje (%)')
        ax.legend(loc='upper left', bbox_to_anchor=(0, 1.0), fontsize=10)
        pie = (f'{info["test_n_dias"]} días de prueba (21/oct–31/dic/2025); 27 detectores, p95 por estación. Sin contramedida.\n'
               'Rojo: días con ≥1 falsa excedencia posible / días del periodo. Verde: ataques no detectados / todos los ataques.\n'
               'Cada ataque altera un solo mensaje. Los faltantes no se consideran ceros; verde no es porcentaje de días.')
        if compuesto:
            pie += '\nAzul: producto descriptivo de rojo y verde / 100. NO es el porcentaje observado de días con daño no detectado.'
        pie += f'\nFalsas alarmas en test limpio: {info["fpr_limpio_pct"]:.2f} %. No se fuerza un cruce ni un máximo en un bit específico.'
        fig.text(.07, .035, pie, fontsize=8.5, va='bottom')
        fig.subplots_adjust(left=.09, right=.97, top=.87, bottom=.27)
        nombre = 'riesgo_compuesto_red_bits_0_7.png' if compuesto else 'dias_vulnerables_no_deteccion_red_bits_0_7.png'
        fig.savefig(destino / nombre, dpi=170)
        plt.close(fig)
        archivos.append(destino / nombre)
    fig, ax = plt.subplots(figsize=(10, 7.5))
    ax.plot(anual.bit, anual.falsas_activaciones_pct, 'o-', color='crimson', lw=2, label='Falsas activaciones')
    ax.plot(anual.bit, anual.contingencias_ocultadas_pct, 's--', color='darkorange', lw=2, label='Contingencias ocultadas')
    configurar_ejes(ax, 'Días (%)')
    ax.set_title('Efecto del ataque sobre el umbral de contingencia\nRed observada, 2025 — O₃, 155 ppb', fontsize=14)
    ax.legend(loc='upper left', fontsize=10)
    for columna, color, dy in [('falsas_activaciones_pct', 'crimson', 24), ('contingencias_ocultadas_pct', 'darkorange', 9)]:
        for r in anual.itertuples():
            ax.annotate(f'{getattr(r, columna):.1f}%', (r.bit, getattr(r, columna)), xytext=(0,dy),
                        textcoords='offset points', ha='center', color=color, fontsize=9, clip_on=False)
    pie = (f'Denominador común: {info["anual_n_dias"]} días con datos; 33 estaciones. Cada escenario modifica un solo mensaje.\n'
           'Falsa activación: máximo diario pasa de <155 a ≥155 ppb. Ocultamiento: pasa de ≥155 a <155 ppb.\n'
           'Son cruces simulados de mediciones, no activaciones/desactivaciones oficiales ni pruebas de persistencia.\n'
           f'El año contiene {info["anual_dias_excedencia"]} días con máximo observado ≥155 ppb; no equivale al número de episodios oficiales.\n'
           'Esta figura evalúa sólo daño: no extrapola el LSTM de octubre–diciembre al resto del año.')
    fig.text(.07, .035, pie, fontsize=8.5, va='bottom')
    fig.subplots_adjust(left=.09, right=.97, top=.87, bottom=.27)
    nombre = destino / 'falsas_activaciones_ocultamientos_2025_bits_0_7.png'
    fig.savefig(nombre, dpi=170)
    plt.close(fig)
    archivos.append(nombre)
    return archivos


def configurar_ejes(ax, ylabel):
    ax.set(xlabel='Bit atacado', ylabel=ylabel, ylim=(0, 105), xlim=(-.25, 7.25))
    ax.set_xticks(BITS, [f'{b}\n({2**b} ppb)' for b in BITS])
    ax.yaxis.set_major_formatter(PercentFormatter(100, decimals=1))
    ax.grid(alpha=.25)


def generar(raiz=RAIZ):
    raiz = Path(raiz)
    tabla, anual, detalle, bit0, info = construir_tablas(raiz)
    destino = raiz / 'results/revision_graficas_bits_0_7'
    destino.mkdir(parents=True, exist_ok=True)
    manifiesto = destino / 'protocolo.json'
    # Run all puede reproducir esta revisión, pero jamás mezclar fuentes nuevas.
    if manifiesto.exists() and json.loads(manifiesto.read_text()) != info:
        raise ValueError('Fuentes o protocolo cambiaron. No sobrescribir una revisión distinta.')
    tablas = {'riesgo_compuesto_red.csv': tabla,
              'efectos_anuales_sin_lstm.csv': anual,
              'dias_efectos_anuales.csv': detalle,
              'evaluacion_bit0.csv.gz': bit0}
    for nombre, df in tablas.items():
        df.to_csv(destino / nombre, index=False)
    manifiesto.write_text(json.dumps(info, indent=2, ensure_ascii=False)+'\n')
    archivos = figuras(tabla, anual, info, raiz / 'docs/img/revision_graficas_bits_0_7')
    print('Predicciones y umbrales guardados verificados. SIN reentrenamiento ni recalibración.')
    print(f'Bit 0: {len(bit0)} ataques aislados; {int(bit0.detectado.sum())} detectados.')
    print('El producto es un indicador; los días con daño no detectado se cuentan aparte en el CSV.')
    return tabla, anual, archivos


if __name__ == '__main__':
    tabla, anual, archivos = generar()
    print(tabla.to_string(index=False))
    print(anual.to_string(index=False))
