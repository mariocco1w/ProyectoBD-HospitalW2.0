# Informe de auditoría final — Hospital W 2.0

**Fecha:** 2 de noviembre de 2026  
**Relación con la línea base:** este informe no sustituye `Informe_Pruebas_CRUD_HospitalW2.md`. Ese documento conserva los 85 resultados anteriores a las correcciones (58 aprobadas, 4 fallidas, 3 parciales y 20 no implementadas).

## A. Información general

| Dato | Valor |
|---|---|
| Proyecto | Hospital W 2.0 |
| Objetivo | Completar la gestión de personal, la admisión de pacientes, la hospitalización con asignación de camas y el inventario, y comprobarlo contra SQL Server. |
| Arquitectura | Aplicación web monolítica. Flask entrega la página y la API. El navegador usa HTML, CSS y JavaScript. |
| Tecnologías | Python 3, Flask, pyodbc, HTML, CSS, JavaScript. |
| Base de datos | `HospitalW2` en SQL Server Express, instancia local, autenticación de Windows, ODBC Driver 18. |
| Repositorio | https://github.com/mariocco1w/ProyectoBD-HospitalW2.0 |
| Alcance | RF1, RF2, RF3 y RF4, más los defectos de sesión y de mensajes ya detectados. No se reconstruyó la base ni se borraron datos preexistentes. |

## B. Estado inicial

La auditoría de la misma fecha, conservada en `Informe_Pruebas_CRUD_HospitalW2.md`, ejecutó 85 pruebas:

| Resultado | Cantidad |
|---|---:|
| Aprobadas | 58 |
| Fallidas | 4 |
| Parciales | 3 |
| No implementadas | 20 |

Defectos que esa auditoría dejó abiertos:

- **RF1.** No había edición. No había baja lógica. `DELETE` borraba al empleado.
- **RF2.** No había edición de paciente, admisión ni contacto.
- **RF3.** No había módulo de hospitalización en la interfaz. Las 100 camas reales ya tenían una hospitalización activa. El índice `UX_Hospitalizacion_Cama_Activa` sí impedía dos activas en la misma cama.
- **RF4.** No había edición de insumos. Entrada y salida se guardaban y no cambiaban `stock_existencia`. Una salida mayor que la existencia se aceptaba.
- **Seguridad y mensajes.** La pantalla de acceso mostraba la clave de demostración. Una clave incorrecta se presentaba como sesión expirada. Un NSS duplicado mostraba el texto del controlador ODBC. La cantidad cero se describía como cantidad negativa.

Conteos de esa línea base, iguales al cierre de esta corrección: Paciente 108, Empleado 18, Insumo 18, ADMISION 17, contactos 9, movimientos 17, Hospitalizacion 103 (100 activas), Cama 100, Cita 18.

## C. Modificaciones realizadas

### C.1 Personal (RF1)

- **Problema.** Alta y consulta sí; edición y baja lógica no. El borrado era físico.
- **Archivos.** `HospitalWeb/app.py`, `HospitalWeb/static/app.js`, `HospitalWeb/templates/index.html`.
- **Rutas.** `PUT /api/empleados/<id>`, `POST /api/empleados/<id>/baja`. `DELETE /api/empleados/<id>` responde 405.
- **Solución.** El formulario de alta se reutiliza precargado. El NSS se valida único excluyendo al propio empleado. Turno y especialidad deben existir. La baja ejecuta `UPDATE estado_activo = 0` y puede repetirse sin error. Los empleados inactivos siguen en la consulta y salen de `empleados_activos`.
- **Tablas.** `Empleado`, `Turno`, `Especialidad`. El disparador `TR_Empleado_ConCitas_Medico` sigue impidiendo quitar el rol médico a quien tiene citas.
- **Interfaz.** Cada fila ofrece Editar y Dar de baja, con confirmación. Ya no ofrece eliminar.

### C.2 Pacientes, admisiones y contactos (RF2)

- **Problema.** No existía modificación.
- **Rutas.** `PUT /api/pacientes/<id>`, `PUT /api/admisiones/<id>`, `PUT /api/contactos/<id>`.
- **Solución.** El paciente actualiza DPI, nombre, apellido, nacimiento, género, dirección, teléfono, adulto mayor, familiar y médico externo. No se tocan filas de `ADMISION` ni de `Hospitalizacion`. La admisión solo cambia paciente y médico; `FechaRegistro` queda fuera del `UPDATE`. El contacto valida paciente, familiar y parentesco, y la clave única `(IdPaciente, IdFamiliar)` impide duplicados. El DPI duplicado se rechaza excluyendo al paciente editado.
- **Borrado.** Un paciente con citas, hospitalizaciones, admisiones, contactos o telemetría no se elimina.

