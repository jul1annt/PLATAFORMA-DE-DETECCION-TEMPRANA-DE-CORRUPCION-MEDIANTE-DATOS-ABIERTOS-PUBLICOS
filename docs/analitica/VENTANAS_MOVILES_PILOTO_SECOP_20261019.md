# Contraste de ventanas móviles con SECOP local

## Alcance comprobado

Se revisaron las **1.698 filas** de la cohorte previamente utilizada para IQR: categoría `V1.80161500`, modalidad directa con ofertas y publicación en 2017. La selección no utilizó puntajes. La revisión de claves y fechas se realizó por identificadores locales, en lotes de 100, mediante consultas de solo lectura al OID 24577; tardó 7,28 segundos.

| Requisito observado | Filas |
|---|---:|
| Cohorte revisada | 1.698 |
| Fecha de adjudicación presente | 1.390 |
| Claves de entidad/proveedor y fecha de adjudicación presentes | 17 |
| De esas 17, identidad fuente/proceso/adjudicación ambigua en el universo raw | 4 |
| Objetivos admitidos para el piloto móvil | 13 |

No se completaron identidades por nombre ni se alteraron los registros. La disponibilidad de fecha de adjudicación no es el requisito de fecha utilizado en el IQR anterior, que agrupó por publicación; sus cifras no deben confundirse. La cobertura de claves observada corresponde a este grupo concreto, no es una estimación nacional.

## Historia adquirida

Para cada objetivo admisible se leyeron **todas las filas almacenadas de su par normalizado entidad/proveedor**, de todas las fechas, modalidades, categorías y fuentes presentes en `contratos_procesados`, enlazadas con `raw_secop`. Las consultas sumaron 21 filas entre los 13 pares. Cada consulta tenía límite de seguridad de 20.001 filas; ninguna lo alcanzó. Se verificó la identidad fuente/proceso/adjudicación con una búsqueda global raw limitada a dos coincidencias para detectar ambigüedad.

La adquisición de esos pares tardó aproximadamente **4,14 segundos**. Se conservaron entradas privadas con hashes para repetir el análisis sin nuevas consultas. No se incluyeron NIT ni nombres en el informe de resultados compartido; sí permanecen los identificadores oficiales de trazabilidad que correspondan.

**La completitud comprobada es la de estos pares según las claves almacenadas en el universo normalizado local.** No demuestra cobertura de contratación nacional, de filas sin normalizar ni de identidades ausentes o escritas de otra forma que no hayan sido conciliadas. El informe conserva expresamente este alcance. No se ejecutó una carga nueva ni una actualización de la fuente.

## Resultado

Los **13 objetivos** registraron cero procesos previos de reiteración en 30 días y cero directos en 90 días, dentro de ese universo. El proceso objetivo se excluye por completo. Las adjudicaciones posteriores al objetivo no se utilizan; tampoco los eventos anteriores a la ventana.

El resultado puede reproducirse íntegramente desde las entradas guardadas. No demuestra ausencia de corrupción ni permite imputar cero al resto de la cohorte. Son pares con historia escasa; este piloto no sirve para estimar la frecuencia de señales ni su rendimiento predictivo. No produjo puntajes completos de riesgo: IQR y competencia siguen separados de estos diagnósticos.

Los importes y la zona temporal originales no se verificaron documentalmente. Se utilizan los instantes que conserva PostgreSQL para el cálculo descriptivo. La tabla raw no suministra una moneda explícita en el modelo actual; no se inventó COP ni se declaró un importe monetario agregado completo. Ningún resultado es elegible para entrenamiento histórico.

El [informe estructurado](VENTANAS_MOVILES_COHORTE_2017_20261019.json) contiene resultados, alcance, evidencia, hashes y exclusiones. El [recibo de validación](VALIDACION_VENTANAS_MOVILES_PILOTO_20261019.json) enlaza adquisición, implementación, repetición y pruebas.

## Modalidad y competencia

La [guía oficial CCE-SEC-GI-17, versión del 20/04/2022](https://operaciones.colombiacompra.gov.co/sites/cce_public/files/cce_step/cce-sec-gi-17guiasecopii_eepccontrataciondirectaconofertas20-04-2022.pdf), páginas 3 a 5, identifica el módulo de contratación directa con ofertas y su función de recibir documentación y gestionar el contrato. Se revisó únicamente la correspondencia exacta de esa etiqueta para este piloto; no se utilizó una búsqueda genérica de la palabra «directa» para habilitar modalidades desconocidas.

Esa clasificación describe el tipo de módulo del registro actual. Una guía de 2022 no reconstruye por sí sola el conocimiento disponible en 2017. La presencia de «ofertas» tampoco valida el campo de número de oferentes ni acredita competencia efectiva. Por ello el indicador de competencia permanece pendiente y no se asignó ausencia de señal a partir de esta guía.

## Ajustes y comprobaciones de código

La exclusión del proceso objetivo ahora ocurre antes de examinar fechas de sus demás adjudicaciones: una fecha ausente de una adjudicación del mismo proceso no contamina el contexto que expresamente debe excluirse. El informe conserva el marco temporal y universo declarado, junto con la advertencia de que no se comprobó cobertura fuera de él.

Pasaron **88 pruebas enfocadas**, incluidas 32 del módulo móvil y CLI. Cubren ventanas inclusivas, zonas horarias, adjudicaciones múltiples, fuentes diferentes, identidades inválidas, versiones contradictorias, datos monetarios faltantes, alcance de población, reproducibilidad y conservación de salida. Son pruebas enfocadas, no una nueva batería completa del backend. El recibo anterior de 86 pruebas se conserva como antecedente de una revisión anterior del código.

## Próximo paso

Comprobar la equivalencia con consultas SQL en un entorno aislado, usando también ventanas con señales positivas, fechas ausentes, procesos con varias adjudicaciones e identidades ambiguas. Este piloto de ceros no basta para probar esa equivalencia. Después se podrán combinar resultados compatibles por identidad, corte y alcance, verificar competencia y repetir sensibilidad de pesos sobre familias corregidas.

Los coeficientes históricos y la referencia base de un punto por familia no se modificaron con este diagnóstico. No hubo escritura de datos operativos, entrenamiento, activación, publicación nueva o contacto con terceros.
