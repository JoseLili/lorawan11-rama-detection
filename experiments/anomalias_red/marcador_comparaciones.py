"""Marcador de todas las comparaciones con intervalo bootstrap ya calculadas.

No entrena ni recalcula nada: lee los intervalos de las revisiones 17 a 21 (RAMA) y de la 20b
(Barcelona) y clasifica cada diferencia de F1 como gana, pierde o sin diferencia clara, según si
el intervalo excluye el 0. Sólo años de examen: 2025 y 2026 en la RAMA, 2018 y 2019 en Barcelona
(2024 participó en el desarrollo y se deja fuera).

Uso: python experiments/anomalias_red/marcador_comparaciones.py
Salida: results/anomalias_red_v1/marcador/
"""

from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
RAMA = RAIZ / "results" / "anomalias_red_v1"
BCN = RAIZ / "results" / "barcelona_paraad" / "examen_colab_2018_2019" / "resumen"
SALIDA = RAMA / "marcador"
ANIOS_RAMA = ("2025", "2026")


def fila(origen, ciudad, escenario, anio, tamano, punto, a, b, tipo, dif, bajo, alto):
    return dict(origen=origen, ciudad=ciudad, escenario=escenario, anio=str(anio),
                tamano=str(tamano), punto=punto, detector_a=a, detector_b=b, tipo=tipo,
                diferencia=dif, ic_bajo=bajo, ic_alto=alto)


def rama():
    filas = []
    # L0 único − V4S compartido, escenario original (revisión 18).
    d = pd.read_csv(RAMA / "revision18" / "intervalos.csv", dtype={"anio": str})
    d = d[(d.metrica == "f1") & d.anio.isin(ANIOS_RAMA)
          & (d.comparacion == "L0_unico − V4S_compartido")]
    for r in d.itertuples():
        filas.append(fila("rev18", "RAMA", "original", r.anio, f"δ{r.delta_pct}", r.punto,
                          "L0", "V4S", "justa (supervisados)", r.diferencia, r.ic_bajo, r.ic_alto))
    # L0 único − V4S compartido, escenarios B y A (revisión 19).
    for anio in ANIOS_RAMA:
        d = pd.read_csv(RAMA / "revision19" / anio / "intervalos.csv")
        for r in d[d.metrica == "f1"].itertuples():
            filas.append(fila("rev19", "RAMA", r.escenario, anio, f"δ{r.delta_pct}", r.punto,
                              "L0", "V4S", "justa (supervisados)", r.diferencia, r.ic_bajo,
                              r.ic_alto))
    # L0 único − R3, escenario original (examen final, revisión 17).
    d = pd.read_csv(RAMA / "examen_final" / "intervalos.csv", dtype={"anio": str})
    d = d[(d.metrica == "f1") & d.anio.isin(ANIOS_RAMA) & (d.comparacion == "L0_unico − R3")]
    for r in d.itertuples():
        filas.append(fila("rev17", "RAMA", "original", r.anio, f"δ{r.delta_pct}", r.punto,
                          "L0", "R3", "referencia (regla sin entrenamiento)", r.diferencia,
                          r.ic_bajo, r.ic_alto))
    # PARAAD − V4 y PARAAD − L0 (revisión 20); la segunda se invierte a L0 − PARAAD.
    d = pd.read_csv(RAMA / "revision20" / "examen" / "intervalos_paraad.csv", dtype={"anio": str})
    d = d[(d.metrica == "f1") & d.anio.isin(ANIOS_RAMA)]
    for r in d[d.comparacion == "PARAAD − V4"].itertuples():
        filas.append(fila("rev20", "RAMA", r.escenario, r.anio, f"δ{r.delta_pct}", r.punto,
                          "PARAAD", "V4", "justa (sin etiquetas)", r.estimacion, r.ic_bajo,
                          r.ic_alto))
    for r in d[d.comparacion == "PARAAD − L0_unico"].itertuples():
        filas.append(fila("rev20", "RAMA", r.escenario, r.anio, f"δ{r.delta_pct}", r.punto,
                          "L0", "PARAAD", "informativa (supervisado contra sin etiquetas)",
                          -r.estimacion, -r.ic_alto, -r.ic_bajo))
    # Error fijo en ppb (revisión 21).
    for anio in ANIOS_RAMA:
        for archivo, a, b, tipo in (
                ("intervalos.csv", "L0", "V4S", "justa (supervisados)"),
                ("intervalos_paraad.csv", "PARAAD", "V4", "justa (sin etiquetas)")):
            d = pd.read_csv(RAMA / "revision21" / anio / archivo)
            for r in d[d.metrica == "f1"].itertuples():
                filas.append(fila("rev21", "RAMA", "error fijo", anio, f"{r.a_ppb} ppb", r.punto,
                                  a, b, tipo, r.diferencia, r.ic_bajo, r.ic_alto))
    return filas


def barcelona():
    filas = []
    nombres = {"l0": "L0", "v4": "V4", "paraad": "PARAAD"}
    d = pd.read_csv(BCN / "diferencias_pareadas.csv", dtype={"ano": str})
    for r in d[d.estado == "con_ataque"].itertuples():
        x, y = r.comparacion.split("-")
        dif, bajo, alto = r.diferencia, r.inferior, r.superior
        if (x, y) == ("v4", "paraad"):  # se expresa como PARAAD − V4
            x, y, dif, bajo, alto = "paraad", "v4", -dif, -alto, -bajo
        tipo = ("justa (sin etiquetas)" if {x, y} == {"v4", "paraad"}
                else "informativa (supervisado contra sin etiquetas)")
        filas.append(fila("rev20b", "Barcelona", "original", r.ano, f"δ{r.delta}", r.punto,
                          nombres[x], nombres[y], tipo, dif, bajo, alto))
    return filas


def veredicto(r):
    if r.ic_bajo > 0:
        return "gana"
    if r.ic_alto < 0:
        return "pierde"
    return "sin diferencia clara"


def main():
    t = pd.DataFrame(rama() + barcelona())
    t["veredicto"] = t.apply(veredicto, axis=1)
    pequeno = {"δ10", "δ5", "5 ppb"}
    t["grupo_tamano"] = t.tamano.map(lambda s: "pequeña" if s in pequeno else "moderada o grande")
    t["par"] = t.detector_a + " − " + t.detector_b
    SALIDA.mkdir(parents=True, exist_ok=True)
    t.sort_values(["par", "ciudad", "escenario", "anio", "tamano", "punto"]).to_csv(
        SALIDA / "marcador_detalle.csv", index=False)
    claves = ["par", "tipo", "ciudad", "escenario", "grupo_tamano"]
    resumen = (t.groupby(claves + ["veredicto"]).size().unstack(fill_value=0)
               .reindex(columns=["gana", "sin diferencia clara", "pierde"], fill_value=0)
               .reset_index())
    resumen["total"] = resumen[["gana", "sin diferencia clara", "pierde"]].sum(axis=1)
    resumen.to_csv(SALIDA / "marcador_resumen.csv", index=False)
    with pd.option_context("display.width", 200, "display.max_rows", 200):
        print(resumen.to_string(index=False))
    print(f"\n{len(t)} comparaciones de F1 en total")


if __name__ == "__main__":
    main()
