# Informe de pruebas CRUD — Hospital W 2.0

> Línea base del 2 de noviembre de 2026, anterior a las correcciones. Este documento no se reescribe: conserva los 85 resultados originales. El estado posterior está en `Informe_Auditoria_Final_HospitalW2.md`.

**Fecha de ejecución:** 2 de noviembre de 2026  
**Alcance:** auditoría funcional de la interfaz y contraste con SQL Server.  
**Restricción cumplida:** no se modificó la lógica de negocio, el esquema ni los datos preexistentes. Los registros de prueba se crearon con el prefijo `QA-AUD-20261102` y fueron eliminados. La prueba de cama ocupada se hizo dentro de una transacción revertida.

## Resumen general

| Resultado | Cantidad |
|---|---:|
| Pruebas ejecutadas | 85 |
| Aprobadas | 58 |
| Fallidas | 4 |
| Parciales | 3 |
| No implementadas | 20 |

La aplicación cubre alta, consulta y borrado físico de pacientes, empleados, insumos, admisiones, contactos de emergencia y movimientos de inventario. No permite modificar registros ya guardados. La hospitalización y la asignación de camas no existen en la interfaz. La baja de personal es un `DELETE` físico, no una baja lógica. Los movimientos de inventario se guardan y no actualizan la existencia.

---

## 1. Descripción de la aplicación evaluada

Hospital W 2.0 expone un panel web de administración para operar la base hospitalaria. El operador inicia sesión, consulta un tablero con indicadores y gráficas, y usa formularios de alta junto con tablas de consulta. Cada fila abre una ficha y, en los módulos editables, ofrece eliminar el registro.

El panel está pensado como página de pruebas del proyecto académico. Cubre pacientes, personal, inventario, admisiones, contactos y telemetría de solo lectura. No cubre el ciclo de hospitalización.

## 2. Arquitectura y tecnologías identificadas

| Capa | Tecnología |
|---|---|
| Lenguaje | Python 3 |
| Servidor | Flask, sesión por cookie |
| Acceso a datos | pyodbc, consultas parametrizadas |
| Interfaz | HTML, CSS y JavaScript sin framework |
| Base de datos | Microsoft SQL Server Express |
| Controlador | ODBC Driver 18 for SQL Server |

La arquitectura es un monolito: `HospitalWeb/app.py` entrega la página y una API JSON. El navegador llama esa API desde `HospitalWeb/static/app.js`. No hay capa separada de aplicación móvil ni de procedimientos almacenados para el CRUD del panel.

**Inicio de la interfaz**

1. Entrar a la carpeta `HospitalWeb`.
2. Ejecutar `iniciar.bat` o `python app.py`.
3. Abrir `http://127.0.0.1:5000`.
4. Iniciar sesión con el usuario administrador local.

Durante la auditoría el proceso quedó escuchando en `127.0.0.1:5000`. El registro del servidor no mostró respuestas HTTP 500.

**Pruebas automatizadas**

El repositorio no contiene pruebas unitarias, de integración ni de interfaz. No hay archivos de pytest, unittest ni una carpeta de tests. La verificación de esta auditoría se hizo contra el panel en ejecución y contra SQL Server.

## 3. Base de datos utilizada

| Dato | Valor observado |
|---|---|
| Motor | SQL Server Express, instancia local |
| Base | `HospitalW2` |
| Autenticación | Windows (`Trusted_Connection`) |
| Esquema principal | `dbo` |

No se transcribe la cadena de conexión ni credenciales. La conexión del panel no usa usuario ni clave de SQL Server.

Conteos generales, iguales antes y después de la auditoría:

| Tabla | Filas |
|---|---:|
| Paciente | 108 |
| Empleado | 18 |
| Insumo | 18 |
| ADMISION | 17 |
| ASIGNACION_CONTACTO_EMERGENCIA | 9 |
| MOVIMIENTO_INVENTARIO | 17 |
| Hospitalizacion | 103 |
| Hospitalizacion con estado Activa | 100 |
| Cama | 100 |
| Cita | 18 |

Las 100 camas tienen una hospitalización activa. No queda cama libre para un ingreso nuevo sin cerrar antes una hospitalización existente.

Disparadores de usuario presentes: `TR_Cita_SoloMedicos` y `TR_Empleado_ConCitas_Medico`. No hay un disparador que actualice `Insumo.stock_existencia` al registrar un movimiento.

## 4. Módulos funcionales encontrados

La navegación real contiene: Tablero, Pacientes, Admisiones, Contactos, Telemetría, Empleados, Insumos y Movimientos. No hay pantallas de hospitalización, camas, citas, salas, familiares, médicos externos ni proveedores.

