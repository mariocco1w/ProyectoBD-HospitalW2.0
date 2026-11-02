# Auditoría final — Hospital W 2.0

**Fecha:** 2 de noviembre de 2026  
**Base:** `HospitalW2` en SQL Server Express, autenticación de Windows.  
**Código revisado:** `HospitalWeb/app.py`, `templates/index.html`, `static/app.js`, `HospitalW2.sql`, `Migracion_IdempotenciaMovimiento.sql`, `ValidacionReglasHospitalDB.sql` y `HospitalWeb/tests/`.  
**Criterio:** una operación solo figura como aprobada si se ejecutó y, cuando persiste, se contrastó con SQL Server.

Esta pasada no reconstruyó el proyecto ni modificó tablas. No encontró un defecto de RF1–RF4 que obligara a cambiar la lógica de la aplicación. Sí amplió la suite con una prueba de rechazos y de aislamiento, y esa prueba pasó.

## Estado general

El panel cubre alta, consulta y modificación de personal, pacientes, admisiones, contactos e insumos; la baja lógica de empleados; el ingreso y el egreso de hospitalización; y los movimientos de inventario que actualizan la existencia en la misma transacción. La telemetría sigue siendo de consulta. Los catálogos se usan como listas y no tienen mantenimiento propio.

La suite quedó en **14 aprobadas y 0 fallidas** (`evidencias/pytest_auditoria_final.txt`). Los conteos reales antes y después fueron los mismos. Quedaron cero filas con prefijo `QAFIN`.

## RF1 — Empleados

| Operación | Resultado | Evidencia |
|---|---|---|
| Crear | Aprobada. La fila queda en `Empleado`. | `test_rf1_alta_edicion_nss_duplicado_y_baja_logica` |
| Consultar | Aprobada. El inactivo sigue en el listado y sale de `empleados_activos`. | El mismo test |
| Modificar | Aprobada. Nombre, apellido, turno y especialidad se leyeron de SQL después del PUT. | El mismo test |
| NSS duplicado | Aprobada en el alta y en la edición. HTTP 409, mensaje en español, sin texto del controlador. | Tests RF1 y `test_rechazos_y_borrado_no_alteran_registros_ajenos` |
| Turno inexistente | Aprobada. HTTP 409 y no se crea la segunda fila. | Test de rechazos |
| Baja lógica | Aprobada. `DELETE` responde 405. Dos bajas seguidas dejan `estado_activo` en falso. | Test RF1 |
| Historial | Aprobada. Un médico con una cita de prueba no puede pasar a enfermería. El rol sigue siendo `Medico` y la cita se elimina solo en la limpieza `QAFIN`. | `test_rf1_no_cambia_el_rol_de_un_medico_con_citas`, disparador `TR_Empleado_ConCitas_Medico` |
| Interfaz | Aprobada. La tabla ofrece Editar y Dar de baja, y no ofrece Eliminar. | Panel en `http://127.0.0.1:5000` |

## RF2 — Pacientes, admisiones y contactos

| Operación | Resultado | Evidencia |
|---|---|---|
| Crear y consultar paciente | Aprobada. | Tests RF2 y de aislamiento |
| Modificar | Aprobada. Apellido, dirección, teléfono y médico se leyeron de `Paciente`. | `test_rf2_edicion_dpi_admision_y_contacto` |
| DPI duplicado | Aprobada. HTTP 409. | El mismo test |
| Familiar o médico inexistente | Aprobada. HTTP 409. | El mismo test |
| Admisión | Aprobada. Se registra y, al editar el médico, `FechaRegistro` permanece `2026-11-02 08:15:00`. Un paciente 999999 se rechaza. | Tests RF2 y de rechazos |
| Contacto | Aprobada. La edición cambia familiar y parentesco. Repetir la pareja paciente-familiar responde 409. Un parentesco 999999 responde 409. | Los mismos tests |
| Borrado | Aprobada. El paciente con admisión no se elimina. El paciente de prueba sin historial sí se elimina. El otro paciente de prueba, su admisión y un paciente real usado como ancla siguen en SQL. El total de pacientes cuyo DPI no empieza por `QAFIN` no cambió. | `test_rechazos_y_borrado_no_alteran_registros_ajenos` |
| Interfaz | Aprobada. La tabla de pacientes ofrece Editar. | Panel en ejecución |

Editar la ficha del paciente no ejecuta `UPDATE` sobre `ADMISION` ni sobre `Hospitalizacion`.

## RF3 — Hospitalización y camas

