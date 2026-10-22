# Observador de recursos de procesos en Windows

`Backend/scripts/windows_resource_observer.py` permite medir procesos nativos sin instalar paquetes ni modificar procesos, servicios, bases o configuración de Windows. Se utiliza para completar la instrumentación de P16.

## Identidad y alcance

El llamador entrega una raíz por grupo: PID y fecha de creación de Windows (`stamp`). Para la aplicación debe usar el supervisor de `services.json` y verificar también las identidades de sus componentes. Para PostgreSQL debe comprobar el PID, directorio y puerto de `postmaster.pid`, contrastar su fecha con la creación del proceso nativo y demostrar que el backend de la conexión SQL pertenece a sus descendientes. La conexión debe validar además base, puerto, OID, revisión y rol ordinario. Un proceso llamado `postgres.exe` por sí solo no identifica el clúster correcto.

Se incluye cada raíz y sus descendientes presentes en el inventario con ascendencia válida. No se mezclan otros clústeres PostgreSQL. Si un supuesto hijo fue creado antes del proceso padre actual, se excluye esa rama y se registra en `excluded_stale_parent_links`; el enlace numérico no demuestra propiedad del proceso. La memoria, identidad, ejecutable y contadores se leen desde el mismo handle. Se vuelve a inventariar el árbol y comprobar sus fechas de creación antes de aceptar la muestra. La comprobación de edades presupone un reloj Windows consistente; las exclusiones quedan visibles para revisión.

`pg_postmaster_start_time()` y la creación del proceso nativo se registran por separado. En este equipo sus valores difieren; no se presupone igualdad ni se atribuye una causa. La ascendencia del backend SQL y la identidad del PID nativo vinculan la medición con el clúster utilizado.

## Uso desde un observador de carga

```python
from pathlib import Path
from scripts.windows_resource_observer import WindowsObserver

observer = WindowsObserver()
# Las raíces deben haber sido verificadas por el llamador.
roots = {
    "application": {"pid": supervisor_pid, "stamp": supervisor_stamp},
    "postgres_cluster": {"pid": postmaster_pid, "stamp": postmaster_stamp},
    "load_generator": observer.process(generator_pid),
}
sample = observer.sample_with_retries(roots, Path.cwd(), max_attempts=8)
```

`sample()` lee los recursos de cada PID/fecha una vez durante la adquisición y comprueba después identidad con derechos limitados. Si aparecen procesos nuevos o se reutiliza un PID, completa solo sus lecturas hasta obtener un inventario final consistente: máximo ocho pasadas internas, registradas en `inventory_passes` y `reconciled_inventory_changes`. Una lectura faltante, una raíz reemplazada o cambios que no convergen no acreditan una captura.

`sample_with_retries()` permite entre uno y ocho intentos de adquisición y espera 50 ms entre ellos; cada adquisición conserva su límite de ocho pasadas internas. Solo reintenta lecturas incompletas o cambios del inventario; una identidad de raíz cambiada falla inmediatamente. Las adquisiciones descartadas quedan en `discarded_attempts`, con grupo y diagnósticos disponibles; no se contabilizan como muestras completas. Si se agotan los intentos, registrar el fallo y detener el ensayo, sin declarar cumplimiento.

El informe debe incluir también el generador de carga, duración de adquisición, separación máxima entre muestras, adquisiciones descartadas, errores y resguardos de memoria/disco. Los grupos deben ser disjuntos antes de sumar sus recursos.

## Interpretación

- La cobertura comprende los árboles del inventario final de cada muestra aceptada. Los contadores se leen durante la adquisición y registran `measured_monotonic_seconds`; no existe un instante atómico común de todas sus lecturas. No acredita todos los procesos transitorios que nacieron y terminaron entre muestras, ni máximos continuos.
- Los bytes privados son memoria privada comprometida por proceso. Su suma no equivale a memoria física exclusiva. Los working sets pueden compartir páginas y tampoco deben presentarse como memoria exclusiva.
- La memoria física disponible corresponde al sistema completo; incluye efectos de otros programas del equipo.
- CPU e I/O son contadores acumulados por proceso. I/O puede incluir actividad ajena al disco físico; no representa por sí solo utilización de disco o CPU por intervalo.
- Esta herramienta completa instrumentación. La aceptación de carga requiere además perfil acordado, resultados, latencias, escrituras, exclusión y fallos bajo el alcance exigido.

## Comprobación focalizada

Desde `Backend`, con el entorno de desarrollo:

```powershell
./venv/Scripts/python.exe -m pytest -q tests/test_windows_resource_observer.py -p no:cacheprovider
```

Las pruebas cubren selección de árboles, exclusión de otro clúster, PIDs inválidos/reutilizados, ramas excluidas con constancia, lecturas faltantes, reconciliación de procesos nuevos/reutilizados sin releer los demás, cambios continuos con fallo acotado, reintentos y rechazo inmediato de una raíz reemplazada. En Windows se verifica además la lectura nativa del proceso de pruebas; en otros sistemas se comprueba el rechazo explícito de la API Windows.