| Módulo de la interfaz | Operaciones reales | Tablas |
|---|---|---|
| Tablero | Consulta agregada | Paciente, Empleado, Insumo, Cita, Hospitalizacion, ADMISION, contactos, movimientos, telemetría |
| Pacientes | Alta, consulta, borrado físico | `Paciente`; lee `FamiliarResponsable` y `MedicoExterno` |
| Admisiones | Alta, consulta, borrado físico | `ADMISION`, `Paciente`, `MedicoExterno` |
| Contactos de emergencia | Alta, consulta, borrado físico | `ASIGNACION_CONTACTO_EMERGENCIA`, `Paciente`, `FamiliarResponsable`, `PARENTESCO` |
| Empleados | Alta, consulta, borrado físico | `Empleado`, `Turno`, `Especialidad` |
| Insumos | Alta, consulta, borrado físico | `Insumo`, `Proveedor` |
| Movimientos | Alta, consulta, borrado físico | `MOVIMIENTO_INVENTARIO`, `Insumo`, `TIPO_MOVIMIENTO` |
| Telemetría | Solo consulta | `REGISTRO_TELEMETRIA`, `RESULTADO_PROCESAMIENTO_TELEMETRIA`, `RESUMEN_RIESGO_PACIENTE` |

Catálogos usados solo como listas desplegables, sin mantenimiento en la interfaz: turnos (3), especialidades (5), familiares (5), médicos externos (3), proveedores (4), parentescos (10) y tipos de movimiento (Entrada, Salida, Ajuste, Devolucion).

Tablas del modelo que la interfaz no opera: `Hospitalizacion`, `Cama`, `Sala`, `Cita`, `AsignacionPersonalSala`, `FamiliarResponsable`, `MedicoExterno`, `Proveedor`, `Turno`, `Especialidad`, `DIRECCION`, `TELEFONO`, `PUESTO`, `CENTRO_MEDICO` y `TIPO_SALA`.

Ningún módulo ofrece editar un registro guardado. La API no define métodos PUT ni PATCH.

## 5. Matriz de pruebas CRUD

Leyenda de estado: **APROBADA**, **FALLIDA**, **PARCIAL**, **NO IMPLEMENTADA**.  
Una prueba solo figura como aprobada si se ejecutó y el resultado coincidió con lo esperado, incluido el contraste con SQL Server cuando había persistencia.