| Operación | Resultado | Evidencia |
|---|---|---|
| Consultar | Aprobada. La API devuelve ingreso, paciente, cama, sala, fechas y estado. La pantalla mostró 103 filas y 100 activas. | Test RF3 y panel |
| Asignar cama ocupada real | Aprobada. HTTP 409 y cero hospitalizaciones con motivo `QAFIN`. | `test_rf3_cama_ocupada_asignacion_controlada_y_cierre` |
| Asignar cama libre de prueba | Aprobada. Estado `Activa` y fecha de ingreso generada por el `DEFAULT`. | El mismo test, leído en SQL |
| Segunda asignación a la misma cama | Aprobada. HTTP 409 y una sola fila activa. | El mismo test |
| Dos asignaciones simultáneas | Aprobada. Un hilo terminó en ok y el otro en rechazo. Quedó una activa. | `test_rf3_dos_asignaciones_simultaneas` |
| Egreso | Aprobada. Estado `Finalizada`, `fecha_hora_salida_real` con valor, segundo cierre HTTP 409, la cama vuelve a `GET /api/camas/disponibles` y la fila sigue en el historial. | Test RF3 |
| Sin camas reales | Aprobada. El selector dice «No hay camas disponibles» y el botón de ingreso está deshabilitado. SQL confirma 0 camas libres. | Panel y `evidencias/integridad_sql.txt` |

La ocupación de las 100 camas reales no se borró para fabricar una cama libre. La asignación exitosa usó una cama `QAFIN` que la limpieza eliminó.

No hay una acción de interfaz para el estado `Cancelada`, que sí admite el `CHECK`. El cierre operativo usa `Finalizada`, que es el valor que exige fecha de salida y libera la cama.

## RF4 — Inventario

| Operación | Resultado en SQL | Evidencia |
|---|---|---|
| Alta y edición de insumo | El nombre editado se leyó de `Insumo`. | `test_rf4_edicion_y_movimientos_actualizan_stock` |
| Entrada de 5 sobre 10 | Existencia 15 | El mismo test |
| Salida de 2 | Existencia 13 | El mismo test |
| Devolución de 1 | Existencia 14 | El mismo test |
| Ajuste a 8 | Existencia 8. El ajuste sustituye la existencia por la cantidad contada. | El mismo test |
| Cantidad 0 y negativa | HTTP 400, mensajes distintos | El mismo test y `test_reglas.py` |
| Salida de 50 con existencia 8 | HTTP 400 y la existencia sigue en 8 | Test RF4 |
| Entrada que supera el máximo | HTTP 400 | Test RF4 |
| Proveedor 999999 | HTTP 409 | Test RF4 |
| Reintento con la misma clave | HTTP 200, `duplicado: true`, la existencia no suma otra vez | Test RF4 |
| Dos salidas simultáneas de todo el stock | Una ok, una rechazo, existencia 0 | `test_rf4_salidas_simultaneas_no_dejan_stock_negativo` |
| Borrar un movimiento | HTTP 405 | Test RF4 |
| Stock real | La suma de existencias de insumos que no son `QAFIN` no cambió durante la prueba de aislamiento. | Test de rechazos |
| Interfaz | El texto del formulario describe entrada, devolución, salida y ajuste. La tabla de movimientos no ofrece Eliminar. | Panel |

Los 17 movimientos que ya existían no se reaplicaron sobre el stock.

## Conteos

Orden: Paciente, Empleado, Insumo, ADMISION, contactos, movimientos, Hospitalizacion, activas, Cama, Cita, camas libres.

| Momento | Valores |
|---|---|
| Antes de esta pasada y después de limpiar `QAFIN` | 108, 18, 18, 17, 9, 17, 103, 100, 100, 18, 0 |
| Después de las 14 pruebas | Los mismos. `QAFIN` = 0 |

Fuente: `evidencias/integridad_sql.txt`, tomada al cerrar la pasada.

## Integridad de SQL Server

Consulta en vivo, sin cambiar el esquema:

| Objeto | Observado |
|---|---|
| Tablas `dbo` | 28, incluida `sysdiagrams`. El modelo de negocio visible tiene 27. No se redujo ni se amplió. |
| Primary keys | 28 |
| Foreign keys | 20. Ninguna usa borrado o actualización en cascada. |
| Unique | 15 restricciones, más el índice filtrado de cama activa y el de idempotencia |
| CHECK | 12 |
| DEFAULT | 15 |
| Disparadores | `TR_Cita_SoloMedicos`, `TR_Empleado_ConCitas_Medico` |
| Huérfanos de empleado-turno, paciente-familiar, hospitalización, movimiento e insumo | 0 |
| Existencia negativa o mayor que el máximo | 0 |
| Dos hospitalizaciones activas en la misma cama | 0 |
| Activa con salida, o finalizada sin salida | 0 |