### C.3 Hospitalización (RF3)

- **Problema.** No había sección ni API.
- **Rutas.** `GET /api/hospitalizaciones`, `GET /api/camas/disponibles`, `POST /api/hospitalizaciones`, `POST /api/hospitalizaciones/<id>/finalizar`.
- **Solución.** El listado muestra ingreso, paciente, cama, sala, fechas y estado, y filtra por paciente y estado. El alta elige paciente y una cama sin hospitalización activa. La fecha de ingreso y el estado `Activa` salen de los `DEFAULT` de la tabla. La asignación bloquea la cama con `UPDLOCK, HOLDLOCK` y el índice único filtrado rechaza la segunda activa. El cierre graba `Finalizada` y `fecha_hora_salida_real = SYSDATETIME()`, y un segundo cierre responde 409. No se borró ninguna hospitalización real para fabricar camas libres.
- **Prueba de asignación exitosa.** Se insertó una cama con número `QAFIN-…`, se asignó, se rechazó la segunda y se finalizó. La limpieza posterior borró solo esas filas de prueba.

### C.4 Inventario (RF4)

- **Problema.** El movimiento se insertaba y la existencia no cambiaba. Una salida excesiva quedaba registrada.
- **Migración.** `Migracion_IdempotenciaMovimiento.sql` agrega `ClaveIdempotencia VARCHAR(64) NULL` y el índice filtrado `UX_MOVIMIENTO_Idempotencia`. Ya está aplicada. No modifica filas anteriores. La reversión es `DROP INDEX` y `DROP COLUMN`, documentada en el propio script.
- **Rutas.** `PUT /api/insumos/<id>` y `POST /api/movimientos`. `DELETE` de un movimiento responde 405. Un insumo con movimientos no se elimina.
- **Reglas, sin reinterpretar el historial.** Entrada y devolución suman. Salida resta y falla si la cantidad supera la existencia. Ajuste sustituye la existencia por la cantidad contada, porque `Cantidad` no tiene signo y el dato histórico describe un conteo físico. Los 17 movimientos ya guardados no se reaplican. La lectura del insumo usa `UPDLOCK, ROWLOCK`. Movimiento y existencia van en la misma transacción. La clave de idempotencia devuelve el movimiento ya creado y no vuelve a mover el stock.

### C.5 Sesión y mensajes

- La tarjeta de acceso ya no muestra usuario ni clave. El campo de usuario tampoco trae un valor escrito en el HTML.
- Un 401 de `/api/login` muestra «Usuario o clave incorrectos.» Los demás 401 informan que la sesión expiró.
- `traducir_error` convierte violaciones de unicidad, llaves foráneas, `CHECK` y los errores 51001 y 51002 a español. El texto del controlador queda solo en el registro del servidor.
- La cantidad cero dice que debe ser mayor que cero. La negativa dice que no puede ser negativa.

## D. Pruebas posteriores

Ejecutadas el 2 de noviembre de 2026 con `python -m pytest tests -q` dentro de `HospitalWeb`. Resultado guardado en `evidencias/pytest_resultado.txt`: **13 aprobadas, 0 fallidas, 1.80 s** en la corrida de cierre, y de nuevo **13 aprobadas en 2.26 s** al guardar el detalle. Las de integración usan SQL Server real. Las de `test_reglas.py` no abren conexión.