| Código | RF | Módulo | Operación | Datos de prueba | Resultado esperado | Resultado obtenido | Estado | Evidencia | Observaciones |
|---|---|---|---|---|---|---|---|---|---|
| SEG-01 | Transversal | Autenticación | Consulta sin sesión | GET de empleados sin cookie | Rechazo sin datos | HTTP 401 | APROBADA | API | |
| SEG-02 | Transversal | Autenticación | Login negativo | Usuario inexistente | Rechazo | HTTP 401, credenciales incorrectas | APROBADA | POST /api/login | La interfaz muestra otro texto. Ver UX-01. |
| SEG-03 | Transversal | Autenticación | Login positivo | Usuario administrador local | Sesión iniciada | HTTP 200 y panel visible | APROBADA | API e interfaz | No se documenta la clave. |
| SEG-04 | Transversal | Limpieza | Reversión | Prefijo QA-AUD-20261102 | Conteos iguales al inicio | Conteos idénticos y cero filas QA | APROBADA | SELECT de control | |
| SEG-05 | Transversal | Autenticación | Exposición en pantalla | Pantalla de acceso | La clave no debería verse en la tarjeta | La tarjeta muestra usuario y clave de demostración en texto visible | FALLIDA | Pantalla de login | Hallazgo de exposición. El valor no se copia en este informe. |
| CAT-01 | Transversal | Catálogos | Read | Listas foráneas | Catálogos cargados | HTTP 200: 3 turnos, 5 especialidades, 5 familiares, 3 médicos, 4 proveedores, 10 parentescos | APROBADA | GET /api/catalogos | |
| RF1-01 | RF1 | Empleados | Create | NSS QA-AUD-20261102-E01, rol Médico, turno y especialidad existentes | Fila con turno y especialidad | HTTP 200 y fila encontrada en `Empleado` | APROBADA | API y SELECT | Registro de prueba, luego eliminado. |
| RF1-02 | RF1 | Empleados | Read | El mismo NSS | La lista coincide con SQL | Nombre, NSS, turno y especialidad coinciden | APROBADA | GET /api/empleados | |
| RF1-03 | RF1 | Empleados | Read existente | Un empleado ya almacenado, solo por id | Interfaz igual a SQL | NSS, nombre y rol coinciden | APROBADA | API y SELECT | No se transcriben datos personales. |
| RF1-04 | RF1 | Empleados | NSS duplicado | Segundo alta del mismo NSS | Rechazo y una sola fila | HTTP 409 por `UQ_Empleado_NSS`; 1 fila | APROBADA | API y SQL | El mensaje llega en inglés técnico. |
| RF1-05 | RF1 | Empleados | Obligatorios | Nombre vacío | Rechazo | HTTP 400, nada insertado | APROBADA | API | |
| RF1-06 | RF1 | Empleados | Rol inválido | Rol Director | Rechazo | HTTP 400, nada insertado | APROBADA | API | |
| RF1-07 | RF1 | Empleados | Turno inexistente | id de turno 999999 | Rechazo por llave foránea | HTTP 409, nada insertado | APROBADA | FK_Empleado_Turno | |
| RF1-08 | RF1 | Empleados | Especialidad inexistente | id 999999 | Rechazo por llave foránea | HTTP 409, nada insertado | APROBADA | FK_Empleado_Especialidad | |
| RF1-09 | RF1 | Empleados | Sin especialidad | NSS QA-AUD-20261102-E02 | Alta con especialidad nula | HTTP 200 y `id_especialidad` NULL | APROBADA | SQL | La especialidad es opcional. |
| RF1-10 | RF1 | Empleados | Alta inactiva | NSS QA-AUD-20261102-E03, casilla Activo desmarcada | `estado_activo = 0` | HTTP 200 y bit en 0 | APROBADA | SQL | Solo ocurre en el alta. No es baja de un empleado ya guardado. |
| RF1-11 | RF1 | Empleados | Update | PUT del empleado de prueba | El cambio persiste | HTTP 405; el nombre no cambió | NO IMPLEMENTADA | API y SQL | No hay botón Editar. |
| RF1-12 | RF1 | Empleados | Baja lógica | Intento de desactivar un empleado existente | El registro permanece con estado inactivo | No existe la operación. POST de baja respondió HTTP 404. El estado siguió activo | NO IMPLEMENTADA | API y SQL | |
| RF1-13 | RF1 | Empleados | Delete | Empleado de prueba sin citas ni asignaciones | Baja lógica: la fila permanece inactiva | HTTP 200 y la fila desapareció. El detalle indicó borrado de 0 citas y 0 asignaciones | FALLIDA | DELETE y SELECT | El botón funciona, pero borra físicamente. No cumple la baja lógica de RF1. |
| RF1-14 | RF1 | Empleados | Delete inexistente | id 99999999 | HTTP 404 | HTTP 404, sin otras filas afectadas | APROBADA | API | |
| RF2-01 | RF2 | Pacientes | Create | DPI QA-AUD-20261102-P01, nacimiento 1990-05-15, dirección, teléfono, familiar y médico existentes | Fila idéntica en SQL | HTTP 200; demográficos y ambas llaves coinciden | APROBADA | API y `Paciente` | |
| RF2-02 | RF2 | Pacientes | Read | El mismo DPI | La lista muestra demográficos, familiar y médico | Coinciden DPI, dirección, teléfono, familiar y médico | APROBADA | GET /api/pacientes | |
| RF2-03 | RF2 | Pacientes | Read existente | Un paciente ya almacenado | Interfaz igual a SQL | DPI, nombre y género coinciden | APROBADA | API y SQL | Sin transcribir datos reales. |
| RF2-04 | RF2 | Pacientes | DPI duplicado | Segundo alta del mismo DPI | Rechazo | HTTP 409 por `UQ_Paciente_DPI`; 1 fila | APROBADA | SQL | |
| RF2-05 | RF2 | Pacientes | Obligatorios | Dirección vacía | Rechazo | HTTP 400, nada insertado | APROBADA | API | |
| RF2-06 | RF2 | Pacientes | Familiar inexistente | id 999999 | Rechazo por llave foránea | HTTP 409, nada insertado | APROBADA | FK_Paciente_Familiar | |
| RF2-07 | RF2 | Pacientes | Médico inexistente | id 999999 | Rechazo por llave foránea | HTTP 409, nada insertado | APROBADA | FK_Paciente_MedicoExterno | |
| RF2-08 | RF2 | Pacientes | Género inválido | Género X | Rechazo | HTTP 400, nada insertado | APROBADA | API | |
| RF2-09 | RF2 | Pacientes | Adulto mayor | DPI QA-AUD-20261102-P06 y casilla marcada | Bit en 1 | HTTP 200 y bit en 1 | APROBADA | SQL | La marca es manual. No se calcula con la fecha de nacimiento. |
| RF2-10 | RF2 | Pacientes | Update | PUT del teléfono de prueba | El teléfono cambia | HTTP 405; el teléfono siguió igual | NO IMPLEMENTADA | API y SQL | |
| RF2-11 | RF2 | Admisiones | Create | Paciente de prueba, médico existente, 2026-11-02 09:30:00 | Fecha exacta guardada | HTTP 200 y esa fecha en `ADMISION` | APROBADA | API y SQL | |
| RF2-12 | RF2 | Admisiones | Create sin médico ni fecha | Paciente de prueba | Médico nulo y fecha del momento | HTTP 200, médico NULL y fecha a menos de dos minutos | APROBADA | SQL | La hora la pone la aplicación, porque siempre envía la fecha. |
| RF2-13 | RF2 | Admisiones | Paciente inexistente | id 99999999 | Rechazo | HTTP 409 y cero filas | APROBADA | FK de ADMISION | |
| RF2-14 | RF2 | Admisiones | Read | Admisión de prueba | Visible con paciente y médico | Apareció en la consulta | APROBADA | GET /api/admisiones | |
| RF2-15 | RF2 | Admisiones | Update | PUT de la admisión de prueba | Cambio persistido | HTTP 405 | NO IMPLEMENTADA | Rutas de app.py | |
| RF2-16 | RF2 | Contactos | Create | Paciente, familiar y parentesco existentes | Asignación guardada | HTTP 200 y fila en la tabla de asignación | APROBADA | API y SQL | |
| RF2-17 | RF2 | Contactos | Duplicado | La misma pareja paciente-familiar | Rechazo | HTTP 409 por `UQ_ASIGNACION_CONTACTO`; 1 fila | APROBADA | SQL | |
| RF2-18 | RF2 | Contactos | Familiar inexistente | id 999999 | Rechazo | HTTP 409 | APROBADA | FK hacia FamiliarResponsable | |
| RF2-19 | RF2 | Contactos | Read | Contacto de prueba | Visible con parentesco | Apareció en la lista | APROBADA | GET /api/contactos | |
| RF2-20 | RF2 | Contactos | Update | PUT del contacto de prueba | Cambio persistido | HTTP 405 | NO IMPLEMENTADA | Rutas de app.py | |
| RF2-21 | RF2 | Contactos | Delete | Contacto de prueba | Solo esa fila desaparece | HTTP 200 y la fila ya no existe | APROBADA | API y SQL | |
| RF2-22 | RF2 | Admisiones | Delete | Admisiones del paciente de prueba | Esas admisiones se van y el paciente sigue | Cero admisiones restantes de ese paciente | APROBADA | API y SQL | Borrado físico. |
| RF2-23 | RF2 | Pacientes | Delete | Paciente de prueba ya sin dependencias | La fila desaparece | HTTP 200 y el DPI ya no existe | APROBADA | API y SQL | |
| RF2-24 | RF2 | Pacientes | Delete en cascada | Paciente de prueba con una admisión | La admisión se elimina junto con el paciente | El detalle reportó 1 admisión borrada. Paciente y admisión quedaron en cero | APROBADA | DELETE /api/pacientes y SQL | También está programado el borrado de citas, hospitalizaciones, contactos y telemetría. |
| RF3-01 | RF3 | Hospitalización | Create | Revisión de menú, formularios y API | Formulario de hospitalización | No hay módulo. GET /api/hospitalizaciones respondió 404 | NO IMPLEMENTADA | index.html, app.js, app.py | |
| RF3-02 | RF3 | Hospitalización | Read | La misma revisión | Consulta de hospitalizaciones | Solo el tablero muestra el agregado de 100 activas | NO IMPLEMENTADA | Tablero | No hay listado ni ficha. |
| RF3-03 | RF3 | Camas | Asignar cama | La misma revisión | Selector de cama | No hay control de camas | NO IMPLEMENTADA | Interfaz | |
| RF3-04 | RF3 | Camas | Cama ocupada | Intento desde la interfaz | La interfaz impide la segunda asignación | La interfaz no ofrece la operación | NO IMPLEMENTADA | Interfaz | La regla sí existe en la base. Ver INT-01. |
| RF3-05 | RF3 | Hospitalización | Fecha de ingreso | Alta desde la interfaz | Fecha y hora reales al ingresar | No hay alta en la interfaz | NO IMPLEMENTADA | Interfaz | El DEFAULT de la tabla sí funciona. Ver INT-01. |
| RF3-06 | RF3 | Hospitalización | Fecha de salida | Alta o cierre desde la interfaz | Se registra la salida | No hay control de salida | NO IMPLEMENTADA | Interfaz | |
| RF3-07 | RF3 | Hospitalización | Cambio de estado | Activa, Finalizada o Cancelada | El estado cambia desde la interfaz | No hay control de estado | NO IMPLEMENTADA | Interfaz | |
| INT-01 | Integridad | Hospitalización | Cama activa única | Cama temporal y dos pacientes, transacción revertida | La segunda alta activa falla y no queda nada grabado | La primera quedó Activa con fecha a 0,2 s. La segunda falló por `UX_Hospitalizacion_Cama_Activa`. Residuos: 0 | APROBADA | SQL con ROLLBACK | No pasa por la interfaz. No se ocupó una cama real. |
| RF4-01 | RF4 | Insumos | Create | Código QA-AUD-20261102-I01, existencia 10, máximo 100, costo 4.50, proveedor existente | Fila con costo, stock y proveedor | HTTP 200 y valores iguales en `Insumo` | APROBADA | API y SQL | |
| RF4-02 | RF4 | Insumos | Read | El mismo código | Existencia, costo y proveedor visibles | Coinciden con SQL | APROBADA | GET /api/insumos | |
| RF4-03 | RF4 | Insumos | Read existente | Un insumo ya almacenado | Existencia igual a SQL | Código y existencia coinciden | APROBADA | API y SQL | |
| RF4-04 | RF4 | Insumos | Código duplicado | Segundo alta del mismo código | Rechazo | HTTP 409 por `UQ_Insumo_Codigo`; 1 fila | APROBADA | SQL | |
| RF4-05 | RF4 | Insumos | Obligatorios | Nombre vacío | Rechazo | HTTP 400, nada insertado | APROBADA | API | |
| RF4-06 | RF4 | Insumos | Proveedor inexistente | id 999999 | Rechazo por llave foránea | HTTP 409, nada insertado | APROBADA | FK_Insumo_Proveedor | |
| RF4-07 | RF4 | Insumos | Costo negativo | Costo -3 | Rechazo | HTTP 400, nada insertado | APROBADA | API | |
| RF4-08 | RF4 | Insumos | Stock inválido | Existencia 50 y máximo 10 | Rechazo | HTTP 400, nada insertado | APROBADA | API | |
| RF4-09 | RF4 | Insumos | Update | PUT del costo | El costo cambia | HTTP 405; el costo siguió en 4.50 | NO IMPLEMENTADA | API y SQL | |
| RF4-10 | RF4 | Movimientos | Entrada | Entrada de 5 sobre existencia 10 | El movimiento se guarda y la existencia sube | HTTP 200 y movimiento guardado. Existencia 10.00 → 10.00 | PARCIAL | `MOVIMIENTO_INVENTARIO` e `Insumo` | No hay disparador de stock. |
| RF4-11 | RF4 | Movimientos | Salida | Salida de 2 | La existencia baja | HTTP 200. La existencia siguió en 10.00 | PARCIAL | SQL | |
| RF4-12 | RF4 | Movimientos | Cantidad cero | Cantidad 0 | Rechazo | HTTP 400 y nada guardado | APROBADA | API | El texto dice que la cantidad no puede ser negativa, aunque el valor era cero. |
| RF4-13 | RF4 | Movimientos | Insumo inexistente | id 999999 | Rechazo por llave foránea | HTTP 409 | APROBADA | FK del movimiento | |
| RF4-14 | RF4 | Movimientos | Read | Entrada de prueba | Visible con tipo, cantidad y costo | Apareció con cantidad 5 | APROBADA | GET /api/movimientos | |
| RF4-15 | RF4 | Movimientos | Update | PUT del movimiento de prueba | Cambio persistido | HTTP 405 | NO IMPLEMENTADA | Rutas de app.py | |
| RF4-16 | RF4 | Movimientos | Delete | Movimiento de prueba | Solo ese movimiento desaparece | HTTP 200 y la fila ya no existe | APROBADA | API y SQL | |
| RF4-17 | RF4 | Insumos | Delete | Insumo de prueba | La fila desaparece | HTTP 200 y el código ya no existe | APROBADA | API y SQL | El borrado también elimina movimientos asociados. |
| RF4-18 | RF4 | Movimientos | Salida mayor al stock | Salida de 50 con existencia 10 | Rechazo o existencia no negativa y actualizada | HTTP 200, 1 movimiento guardado y existencia sigue en 10.00 | FALLIDA | API y SQL | La salida excesiva queda registrada y el stock no se mueve. |
| TEL-01 | Transversal | Telemetría | Read | Listado clínico | Conteo igual a SQL | HTTP 200; 5 filas en API y 5 en SQL | APROBADA | GET /api/telemetria | |
| TEL-02 | Transversal | Telemetría | Create | POST al listado | No crea registros | HTTP 405 | NO IMPLEMENTADA | app.py | El diseño de esta pantalla es de solo lectura. |
| DASH-01 | Transversal | Tablero | Read | Indicadores | Conteos iguales a SQL | Pacientes 108, empleados 18, insumos 18 y 100 hospitalizaciones activas | APROBADA | API, interfaz y SQL | |
| MOD-01 | Transversal | Familiares | CRUD | GET /api/familiares | Mantenimiento del catálogo | HTTP 404. Solo hay lista desplegable | NO IMPLEMENTADA | Interfaz | Hay 5 familiares utilizables. |
| MOD-02 | Transversal | Médicos externos | CRUD | GET /api/medicos | Mantenimiento del catálogo | HTTP 404. Solo hay lista desplegable | NO IMPLEMENTADA | Interfaz | Hay 3 médicos utilizables. |
| MOD-03 | Transversal | Proveedores | CRUD | GET /api/proveedores | Mantenimiento del catálogo | HTTP 404. Solo hay lista desplegable | NO IMPLEMENTADA | Interfaz | Hay 4 proveedores utilizables. |
| MOD-04 | Transversal | Camas | CRUD | GET /api/camas | Mantenimiento y ocupación | HTTP 404 | NO IMPLEMENTADA | Interfaz | |
| MOD-05 | Transversal | Citas | CRUD | GET /api/citas | Mantenimiento de citas | HTTP 404 | NO IMPLEMENTADA | Interfaz | El tablero solo muestra el total: 18. |
| UX-01 | Transversal | Login | Mensaje de error | Clave incorrecta en el formulario | Mensaje de credenciales incorrectas | El aviso dice «La sesión expiró. Vuelva a iniciar sesión.» | FALLIDA | Interfaz | El API sí distingue la clave incorrecta. El JavaScript convierte todo HTTP 401 en sesión expirada. |
| UX-02 | Transversal | Empleados | Validación del formulario | Envío con campos vacíos | El navegador bloquea el envío | `checkValidity()` falso y cero POST | APROBADA | Formulario de empleados | Campos requeridos: NSS, nombre, apellido, rol y turno. |
| UX-03 | Transversal | Empleados | Create desde la interfaz | NSS QA-AUD-UI-E01, nombre Interfaz Auditoria | Mensaje de éxito y fila visible, coincidente con SQL | Aviso de registro correcto. La tabla y la ficha mostraron NSS, rol Médico, turno Matutino y estado Activo | APROBADA | Interfaz y bitácora HTTP 200 | |
| UX-04 | Transversal | Empleados | NSS duplicado en pantalla | Segundo alta del mismo NSS de interfaz | Rechazo comprensible | HTTP 409 y el aviso muestra el texto crudo del controlador ODBC, en inglés | PARCIAL | Interfaz | El rechazo es correcto. El mensaje no es comprensible para un usuario final. |
| UX-05 | Transversal | Empleados | Delete desde la interfaz | El empleado QA-AUD-UI-E01 | Confirmación y desaparición solo de esa fila | El diálogo advirtió borrado permanente. DELETE respondió HTTP 200. En SQL no quedó ningún NSS de prueba y el total volvió a 18 | APROBADA | Interfaz, bitácora y SQL | Confirma el borrado físico, no la baja lógica. |
| UX-06 | Transversal | Navegación | Read de módulos | Pacientes, admisiones, contactos, insumos, movimientos y telemetría | Tablas con datos reales | 108, 17, 9, 18, 17 y 5 filas, alineadas con SQL | APROBADA | Interfaz | No se transcriben nombres ni DPI reales. |
| UX-07 | Transversal | Estabilidad | Consola y bitácora | Recorrido completo | Sin cierre ni HTTP 500 | Cero errores de JavaScript capturados y cero HTTP 500 en la bitácora de Flask | APROBADA | Consola del navegador y terminal del servidor | |

