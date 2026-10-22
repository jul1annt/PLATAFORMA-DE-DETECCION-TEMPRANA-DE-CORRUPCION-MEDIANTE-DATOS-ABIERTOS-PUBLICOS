# Política compartida al registrar modelos

El registro del resultado de entrenamiento aplica ahora la misma validación completa que la aprobación cuando el informe declara `validated=true`. Comprueba etapa, versión, tipo booleano del estado, hashes y política de particiones. Un candidato que no superó la comparación estadística puede conservarse con `validated=false`. La reanudación vuelve a comprobar los archivos almacenados antes de registrarlos.

Siete variantes sintéticas cubren aprobación, candidato, auditoría ausente o alterada, etapa y versión incompatibles y aprobación inconsistente. Incluyen reanudación sin duplicar registros ni repetir el proceso hijo simulado. Estas pruebas verifican persistencia; no acreditan un entrenamiento judicial real.

La primera ejecución específica tuvo dos fallos por colisión del identificador de la propia preparación de datos sintéticos con una restricción única existente. Se corrigió la preparación asignando una versión distinta y recalculando hashes. La repetición pasó **72 pruebas**. La suite completa posterior pasó **613 pruebas en 63,41 segundos**, sin errores ni omisiones.

La [validación consolidada](VALIDACION_REGISTRO_MODELOS_20261019.json) conserva identificador de ejecución, hash JUnit y hashes del código. Sus consultas de solo lectura comprobaron limpieza de los datos sintéticos y ausencia de modelos reales, además del esquema original `3c19a8f7e2d0`. No se repitieron las cargas de volumen ni migraciones ya comprobadas. La publicación nueva continúa pendiente de evidencia judicial suficiente y evaluación independiente.
