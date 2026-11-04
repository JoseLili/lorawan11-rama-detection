# S1: cierre incompleto por sesión ausente

Consulta del 2026-11-04 01:47 UTC: la sesión `tinto-s1-r1-20261031` no aparece y el inventario del CLI no contiene sesiones activas. El recolector local anterior tampoco está disponible. Se intentó una descarga puntual, sin obtener respaldos nuevos.

Se conserva la primera corrida completa: 9 épocas, mejor época 1, val_loss 0.04715469479560852. El archivo corrida1.tar.gz tiene 1689676 bytes y SHA256 1ed62542ae62b97ee543a807bdfb507a076533528ac1e6fab82cbee2979c68a0; ambos se volvieron a comprobar contra corrida1.json. Se extrajo con filtro seguro en recuperacion_parcial_20261104, conservando modelo, historia, puntajes y registros.

La segunda corrida fue observada por última vez en época 6, con 5 completadas. No se recuperaron su resultado ni el archivo final. No es posible afirmar si terminó antes de desaparecer la sesión, ni determinar la causa de su desaparición.

El experimento queda incompleto: no se puede comprobar la igualdad entre ambas corridas exigida por el protocolo. No se ejecutó la evaluación comparativa ni se infirió F1 a partir de la pérdida. No se relanzaron entrenamientos ni se modificó la configuración. No había una VM activa que detener. Se cierra el monitor porque no quedan resultados remotos accesibles; cualquier reintento requiere nueva autorización.