## 6. Resultados por requerimiento

### RF1. Gestión de personal médico y administrativo

**Estado del requerimiento: parcial.**

La interfaz registra empleados, consulta los existentes y valida NSS único, turno existente, especialidad válida y campos obligatorios. Las pruebas positivas y negativas quedaron confirmadas en `dbo.Empleado`.

No se puede modificar un empleado guardado. No existe baja lógica: el único control posterior al alta es Eliminar, y ejecuta un `DELETE` que también borra citas y asignaciones a sala. La casilla Activo solo aplica al momento de crear el registro.

No se pueden dar de alta turnos ni especialidades desde el panel. Solo se asocian los que ya existen.

### RF2. Admisión y control de pacientes

**Estado del requerimiento: parcial.**

El alta de paciente guarda DPI, nombre, apellido, fecha de nacimiento, género, dirección, teléfono, familiar responsable y médico externo. La consulta muestra esos datos y coinciden con SQL Server. Un DPI duplicado, un familiar inexistente, un médico inexistente, un género inválido y una dirección vacía son rechazados. La marca de adulto mayor se almacena, aunque no se deduce de la edad.

También funcionan, como módulos aparte, la admisión y el contacto de emergencia: alta, consulta y borrado. La admisión puede omitir el médico y, si no se escribe fecha, guarda la hora del momento. El contacto rechaza una pareja paciente-familiar repetida.