| Código | Requerimiento | Operación | Resultado esperado | Resultado obtenido | Estado | Evidencia |
|---|---|---|---|---|---|---|
| AUT-01 | Seguridad | Login incorrecto | Mensaje de credenciales, sin «expiró» | HTTP 401 y ese texto | APROBADA | `test_login_incorrecto_no_dice_sesion_expirada` |
| AUT-02 | Seguridad | API sin sesión | HTTP 401 en empleados y hospitalizaciones | HTTP 401 | APROBADA | `test_api_exige_sesion` |
| RF1-A | RF1 | Alta, edición, NSS duplicado, DELETE y baja | NSS único, fila inactiva, DELETE 405, sigue en el listado | Coincide; el mensaje no contiene «ODBC» | APROBADA | `test_rf1_alta_edicion_nss_duplicado_y_baja_logica` |
| RF1-B | RF1 | Cambiar el rol de un médico con citas | Rechazo del disparador 51002 | HTTP 409 y mensaje en español | APROBADA | `test_rf1_no_cambia_el_rol_de_un_medico_con_citas` |
| RF2-A | RF2 | Editar paciente, DPI duplicado, familiar o médico inexistente, admisión y contacto | Cambios persistidos; `FechaRegistro` igual; duplicado rechazado | Coincide en SQL Server | APROBADA | `test_rf2_edicion_dpi_admision_y_contacto` |
| RF3-A | RF3 | Cama real ocupada, cama de prueba, segunda asignación, cierre y segundo cierre | La cama real no recibe fila; la de prueba se ocupa, se rechaza la segunda, queda `Finalizada` con salida y vuelve a estar libre | Coincide | APROBADA | `test_rf3_cama_ocupada_asignacion_controlada_y_cierre` |
| RF3-B | RF3 | Dos asignaciones simultáneas a la misma cama de prueba | Una ok y una rechazada; una sola activa | `["ok", "rechazo"]` | APROBADA | `test_rf3_dos_asignaciones_simultaneas` |
| RF4-A | RF4 | Edición y movimientos | 10 + entrada 5 = 15; salida 2 = 13; devolución 1 = 14; ajuste 8 = 8; cero, negativa, salida 50 y entrada sobre el máximo rechazadas; la clave repetida no suma otra vez; proveedor 999999 rechazado; DELETE de movimiento 405 | Existencia final 9 tras la única entrada aceptada de 1 | APROBADA | `test_rf4_edicion_y_movimientos_actualizan_stock` |
| RF4-B | RF4 | Dos salidas simultáneas de 10 sobre existencia 10 | Una ok, una rechazo, existencia 0 | Coincide | APROBADA | `test_rf4_salidas_simultaneas_no_dejan_stock_negativo` |
| REG-01 | RF4 | Regla de stock | Entrada, salida, ajuste y devolución | Valores calculados correctos | APROBADA | `test_nuevo_stock_entrada_salida_ajuste_y_devolucion` |
| REG-02 | RF4 | Tope y salida excesiva | Excepciones | Se lanzan | APROBADA | `test_nuevo_stock_rechaza_salida_excesiva_y_maximo` |
| REG-03 | UX | Cantidad 0 y negativa | Mensajes distintos | «mayor que cero» y «no puede ser negativa» | APROBADA | `test_cantidad_cero_y_negativa_tienen_mensajes_distintos` |
| REG-04 | Seguridad | Traducción | El texto visible no incluye ODBC ni Microsoft | El NSS duplicado queda en español | APROBADA | `test_traduccion_no_expone_el_texto_del_controlador` |

Comprobaciones de interfaz, en el panel reiniciado con el código nuevo, en `http://127.0.0.1:5000`:

| Código | Operación | Resultado obtenido | Estado | Evidencia |
|---|---|---|---|---|
| UI-01 | Pantalla de acceso | El HTML no contiene la clave de demostración | APROBADA | `evidencias/ui-login.png` |
| UI-02 | Clave incorrecta | Aviso «Usuario o clave incorrectos.» y el formulario sigue visible | APROBADA | Ejecución en la página |
| UI-03 | Acceso válido | Entra al panel | APROBADA | Ejecución en la página |
| UI-04 | Hospitalización | 103 filas, 100 activas, selector «No hay camas disponibles», botón de ingreso deshabilitado | APROBADA | `evidencias/ui-hospitalizacion.png` |
| UI-05 | Empleado de prueba `QAFIN-UI01` | Alta, nombre cambiado a «Editado» en SQL, baja con `estado_activo` en falso y fila visible como Inactivo | APROBADA | `evidencias/ui-empleado-inactivo.png` y SELECT |

La fila `QAFIN-UI01` se eliminó al cerrar, porque era un registro de prueba y no tenía citas. No se usó el botón de la aplicación para ese borrado: la aplicación rechaza el `DELETE` de empleados. La limpieza fue el mismo procedimiento SQL del prefijo `QAFIN`.

## E. Comparación antes y después

