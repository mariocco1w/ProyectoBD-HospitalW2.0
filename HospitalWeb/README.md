# Hospital W 2.0 - Panel de Administracion (pagina de pruebas)

Aplicacion web de pruebas para que un **administrador** pueda **ingresar** y
**eliminar** datos de la base `HospitalW2` (SQL Server Express):

- **Pacientes**
- **Empleados**
- **Insumos**

## Requisitos

- Windows con SQL Server Express (instancia `.\SQLEXPRESS`) y la base `HospitalW2`.
- Python 3 (ya instalado).
- ODBC Driver 17 o 18 for SQL Server (ya instalado).

## Como ejecutar

Doble clic en **`iniciar.bat`**, o desde una terminal:

```powershell
cd "C:\Users\Mario Monroy\Documents\SQL Server Management Studio 22\HospitalWeb"
python -m pip install -r requirements.txt
python app.py
```

Luego abre <http://127.0.0.1:5000>

## Acceso

- Usuario: **admin**
- Clave: **admin123**

(puedes cambiarlos con las variables de entorno `HOSPITAL_ADMIN_USER` y
`HOSPITAL_ADMIN_PASS` antes de iniciar).

## Que hace

| Modulo | Ingresar | Eliminar |
|--------|----------|----------|
| Pacientes | DPI, nombre, apellido, fecha de nacimiento, genero, direccion, telefono, familiar responsable, medico externo, adulto mayor | Elimina el paciente y, en cascada, sus citas y hospitalizaciones |
| Empleados | NSS, nombre, apellido, rol, turno, especialidad (opcional), activo | Elimina el empleado y, en cascada, sus citas y asignaciones a salas |
| Insumos | Codigo, nombre, tipo, stock existencia/maximo, costo, proveedor | Elimina el insumo |

Las operaciones usan consultas **parametrizadas** (sin concatenar SQL) y las
eliminaciones se ejecutan dentro de una **transaccion**.

## Configuracion (opcional)

Variables de entorno soportadas por `app.py`:

| Variable | Valor por defecto |
|----------|-------------------|
| `HOSPITAL_SERVER` | `.\SQLEXPRESS` |
| `HOSPITAL_DB` | `HospitalW2` |
| `HOSPITAL_DRIVER` | `ODBC Driver 18 for SQL Server` |
| `HOSPITAL_TRUSTED` | `yes` (autenticacion de Windows) |
| `HOSPITAL_ADMIN_USER` | `admin` |
| `HOSPITAL_ADMIN_PASS` | `admin123` |

La conexion usa **autenticacion de Windows** (`Trusted_Connection=yes`), por lo
que no hay que escribir usuario/clave de SQL Server.

## Estructura

```
HospitalWeb/
  app.py                -> backend Flask + API (pyodbc)
  templates/index.html  -> interfaz del administrador (HTML/CSS/JS)
  requirements.txt
  iniciar.bat
  README.md
```