No hay edición de pacientes, admisiones ni contactos. No se pueden registrar familiares ni médicos nuevos; si el catálogo no tuviera registros, el formulario de paciente no podría completarse. El borrado de un paciente es físico y arrastra admisiones, contactos, citas, hospitalizaciones y telemetría. Esa cascada se comprobó con una admisión de prueba.

### RF3. Hospitalización y asignación de camas

**Estado del requerimiento: no implementado en la interfaz.**

El menú no tiene hospitalización ni camas. No existe API para registrar un ingreso, elegir cama, impedir una cama ocupada, guardar la salida ni cambiar el estado. El tablero únicamente muestra que hay 100 hospitalizaciones activas.

En la base, la regla sí está instalada. Dentro de una transacción que se revirtió por completo:

- la primera hospitalización de prueba tomó el estado `Activa` y una fecha de ingreso real, por los valores DEFAULT;
- la segunda hospitalización activa sobre la misma cama fue rechazada por el índice único filtrado `UX_Hospitalizacion_Cama_Activa`;
- no quedó cama ni hospitalización de prueba.

Esa comprobación no sustituye al requerimiento de interfaz. Además, hoy las 100 camas reales ya tienen una hospitalización activa, así que un alta nueva no tendría cama libre aunque la pantalla existiera.

