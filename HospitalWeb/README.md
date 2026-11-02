# Hospital W 2.0 — Panel de administración

Aplicación web para operar la base `HospitalW2` en SQL Server Express. El administrador consulta, registra y modifica pacientes, personal, inventario y hospitalizaciones. La telemetría se consulta y no se captura desde este panel.

## Requisitos

- Windows con SQL Server Express (instancia `.\SQLEXPRESS`) y la base `HospitalW2` ya creada.
- Python 3.
- ODBC Driver 18 for SQL Server.
- Autenticación de Windows hacia SQL Server. No hace falta usuario ni clave del motor.

## Cómo ejecutar

Desde la carpeta `HospitalWeb`:

```powershell
python -m pip install -r requirements.txt
python app.py
```

También se puede usar `iniciar.bat`. El panel queda en <http://127.0.0.1:5000>.

El usuario y la clave del panel se leen de `HOSPITAL_ADMIN_USER` y `HOSPITAL_ADMIN_PASS`. Defínalas en el entorno antes de iniciar el proceso. No se imprimen en esta guía ni en la pantalla de acceso.

## Módulos

| Módulo | Operaciones |
|---|---|
| Pacientes | Alta, consulta, edición. El borrado físico solo procede si el paciente no tiene admisiones, contactos, citas, hospitalizaciones ni telemetría. |
| Admisiones | Alta, consulta, edición de paciente y médico. La fecha de registro original se conserva. |
| Contactos de emergencia | Alta, consulta y edición. No se permite repetir el mismo familiar para el mismo paciente. |
| Hospitalización | Consulta, filtro por paciente y estado, ingreso en cama libre y egreso. El egreso deja el estado `Finalizada` y libera la cama. |
| Empleados | Alta, consulta, edición y baja lógica. El `DELETE` responde 405. El historial de citas se conserva. |
| Insumos | Alta, consulta y edición. No se elimina un insumo que ya tiene movimientos. |
| Movimientos | Alta que actualiza `stock_existencia` en la misma transacción. El historial no se edita ni se borra. |
| Telemetría | Solo consulta. |

Reglas de inventario: entrada y devolución suman, salida resta y no puede superar la existencia, y el ajuste sustituye la existencia por la cantidad contada. Una clave de idempotencia opcional evita aplicar dos veces el mismo envío.

## Migración

`Migracion_IdempotenciaMovimiento.sql`, en la raíz del repositorio, agrega `MOVIMIENTO_INVENTARIO.ClaveIdempotencia` y el índice filtrado `UX_MOVIMIENTO_Idempotencia`. Es aditiva: no borra filas. La reversión está comentada al inicio del script. En esta instalación ya fue aplicada.

## Pruebas

Desde `HospitalWeb`:

```powershell
python -m pytest tests -q
```

Las pruebas de integración usan el prefijo `QAFIN`, limpian solo esas filas y comprueban que los conteos de las tablas reales vuelven al valor inicial. No eliminan hospitalizaciones ni camas preexistentes.

## Configuración

| Variable | Uso |
|---|---|
| `HOSPITAL_SERVER` | Instancia. Si no se define, `.\SQLEXPRESS`. |
| `HOSPITAL_DB` | Base. Si no se define, `HospitalW2`. |
| `HOSPITAL_DRIVER` | Controlador ODBC. Si no se define, Driver 18. |
| `HOSPITAL_TRUSTED` | `yes` usa autenticación de Windows. |
| `HOSPITAL_ADMIN_USER` | Usuario del panel. |
| `HOSPITAL_ADMIN_PASS` | Clave del panel. |

## Estructura

```
HospitalWeb/
  app.py
  templates/index.html
  static/app.js
  static/app.css
  tests/
  requirements.txt
  iniciar.bat
```
