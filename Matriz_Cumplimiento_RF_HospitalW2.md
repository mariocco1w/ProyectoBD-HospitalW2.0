# Matriz de cumplimiento — Hospital W 2.0

Fecha de verificación: 2 de noviembre de 2026. La evidencia de cada fila está en `Informe_Auditoria_Final_HospitalW2.md` y en `evidencias/`.

| Requerimiento | Qué pide la guía | Estado | Cómo se comprobó |
|---|---|---|---|
| RF1 Alta | Registrar personal | Cumplido | Pytest `test_rf1_alta_edicion_nss_duplicado_y_baja_logica` y alta de `QAFIN-UI01` en la interfaz |
| RF1 Consulta | Consultar personal, incluido el inactivo | Cumplido | El mismo pytest: el NSS inactivo sigue en `GET /api/empleados` y no está en `empleados_activos` |
| RF1 Edición | Modificar campos admitidos, NSS único y llaves válidas | Cumplido | PUT en pytest y cambio de nombre a «Editado» confirmado con SELECT |
| RF1 Baja lógica | Desactivar sin `DELETE`, conservar historia, operación repetible | Cumplido | `DELETE` responde 405. Dos POST de baja dejan `estado_activo` en falso. El médico con citas no cambia de rol (51002, HTTP 409) |
| RF2 Pacientes | Alta, consulta y edición demográfica, dirección, teléfono, familiar y médico. DPI único | Cumplido | `test_rf2_edicion_dpi_admision_y_contacto`. Familiar o médico inexistente rechazados |
| RF2 Admisiones | Consultar historial y editar sin cambiar `FechaRegistro` | Cumplido | El mismo pytest compara la fecha antes y después |
| RF2 Contactos | Alta, consulta y edición sin duplicar paciente y familiar | Cumplido | El mismo pytest |
| RF3 Consulta | Listado con ingreso, paciente, cama, sala, fechas y estado, y filtros | Cumplido | API en pytest y pantalla: 103 filas, filtro de estado disponible |
| RF3 Ingreso | Solo cama libre, fecha automática, estado `Activa` | Cumplido | Cama real ocupada rechazada sin dejar fila. Cama `QAFIN` asignada y luego eliminada en la limpieza |
| RF3 Concurrencia | Una sola asignación gana | Cumplido | `test_rf3_dos_asignaciones_simultaneas`: un ok y un rechazo. El índice `UX_Hospitalizacion_Cama_Activa` sigue presente |
| RF3 Egreso | Salida real, estado `Finalizada`, cama libre, sin segundo cierre, historial intacto | Cumplido | `test_rf3_cama_ocupada_asignacion_controlada_y_cierre` |
| RF3 Sin camas reales | No borrar ocupación real; el alta se rechaza si no hay cama | Cumplido | La interfaz muestra cero camas libres y deshabilita el ingreso. Siguen 100 activas |
| RF4 Insumos | Alta, consulta y edición, código único, proveedor, costo y tope | Cumplido | `test_rf4_edicion_y_movimientos_actualizan_stock` |
| RF4 Movimientos | Entrada, salida, devolución y ajuste actualizan existencia en una transacción | Cumplido | Existencias 15, 13, 14 y 8 leídas en SQL dentro del mismo pytest |
| RF4 Rechazos | Cero, negativa, salida mayor al stock, sobre el máximo, proveedor inexistente | Cumplido | El mismo pytest. La existencia no cambia cuando el movimiento se rechaza |
| RF4 Concurrencia e idempotencia | Dos salidas no consumen dos veces; un reintento no se aplica dos veces | Cumplido | `test_rf4_salidas_simultaneas_no_dejan_stock_negativo` y la clave `clave-qafin-1` |
| Seguridad de sesión y mensajes | Sin clave en pantalla, 401 distinguido, errores SQL en español | Cumplido | AUT-01, AUT-02, REG-04 y capturas UI-01 y UI-02 |

Fuera de esta matriz, y sin marcarlos como cumplidos: pantallas de mantenimiento para familiares, médicos, proveedores, turnos, especialidades y camas; alta de citas; captura de telemetría; edición o borrado de un movimiento ya registrado.