| Concepto | Antes | Después |
|---|---|---|
| Pruebas de la auditoría inicial | 85 ejecutadas: 58 aprobadas, 4 fallidas, 3 parciales, 20 no implementadas | Esas 85 no se volvieron a ejecutar una por una. Siguen documentadas como línea base. |
| Suite nueva | No existía | 13 de 13 aprobadas contra el código y, en integración, contra SQL Server |
| RF1-13, borrado físico | Fallida | `DELETE` responde 405. La baja es lógica. |
| RF4-18, salida de 50 con existencia 10 | Fallida: se guardaba y el stock no se movía | Rechazada y la existencia no cambia |
| SEG-05, clave en la tarjeta | Fallida | La tarjeta ya no la muestra |
| UX-01, sesión expirada | Fallida en la interfaz | El login muestra credenciales incorrectas |
| RF4-10 y RF4-11 | Parciales: el movimiento no movía el stock | Entrada, salida, devolución y ajuste actualizan la existencia |
| UX-04, NSS duplicado | Parcial: rechazo con texto ODBC | Rechazo con mensaje en español |
| Edición y hospitalización | No implementadas | Implementadas y cubiertas por la suite y por UI-04 y UI-05 |

Siguen sin módulo propio, por decisión de alcance: mantenimiento de familiares, médicos externos, proveedores, turnos, especialidades y camas, y el alta de citas. La telemetría sigue siendo de consulta. Un movimiento ya guardado no se edita ni se borra; la corrección es otro movimiento. Esas cuatro ausencias ya estaban en la línea base como TEL-02, MOD-01 a MOD-05 y RF4-15. No se marcan como aprobadas.

## F. Validación de base de datos

Después de limpiar el prefijo `QAFIN`, `evidencias/conteos_sql.txt` registra:

```
conteos=(108, 18, 18, 17, 9, 17, 103, 100, 18)
hospitalizaciones_activas=100
restos_qafin=0 en Empleado, Paciente, Insumo, Cama y motivo de hospitalización
indices=UX_Hospitalizacion_Cama_Activa, UX_MOVIMIENTO_Idempotencia
clave_idempotencia_len=64
```

El orden de `conteos` es Paciente, Empleado, Insumo, ADMISION, contactos, movimientos, Hospitalizacion, Cama y Cita. Coincide con la línea base. Las 100 camas reales siguen ocupadas. No se eliminaron ni se recrearon tablas. Las llaves y los `CHECK` existentes siguen siendo las que rechazan DPI, NSS, stock negativo, stock sobre el máximo y una segunda hospitalización activa. Los `DEFAULT` de ingreso y estado `Activa` se usaron al insertar sin enviar esas columnas.

## G. Seguridad

Las rutas de consulta y de modificación revisadas exigen sesión. El login distingue clave incorrecta de sesión expirada. Las consultas nuevas siguen parametrizadas. Las acciones de baja, egreso y guardado de formularios pasan por el cuadro de confirmación cuando corresponde a baja, egreso o borrado. El texto técnico de SQL Server no se devuelve al navegador. La clave del panel no está en HTML, JavaScript ni en esta documentación. El proceso todavía puede leerla de `HOSPITAL_ADMIN_PASS`; hay que definir esa variable antes de exponer el panel fuera del equipo de desarrollo. No se imprimen credenciales de SQL Server porque la conexión usa autenticación de Windows.

## H. Conclusión

RF1, RF2, RF3 y RF4 quedaron implementados sobre el código existente y comprobados: la suite aplicable terminó con 13 aprobadas y 0 fallidas, y las cinco comprobaciones de interfaz de la sección D también se ejecutaron. Los conteos reales volvieron a la línea base.

No se declara el 100 % de las 85 pruebas originales, porque esa matriz no se repitió completa. Tampoco se declara cubierto el mantenimiento de catálogos, el alta de citas, la captura de telemetría ni la edición de un movimiento histórico: siguen fuera del panel a propósito.

## I. Anexos

- `evidencias/pytest_resultado.txt`
- `evidencias/conteos_sql.txt`
- `evidencias/ui-login.png`
- `evidencias/ui-hospitalizacion.png`
- `evidencias/ui-empleado-baja.png`
- `evidencias/ui-empleado-inactivo.png`
- `Migracion_IdempotenciaMovimiento.sql`
- `Informe_Pruebas_CRUD_HospitalW2.md` (línea base, sin reescribir sus resultados)
- `Informe_Tecnico_HospitalW2.md`
- `Matriz_Cumplimiento_RF_HospitalW2.md`
- Instrucciones de ejecución: `HospitalWeb/README.md`

Archivos de aplicación modificados: `HospitalWeb/app.py`, `HospitalWeb/static/app.js`, `HospitalWeb/templates/index.html`, `HospitalWeb/requirements.txt`, `HospitalWeb/README.md`, `.gitignore`. Archivos nuevos de prueba: `HospitalWeb/tests/`. No se hizo push a GitHub.