`UX_Hospitalizacion_Cama_Activa` y `UX_MOVIMIENTO_Idempotencia` siguen presentes. `ClaveIdempotencia` mide 64 caracteres. La migración aplicada es aditiva y no se volvió a ejecutar.

## Errores encontrados y correcciones

No apareció un fallo de persistencia, de concurrencia ni de validación en RF1–RF4. Por eso `app.py`, el HTML y el JavaScript no se modificaron en esta pasada.

Lo que sí se agregó fue `test_rechazos_y_borrado_no_alteran_registros_ajenos`, porque la suite anterior no comprobaba de forma explícita el NSS duplicado en el alta, el turno inexistente, la admisión con paciente inexistente, el parentesco inexistente ni que borrar un paciente de prueba dejara intactos a los demás. La prueba pasó a la primera ejecución.

## Funcionalidades aprobadas

RF1 completo en el alcance del panel: alta, consulta, edición, baja lógica, NSS, turno y conservación de citas.  
RF2 completo en ese alcance: paciente, admisión, contacto, DPI, llaves y borrado que no arrastra registros ajenos.  
RF3 completo para consulta, rechazo de cama ocupada, asignación controlada, concurrencia, ingreso automático y egreso a `Finalizada`.  
RF4 completo para edición, los cuatro tipos de movimiento, topes, concurrencia e idempotencia.

## Funcionalidades pendientes

No bloquean los cuatro requerimientos anteriores y no se marcaron como aprobadas:

- No hay pantallas para mantener familiares, médicos externos, proveedores, turnos, especialidades ni camas.
- No hay alta ni edición de citas. El disparador de citas sí se ejerció con un insert de prueba.
- La telemetría no se captura desde el panel.
- Un movimiento ya guardado no se edita ni se borra.
- No hay acción para pasar una hospitalización a `Cancelada`.
- Con las 100 camas reales ocupadas, un ingreso nuevo sobre datos reales sigue rechazándose hasta que se finalice una hospitalización existente. Eso es el comportamiento correcto, no una cama libre pendiente de crear.

## Interfaz

En el panel en ejecución, la pantalla de acceso no contiene la clave en el HTML. El ingreso válido abre la aplicación. Hospitalización muestra la ausencia de camas y deshabilita el alta. Empleados ofrece editar y dar de baja. Pacientes e insumos ofrecen editar. Movimientos no ofrece eliminar.

No se recorrió con el ratón cada formulario. Las operaciones de guardado de paciente, admisión, contacto, insumo y hospitalización de prueba se ejecutaron por la misma API que esos formularios llaman, y el resultado se leyó en SQL Server.

## Evidencias

- `evidencias/pytest_auditoria_final.txt` — 14 aprobadas, 0 fallidas, 2.44 s.
- `evidencias/integridad_sql.txt` — conteos, llaves, índices y huérfanos.
- `evidencias/ui-login.png`, `ui-hospitalizacion.png`, `ui-empleado-inactivo.png` — capturas de la implementación vigente. Esta pasada confirmó los mismos estados en el panel vivo y no generó capturas nuevas.
- Informes previos, que no se reescribieron: `Informe_Pruebas_CRUD_HospitalW2.md`, `Informe_Auditoria_Final_HospitalW2.md`, `Informe_Tecnico_HospitalW2.md`, `Matriz_Cumplimiento_RF_HospitalW2.md`.

## Limitaciones

La clave del panel sigue pudiendo definirse con `HOSPITAL_ADMIN_PASS`. Si esa variable no existe, el proceso usa el valor local de `app.py`. No se copia aquí. La conexión a SQL Server no usa usuario ni clave del motor.

La prueba de asignación exitosa y la de concurrencia de camas no ocuparon una de las 100 camas reales. Usaron una cama creada con prefijo `QAFIN` y la limpieza la eliminó. El rechazo sobre una cama real ocupada sí se ejecutó.

## Conclusión para la Fase I

RF1, RF2, RF3 y RF4 están implementados y verificados contra SQL Server, con 14 pruebas aprobadas y los conteos reales intactos. La Fase I de esos cuatro requerimientos puede entregarse. No se declara cerrado lo que la sección de pendientes enumera, porque esas piezas siguen fuera del panel.