### RF4. Gestión de inventario

**Estado del requerimiento: parcial.**

El alta de insumo guarda código, nombre, tipo, existencia, máximo, costo unitario y proveedor obligatorio. La consulta muestra la existencia y coincide con SQL Server. Se rechazan código duplicado, proveedor inexistente, costo negativo, existencia mayor al máximo y nombre vacío.

La interfaz registra entradas, salidas, ajustes y devoluciones en `MOVIMIENTO_INVENTARIO`. Esos movimientos no modifican `stock_existencia`. Una salida de 50 unidades sobre un insumo con existencia 10 fue aceptada y el stock permaneció en 10.00. No hay disparador ni lógica de aplicación que recalcule la existencia ni que impida quedar en negativo.

No se puede modificar un insumo ni un movimiento. No se pueden registrar proveedores nuevos.

## 7. Pruebas de integridad de datos

| Regla | Dónde se comprobó | Resultado |
|---|---|---|
| `UQ_Empleado_NSS` | Alta duplicada | Rechazada, una sola fila |
| `FK_Empleado_Turno` y `FK_Empleado_Especialidad` | Ids inexistentes | Rechazadas |
| `CK_Empleado_Rol` y validación de la API | Rol Director | Rechazado antes de llegar a un rol fuera de la lista |
| `UQ_Paciente_DPI` | DPI duplicado | Rechazado |
| `FK_Paciente_Familiar` y `FK_Paciente_MedicoExterno` | Ids inexistentes | Rechazadas |
| Género permitido | Valor X | Rechazado por la API |
| `UQ_ASIGNACION_CONTACTO` | Misma pareja paciente-familiar | Rechazada |
| `UQ_Insumo_Codigo` | Código duplicado | Rechazado |
| `FK_Insumo_Proveedor` | Proveedor inexistente | Rechazado |
| `CK_Insumo_Stock` y `CK_Insumo_Costo` | Existencia sobre el máximo y costo negativo | Rechazados por la API, sin fila nueva |
| `CK_MOVIMIENTO_Cantidad` | Cantidad 0 | Rechazada por la API |
| FK del movimiento | Insumo inexistente | Rechazada |
| `UX_Hospitalizacion_Cama_Activa` | Segunda hospitalización activa, transacción revertida | Rechazada |
| DEFAULT de ingreso y estado | Primera hospitalización de esa transacción | `Activa` y fecha real |
| Consistencia interfaz / SQL | Empleado, paciente, insumo y tablero, de prueba y preexistentes | Coinciden en las consultas probadas |
| Manejo de errores SQL | Duplicados y llaves foráneas | La API responde 409 y no deja la fila. El texto mostrado es el error original del motor |

