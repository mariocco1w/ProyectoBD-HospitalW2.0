# Informe técnico — Hospital W 2.0

## 1. Qué es el sistema

Hospital W 2.0 es un panel web para la base `HospitalW2`. Un solo proceso Flask, en `HospitalWeb/app.py`, entrega `templates/index.html` y atiende la API JSON. `static/app.js` llama esa API. Los datos viven en SQL Server Express y se leen con pyodbc y autenticación de Windows. No hay una segunda base ni una reconstrucción del esquema.

Para ejecutarlo: entrar a `HospitalWeb`, instalar `requirements.txt` y correr `python app.py` o `iniciar.bat`. El panel escucha en `http://127.0.0.1:5000`. El usuario y la clave se definen con `HOSPITAL_ADMIN_USER` y `HOSPITAL_ADMIN_PASS`.

## 2. Módulos y operaciones

| Módulo | Crear | Consultar | Modificar | Baja |
|---|---|---|---|---|
| Pacientes | Sí | Sí | Sí: datos demográficos, dirección, teléfono, familiar y médico | Solo si no tiene historia asociada |
| Admisiones | Sí | Sí, historial incluido | Paciente y médico. `FechaRegistro` no se actualiza | La operación previa de borrado de una admisión se mantiene |
| Contactos de emergencia | Sí | Sí | Sí, si la pareja paciente-familiar no existe ya | Se mantiene el borrado de la asociación |
| Hospitalización | Sí, solo en cama libre | Sí, con filtro de paciente y estado | El egreso pasa de `Activa` a `Finalizada` | No hay borrado. El egreso conserva la fila |
| Empleados | Sí | Sí, activos e inactivos | Sí | Lógica: `estado_activo = 0`. El `DELETE` responde 405 |
| Insumos | Sí | Sí | Nombre, tipo, costos, existencias y proveedor | Rechazada si ya hay movimientos |
| Movimientos | Sí, y actualiza la existencia | Sí | No. El libro no se corrige editando la fila | `DELETE` responde 405 |
| Telemetría | No | Sí | No | No |

Los catálogos de familiar, médico, proveedor, turno, especialidad y parentesco se usan como listas. No tienen pantallas de mantenimiento. Las camas no se administran como catálogo: el ingreso solo ofrece las que no tienen hospitalización activa.

## 3. Reglas de negocio

**Personal.** NSS único, también al editar, sin contar al mismo empleado. El turno es obligatorio y debe existir. La especialidad, si se envía, debe existir. Un empleado con citas no puede dejar de ser médico: lo impide `TR_Empleado_ConCitas_Medico` (error 51002) y la API responde 409. La baja no borra citas ni asignaciones y puede invocarse otra vez sobre el mismo id.

**Pacientes.** DPI único al crear y al editar. Familiar y médico deben existir. Cambiar la ficha del paciente no reescribe sus admisiones ni sus hospitalizaciones.

**Admisiones y contactos.** La admisión exige paciente. El médico externo puede quedar vacío si el esquema lo permite. El contacto exige paciente, familiar y parentesco, y no repite la pareja paciente-familiar.

**Hospitalización.** Estados usados, que son los que admite la tabla: `Activa` al ingresar y `Finalizada` al egresar. No se inventó un estado nuevo. El ingreso no envía fecha ni estado: usan el `DEFAULT` (`SYSDATETIME()` y `Activa`). La cama se bloquea en la transacción y el índice `UX_Hospitalizacion_Cama_Activa` impide dos filas activas. Si no hay cama libre, la interfaz deshabilita el alta y el servidor rechaza la cama ocupada. Cerrar dos veces la misma hospitalización responde 409. La fila finalizada permanece en el historial y la cama vuelve a salir en las disponibles.

**Inventario.** La cantidad debe ser mayor que cero. Entrada y devolución suman. Salida resta y no puede dejar la existencia en negativo. Ajuste deja la existencia igual a la cantidad contada; no es un delta con signo, porque la columna `Cantidad` solo acepta valores positivos y el movimiento histórico de referencia es un conteo físico. Nadie reprocesó los 17 movimientos que ya estaban guardados. Existencia y máximo siguen limitados por el `CHECK` del insumo. Proveedor obligatorio. Código único. El movimiento y el `UPDATE` de `stock_existencia` comparten transacción; si uno falla, no queda el otro. Dos salidas simultáneas bloquean la fila del insumo. Una clave de idempotencia repetida devuelve el movimiento existente con `duplicado: true` y no mueve el stock otra vez.

## 4. Conexión

`app.py` arma la cadena con `HOSPITAL_DRIVER`, `HOSPITAL_SERVER`, `HOSPITAL_DB` y `HOSPITAL_TRUSTED`. Si no hay variables, usa Driver 18, `.\SQLEXPRESS`, `HospitalW2` y autenticación de Windows. Cada operación abre la conexión, ejecuta SQL parametrizado y confirma o revierte con el administrador de contexto. Los errores de integridad se traducen antes de llegar al navegador.

La única migración aplicada es aditiva: `ClaveIdempotencia` en `MOVIMIENTO_INVENTARIO`, más su índice único filtrado. Las filas viejas quedan con NULL y el índice no las considera.

## 5. Pruebas ejecutadas y dónde se ejecutaron

**Directo en SQL Server, a través de pytest y de la API.** `HospitalWeb/tests/test_integracion.py` crea filas `QAFIN`, las lee con `SELECT`, comprueba stock, estados, fechas de salida y el rechazo de la segunda cama, y al terminar borra solo ese prefijo. La corrida final fue 13 aprobadas y 0 fallidas. El detalle está en `evidencias/pytest_resultado.txt`.

**Sin base de datos.** `test_reglas.py` cubre el cálculo de stock, los mensajes de cantidad y la traducción de un NSS duplicado.

**En la interfaz.** Con el proceso reiniciado se comprobó la pantalla de acceso, el mensaje de clave incorrecta, el ingreso al panel, la hospitalización sin camas libres (103 registros y 100 activas) y el alta, la edición y la baja de un empleado de prueba. Capturas en `evidencias/`. Esas pruebas de pantalla no recorrieron cada formulario de paciente, admisión, contacto e insumo: esas operaciones quedaron cubiertas por la API que esos formularios llaman.

**Conteos al cerrar**, leídos en SQL Server y guardados en `evidencias/conteos_sql.txt`: 108, 18, 18, 17, 9, 17, 103, 100 y 18, con 100 hospitalizaciones activas y cero filas `QAFIN`.

## 6. Resultado

El panel ya registra, consulta, modifica y da de baja al personal; modifica pacientes, admisiones y contactos; hospitaliza solo en cama libre y cierra el ingreso; y hace que cada movimiento de inventario mueva la existencia en la misma transacción. La línea base de datos preexistentes se conservó.