No se alteraron índices, restricciones ni relaciones. No se ejecutaron actualizaciones ni borrados masivos. Los borrados se limitaron a filas creadas en la auditoría.

## 8. Errores encontrados

Prioridad de mayor a menor impacto sobre la Fase I:

1. **RF3 ausente.** No se puede hospitalizar, asignar cama, registrar salida ni cambiar el estado desde la interfaz. Es el requerimiento que el panel no cubre.
2. **La baja de personal no es lógica.** Eliminar un empleado borra la fila y puede borrar citas y asignaciones. RF1 pide desactivarlo y conservarlo.
3. **El inventario no mueve existencias.** Entradas y salidas se archivan y `stock_existencia` no cambia. Una salida mayor que el stock se acepta.
4. **No hay modificación en ningún módulo operativo.** Paciente, empleado, insumo, admisión, contacto y movimiento solo se crean, consultan y borran.
5. **Los mensajes de integridad no son comprensibles.** El usuario ve el texto del controlador ODBC, en inglés, con el nombre de la restricción y códigos del driver. El rechazo en sí es correcto.
6. **El login fallido se presenta como sesión expirada.** Una clave incorrecta produce el aviso «La sesión expiró. Vuelva a iniciar sesión.», aunque el servidor respondió credenciales incorrectas.
7. **La pantalla de acceso muestra la clave de demostración** en texto visible dentro de la tarjeta de bienvenida.
8. **La cantidad cero se rechaza con un texto equivocado:** «La cantidad no puede ser negativo.»
9. **El borrado de un paciente es en cascada** sobre citas, hospitalizaciones, admisiones, contactos y telemetría. Funciona, y es un riesgo alto si se usa sobre un paciente real.

## 9. Funcionalidades parcialmente implementadas

- Personal: alta, consulta, NSS único, turno, especialidad y obligatorios. Falta editar y dar de baja sin borrar.
- Pacientes: alta, consulta, demográficos, familiar, médico y validaciones. Falta editar. El familiar y el médico solo se eligen entre los ya cargados.
- Admisiones y contactos: alta, consulta y borrado. Falta editar.
- Inventario: alta, consulta, costo, proveedor y validaciones. Los movimientos existen como historial y no como control de existencia.
- Tablero: los agregados de citas y hospitalizaciones coinciden con SQL, sin permitir operar esos procesos.
- Adulto mayor: se guarda la casilla y no se contrasta con la fecha de nacimiento.

## 10. Funcionalidades no implementadas

- Edición de empleados, pacientes, insumos, admisiones, contactos y movimientos.
- Baja lógica de empleados.
- Registrar, consultar, asignar y cerrar hospitalizaciones desde la interfaz.
- Disponibilidad de camas y bloqueo de cama ocupada desde la interfaz.
- Fecha de salida y cambio de estado de una hospitalización desde la interfaz.
- Mantenimiento de familiares, médicos externos, proveedores, turnos, especialidades, camas y citas.
- Alta o edición de telemetría. La consulta sí está implementada y es de solo lectura.

## 11. Evidencias disponibles

- Este informe, generado el 2 de noviembre de 2026.
- Panel en ejecución durante las pruebas: `http://127.0.0.1:5000`.
- Bitácora de Flask sin HTTP 500. Consta, entre otras respuestas, el alta de empleados 200, el NSS duplicado 409, el login incorrecto 401 y el `DELETE /api/empleados/50` con resultado 200.
- Contraste fila por fila en `HospitalW2` para altas, rechazos y borrados de prueba.
- Conteos anteriores y posteriores idénticos: 108 pacientes, 18 empleados, 18 insumos, 17 admisiones, 9 contactos, 17 movimientos, 103 hospitalizaciones, 100 camas y 18 citas.
- Cero filas residuales con prefijo `QA-AUD` y cero hospitalizaciones cuyo motivo perteneciera a la prueba.
- Recorrido de la interfaz: login, tablero, formulario vacío, alta visible, ficha de empleado, diálogo de eliminación y tablas de los seis módulos de consulta.
- La prueba de cama se revirtió con `ROLLBACK`. No se ocupó ninguna de las 100 camas reales.

No se adjuntan capturas con datos personales de pacientes reales ni con la clave visible del panel.

## 12. Conclusión

Hospital W 2.0 tiene un panel utilizable para alta, consulta y borrado físico de pacientes, personal e inventario, con validaciones de obligatorios, duplicados y llaves foráneas que sí se reflejan en SQL Server. Ese comportamiento alcanza una parte de RF1, RF2 y RF4.

La Fase I no puede darse por completa con la interfaz actual. Falta toda la operación de RF3. Falta la baja lógica de RF1 y la modificación en los cuatro requerimientos. El inventario registra movimientos sin actualizar existencias, así que la consulta de stock no representa las entradas y salidas capturadas en pantalla.

El diagnóstico queda limitado a la evidencia ejecutada. No se corrigió ningún defecto en esta etapa.
