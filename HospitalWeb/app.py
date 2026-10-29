"""
Hospital W 2.0 - Panel de Administracion
Backend Flask + pyodbc (SQL Server, autenticacion de Windows).

Permite al administrador LISTAR, INGRESAR y ELIMINAR datos de:
  - Pacientes
  - Empleados
  - Insumos
  - Admisiones           (ADMISION)
  - Contactos de emergencia (ASIGNACION_CONTACTO_EMERGENCIA)
  - Movimientos de inventario (MOVIMIENTO_INVENTARIO)
  - Telemetria           (REGISTRO_TELEMETRIA, solo lectura)

Ademas entrega los datos agregados del panel principal (graficas de pastel).

Ejecutar:  python app.py   y abrir http://127.0.0.1:5000
"""

import os
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal
from functools import wraps

import pyodbc
from flask import Flask, jsonify, render_template, request, session

# ---------------------------------------------------------------------------
# Configuracion (se puede cambiar con variables de entorno)
# ---------------------------------------------------------------------------
DB_DRIVER = os.environ.get("HOSPITAL_DRIVER", "ODBC Driver 18 for SQL Server")
DB_SERVER = os.environ.get("HOSPITAL_SERVER", r".\SQLEXPRESS")
DB_NAME = os.environ.get("HOSPITAL_DB", "HospitalW2")
DB_TRUSTED = os.environ.get("HOSPITAL_TRUSTED", "yes")  # autenticacion Windows

ADMIN_USER = os.environ.get("HOSPITAL_ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("HOSPITAL_ADMIN_PASS", "admin123")

CONN_STR = (
    f"DRIVER={{{DB_DRIVER}}};"
    f"SERVER={DB_SERVER};"
    f"DATABASE={DB_NAME};"
    f"Trusted_Connection={DB_TRUSTED};"
    "TrustServerCertificate=yes;"
)

app = Flask(__name__)
app.secret_key = os.environ.get("HOSPITAL_SECRET", "hospital-w2-panel-secret")


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
@contextmanager
def db():
    """Conexion con commit/rollback automatico y cierre garantizado."""
    conn = pyodbc.connect(CONN_STR, autocommit=False)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def to_jsonable(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def fetch(cursor, sql, params=()):
    cursor.execute(sql, params)
    cols = [c[0] for c in cursor.description]
    return [{c: to_jsonable(v) for c, v in zip(cols, row)} for row in cursor.fetchall()]


def serie(cursor, sql):
    """Ejecuta una consulta de 2 columnas (etiqueta, valor) para las graficas."""
    cursor.execute(sql)
    return [
        {"label": "(sin dato)" if r[0] in (None, "") else str(r[0]), "value": to_jsonable(r[1])}
        for r in cursor.fetchall()
    ]


def friendly_error(exc):
    if isinstance(exc, pyodbc.Error) and len(exc.args) > 1:
        return str(exc.args[1])
    return str(exc)


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not session.get("user"):
            return jsonify(error="Sesion no iniciada."), 401
        return view(*args, **kwargs)

    return wrapper


def error_response(exc):
    msg = friendly_error(exc)
    if isinstance(exc, pyodbc.IntegrityError):
        return jsonify(error="Restriccion de integridad: " + msg), 409
    return jsonify(error=msg), 400


def entero(valor, minimo=None):
    """Convierte a entero validando el minimo. Lanza ValueError si es invalido."""
    n = int(valor)
    if minimo is not None and n < minimo:
        raise ValueError(f"El valor debe ser mayor o igual a {minimo}.")
    return n


def decimal_positivo(valor, nombre, permitir_cero=True):
    try:
        n = Decimal(str(valor))
    except Exception:
        raise ValueError(f"{nombre} debe ser numerico.")
    if n < 0 or (not permitir_cero and n == 0):
        raise ValueError(f"{nombre} no puede ser negativo.")
    return n


# ---------------------------------------------------------------------------
# Autenticacion del administrador
# ---------------------------------------------------------------------------
@app.get("/")
def index():
    return render_template("index.html")


@app.post("/api/login")
def api_login():
    data = request.get_json(silent=True) or {}
    if data.get("usuario") == ADMIN_USER and data.get("clave") == ADMIN_PASS:
        session["user"] = ADMIN_USER
        return jsonify(user=ADMIN_USER)
    return jsonify(error="Usuario o clave incorrectos."), 401


@app.post("/api/logout")
def api_logout():
    session.clear()
    return jsonify(ok=True)


@app.get("/api/me")
def api_me():
    return jsonify(user=session.get("user"))


# ---------------------------------------------------------------------------
# Datos para los formularios (llaves foraneas y opciones validas)
# ---------------------------------------------------------------------------
@app.get("/api/catalogos")
@login_required
def api_catalogos():
    with db() as conn:
        cur = conn.cursor()
        data = {
            "turnos": fetch(cur, "SELECT id_turno, nombre_turno FROM dbo.Turno ORDER BY nombre_turno;"),
            "especialidades": fetch(
                cur,
                "SELECT id_especialidad, nombre_especialidad FROM dbo.Especialidad ORDER BY nombre_especialidad;",
            ),
            "familiares": fetch(
                cur,
                "SELECT id_familiar, nombre + ' ' + apellido AS nombre_completo, telefono, parentesco "
                "FROM dbo.FamiliarResponsable ORDER BY nombre, apellido;",
            ),
            "medicos": fetch(
                cur,
                "SELECT id_medico_externo, nombre + ' ' + apellido AS nombre_completo "
                "FROM dbo.MedicoExterno ORDER BY nombre, apellido;",
            ),
            "proveedores": fetch(
                cur,
                "SELECT id_proveedor, razon_social FROM dbo.Proveedor ORDER BY razon_social;",
            ),
            "parentescos": fetch(
                cur,
                "SELECT IdParentesco, NombreParentesco FROM dbo.PARENTESCO ORDER BY NombreParentesco;",
            ),
            "tipos_movimiento": fetch(
                cur,
                "SELECT IdTipoMovimiento, NombreTipoMovimiento FROM dbo.TIPO_MOVIMIENTO ORDER BY IdTipoMovimiento;",
            ),
            "insumos": fetch(
                cur,
                "SELECT id_insumo, codigo_insumo, nombre_insumo FROM dbo.Insumo ORDER BY nombre_insumo;",
            ),
            "pacientes_opciones": fetch(
                cur,
                "SELECT id_paciente, nombre + ' ' + apellido + ' (DPI ' + dpi + ')' AS nombre_completo "
                "FROM dbo.Paciente ORDER BY nombre, apellido;",
            ),
        }
    data["generos"] = ["Femenino", "Masculino", "Otro"]
    data["roles"] = ["Medico", "Enfermeria", "Administrativo", "Tecnico", "Otro"]
    return jsonify(data)


# ---------------------------------------------------------------------------
# DASHBOARD (datos agregados para las graficas)
# ---------------------------------------------------------------------------
@app.get("/api/dashboard")
@login_required
def api_dashboard():
    with db() as conn:
        cur = conn.cursor()
        kpis = fetch(
            cur,
            """
            SELECT
              (SELECT COUNT(*) FROM dbo.Paciente)                              AS pacientes,
              (SELECT COUNT(*) FROM dbo.Empleado)                              AS empleados,
              (SELECT COUNT(*) FROM dbo.Empleado WHERE estado_activo = 1)      AS empleados_activos,
              (SELECT COUNT(*) FROM dbo.Insumo)                                AS insumos,
              (SELECT COUNT(*) FROM dbo.Insumo
                WHERE stock_existencia <= stock_maximo * 0.25)                 AS stock_bajo,
              (SELECT COUNT(*) FROM dbo.Cita)                                  AS citas,
              (SELECT COUNT(*) FROM dbo.Hospitalizacion WHERE estado = 'Activa') AS hosp_activas,
              (SELECT COUNT(*) FROM dbo.ADMISION)                              AS admisiones,
              (SELECT COUNT(*) FROM dbo.ASIGNACION_CONTACTO_EMERGENCIA)        AS contactos,
              (SELECT COUNT(*) FROM dbo.MOVIMIENTO_INVENTARIO)                 AS movimientos,
              (SELECT COUNT(*) FROM dbo.REGISTRO_TELEMETRIA)                   AS telemetria
            """,
        )[0]

        charts = {
            "pacientes_genero": serie(
                cur,
                "SELECT genero, COUNT(*) FROM dbo.Paciente "
                "GROUP BY genero ORDER BY COUNT(*) DESC;",
            ),
            "pacientes_edad": serie(
                cur,
                """
                SELECT grp.label, COUNT(*) AS total
                FROM (
                    SELECT CASE
                             WHEN DATEDIFF(YEAR, p.fecha_nacimiento, GETDATE()) < 18 THEN 1
                             WHEN DATEDIFF(YEAR, p.fecha_nacimiento, GETDATE()) < 40 THEN 2
                             WHEN DATEDIFF(YEAR, p.fecha_nacimiento, GETDATE()) < 60 THEN 3
                             ELSE 4
                           END AS ord,
                           CASE
                             WHEN DATEDIFF(YEAR, p.fecha_nacimiento, GETDATE()) < 18 THEN '0 a 17 anios'
                             WHEN DATEDIFF(YEAR, p.fecha_nacimiento, GETDATE()) < 40 THEN '18 a 39 anios'
                             WHEN DATEDIFF(YEAR, p.fecha_nacimiento, GETDATE()) < 60 THEN '40 a 59 anios'
                             ELSE '60 anios o mas'
                           END AS label
                    FROM dbo.Paciente p
                ) grp
                GROUP BY grp.ord, grp.label
                ORDER BY grp.ord;
                """,
            ),
            "citas_estado": serie(
                cur,
                "SELECT estado, COUNT(*) FROM dbo.Cita GROUP BY estado ORDER BY COUNT(*) DESC;",
            ),
            "hospitalizaciones_estado": serie(
                cur,
                "SELECT estado, COUNT(*) FROM dbo.Hospitalizacion GROUP BY estado ORDER BY COUNT(*) DESC;",
            ),
            "insumos_tipo": serie(
                cur,
                "SELECT tipo_insumo, COUNT(*) FROM dbo.Insumo GROUP BY tipo_insumo ORDER BY COUNT(*) DESC;",
            ),
            "insumos_proveedor": serie(
                cur,
                "SELECT p.razon_social, COUNT(*) FROM dbo.Insumo i "
                "JOIN dbo.Proveedor p ON p.id_proveedor = i.id_proveedor "
                "GROUP BY p.razon_social ORDER BY COUNT(*) DESC;",
            ),
            "empleados_rol": serie(
                cur,
                "SELECT rol, COUNT(*) FROM dbo.Empleado GROUP BY rol ORDER BY COUNT(*) DESC;",
            ),
            "movimientos_tipo": serie(
                cur,
                "SELECT tm.NombreTipoMovimiento, COUNT(*) "
                "FROM dbo.MOVIMIENTO_INVENTARIO m "
                "JOIN dbo.TIPO_MOVIMIENTO tm ON tm.IdTipoMovimiento = m.IdTipoMovimiento "
                "GROUP BY tm.NombreTipoMovimiento ORDER BY COUNT(*) DESC;",
            ),
        }
    return jsonify(kpis=kpis, charts=charts)


# ---------------------------------------------------------------------------
# PACIENTES
# ---------------------------------------------------------------------------
PACIENTE_SELECT = """
SELECT p.id_paciente,
       p.dpi,
       p.nombre,
       p.apellido,
       CONVERT(varchar(10), p.fecha_nacimiento, 23) AS fecha_nacimiento,
       p.genero,
       p.direccion,
       p.telefono,
       p.es_adulto_mayor,
       p.id_familiar,
       ISNULL(fr.nombre + ' ' + fr.apellido, '(sin asignar)') AS familiar,
       p.id_medico_externo,
       ISNULL(me.nombre + ' ' + me.apellido, '(sin asignar)') AS medico_externo,
       (SELECT COUNT(*) FROM dbo.Cita c WHERE c.id_paciente = p.id_paciente) AS citas,
       (SELECT COUNT(*) FROM dbo.Hospitalizacion h WHERE h.id_paciente = p.id_paciente) AS hospitalizaciones,
       (SELECT COUNT(*) FROM dbo.ADMISION a WHERE a.IdPaciente = p.id_paciente) AS admisiones,
       (SELECT COUNT(*) FROM dbo.REGISTRO_TELEMETRIA t WHERE t.IdPaciente = p.id_paciente) AS telemetria,
       (SELECT COUNT(*) FROM dbo.ASIGNACION_CONTACTO_EMERGENCIA ac WHERE ac.IdPaciente = p.id_paciente) AS contactos
FROM dbo.Paciente p
LEFT JOIN dbo.FamiliarResponsable fr ON fr.id_familiar = p.id_familiar
LEFT JOIN dbo.MedicoExterno me ON me.id_medico_externo = p.id_medico_externo
ORDER BY p.id_paciente;
"""


@app.get("/api/pacientes")
@login_required
def api_pacientes():
    with db() as conn:
        return jsonify(fetch(conn.cursor(), PACIENTE_SELECT))


@app.post("/api/pacientes")
@login_required
def api_paciente_crear():
    d = request.get_json(silent=True) or {}
    requeridos = [
        "dpi", "nombre", "apellido", "fecha_nacimiento", "genero",
        "direccion", "telefono", "id_familiar", "id_medico_externo",
    ]
    faltan = [c for c in requeridos if d.get(c) in (None, "")]
    if faltan:
        return jsonify(error="Campos obligatorios faltantes: " + ", ".join(faltan)), 400
    if d["genero"] not in ("Femenino", "Masculino", "Otro"):
        return jsonify(error="Genero no valido."), 400
    try:
        with db() as conn:
            conn.cursor().execute(
                """
                INSERT INTO dbo.Paciente
                    (dpi, nombre, apellido, fecha_nacimiento, genero, direccion,
                     telefono, es_adulto_mayor, id_familiar, id_medico_externo)
                VALUES (?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    d["dpi"].strip(),
                    d["nombre"].strip(),
                    d["apellido"].strip(),
                    d["fecha_nacimiento"],
                    d["genero"],
                    d["direccion"].strip(),
                    d["telefono"].strip(),
                    1 if d.get("es_adulto_mayor") else 0,
                    int(d["id_familiar"]),
                    int(d["id_medico_externo"]),
                ),
            )
    except pyodbc.Error as exc:
        return error_response(exc)
    return jsonify(ok=True)


@app.delete("/api/pacientes/<int:id_paciente>")
@login_required
def api_paciente_eliminar(id_paciente):
    try:
        with db() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM dbo.REGISTRO_TELEMETRIA WHERE IdPaciente=?;", (id_paciente,))
            telemetria = cur.rowcount
            cur.execute("DELETE FROM dbo.ASIGNACION_CONTACTO_EMERGENCIA WHERE IdPaciente=?;", (id_paciente,))
            contactos = cur.rowcount
            cur.execute("DELETE FROM dbo.ADMISION WHERE IdPaciente=?;", (id_paciente,))
            admisiones = cur.rowcount
            cur.execute("DELETE FROM dbo.Hospitalizacion WHERE id_paciente=?;", (id_paciente,))
            hosp = cur.rowcount
            cur.execute("DELETE FROM dbo.Cita WHERE id_paciente=?;", (id_paciente,))
            citas = cur.rowcount
            cur.execute("DELETE FROM dbo.Paciente WHERE id_paciente=?;", (id_paciente,))
            if cur.rowcount == 0:
                raise LookupError("No existe el paciente indicado.")
    except LookupError as exc:
        return jsonify(error=str(exc)), 404
    except pyodbc.Error as exc:
        return error_response(exc)
    return jsonify(
        ok=True,
        detalle=(
            "Paciente eliminado. Tambien se borraron "
            f"{citas} cita(s), {hosp} hospitalizacion(es), {admisiones} admision(es), "
            f"{contactos} contacto(s) y {telemetria} registro(s) de telemetria."
        ),
    )


# ---------------------------------------------------------------------------
# EMPLEADOS
# ---------------------------------------------------------------------------
EMPLEADO_SELECT = """
SELECT e.id_empleado,
       e.nss,
       e.nombre,
       e.apellido,
       e.rol,
       e.estado_activo,
       e.id_turno,
       ISNULL(t.nombre_turno, '(sin turno)') AS nombre_turno,
       e.id_especialidad,
       ISNULL(esp.nombre_especialidad, '(sin especialidad)') AS nombre_especialidad,
       (SELECT COUNT(*) FROM dbo.Cita c WHERE c.id_empleado = e.id_empleado) AS citas,
       (SELECT COUNT(*) FROM dbo.AsignacionPersonalSala a WHERE a.id_empleado = e.id_empleado) AS asignaciones
FROM dbo.Empleado e
LEFT JOIN dbo.Turno t ON t.id_turno = e.id_turno
LEFT JOIN dbo.Especialidad esp ON esp.id_especialidad = e.id_especialidad
ORDER BY e.id_empleado;
"""


@app.get("/api/empleados")
@login_required
def api_empleados():
    with db() as conn:
        return jsonify(fetch(conn.cursor(), EMPLEADO_SELECT))


@app.post("/api/empleados")
@login_required
def api_empleado_crear():
    d = request.get_json(silent=True) or {}
    requeridos = ["nss", "nombre", "apellido", "rol", "id_turno"]
    faltan = [c for c in requeridos if d.get(c) in (None, "")]
    if faltan:
        return jsonify(error="Campos obligatorios faltantes: " + ", ".join(faltan)), 400
    if d["rol"] not in ("Medico", "Enfermeria", "Administrativo", "Tecnico", "Otro"):
        return jsonify(error="Rol no valido."), 400
    id_especialidad = d.get("id_especialidad") or None
    try:
        with db() as conn:
            conn.cursor().execute(
                """
                INSERT INTO dbo.Empleado
                    (nss, nombre, apellido, rol, estado_activo, id_turno, id_especialidad)
                VALUES (?,?,?,?,?,?,?)
                """,
                (
                    d["nss"].strip(),
                    d["nombre"].strip(),
                    d["apellido"].strip(),
                    d["rol"],
                    1 if d.get("estado_activo", True) else 0,
                    int(d["id_turno"]),
                    int(id_especialidad) if id_especialidad else None,
                ),
            )
    except pyodbc.Error as exc:
        return error_response(exc)
    return jsonify(ok=True)


@app.delete("/api/empleados/<int:id_empleado>")
@login_required
def api_empleado_eliminar(id_empleado):
    try:
        with db() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM dbo.Cita WHERE id_empleado=?;", (id_empleado,))
            citas = cur.rowcount
            cur.execute("DELETE FROM dbo.AsignacionPersonalSala WHERE id_empleado=?;", (id_empleado,))
            asig = cur.rowcount
            cur.execute("DELETE FROM dbo.Empleado WHERE id_empleado=?;", (id_empleado,))
            if cur.rowcount == 0:
                raise LookupError("No existe el empleado indicado.")
    except LookupError as exc:
        return jsonify(error=str(exc)), 404
    except pyodbc.Error as exc:
        return error_response(exc)
    return jsonify(
        ok=True,
        detalle=f"Empleado eliminado. Tambien se borraron {citas} cita(s) y {asig} asignacion(es).",
    )


# ---------------------------------------------------------------------------
# INSUMOS
# ---------------------------------------------------------------------------
INSUMO_SELECT = """
SELECT i.id_insumo,
       i.codigo_insumo,
       i.nombre_insumo,
       i.tipo_insumo,
       i.stock_existencia,
       i.stock_maximo,
       i.costo_unitario,
       i.id_proveedor,
       ISNULL(p.razon_social, '(sin proveedor)') AS proveedor,
       (SELECT COUNT(*) FROM dbo.MOVIMIENTO_INVENTARIO m WHERE m.IdInsumo = i.id_insumo) AS movimientos
FROM dbo.Insumo i
LEFT JOIN dbo.Proveedor p ON p.id_proveedor = i.id_proveedor
ORDER BY i.id_insumo;
"""


@app.get("/api/insumos")
@login_required
def api_insumos():
    with db() as conn:
        return jsonify(fetch(conn.cursor(), INSUMO_SELECT))


@app.post("/api/insumos")
@login_required
def api_insumo_crear():
    d = request.get_json(silent=True) or {}
    requeridos = [
        "codigo_insumo", "nombre_insumo", "tipo_insumo",
        "stock_existencia", "stock_maximo", "costo_unitario", "id_proveedor",
    ]
    faltan = [c for c in requeridos if d.get(c) in (None, "")]
    if faltan:
        return jsonify(error="Campos obligatorios faltantes: " + ", ".join(faltan)), 400
    try:
        existencia = Decimal(str(d["stock_existencia"]))
        maximo = Decimal(str(d["stock_maximo"]))
        costo = Decimal(str(d["costo_unitario"]))
    except Exception:
        return jsonify(error="Los valores de existencia, maximo y costo deben ser numericos."), 400
    if existencia < 0 or maximo <= 0 or existencia > maximo:
        return jsonify(
            error="El stock de existencia debe estar entre 0 y el stock maximo, "
            "y el stock maximo debe ser mayor que 0.",
        ), 400
    if costo < 0:
        return jsonify(error="El costo unitario no puede ser negativo."), 400
    try:
        with db() as conn:
            conn.cursor().execute(
                """
                INSERT INTO dbo.Insumo
                    (codigo_insumo, nombre_insumo, tipo_insumo,
                     stock_existencia, stock_maximo, costo_unitario, id_proveedor)
                VALUES (?,?,?,?,?,?,?)
                """,
                (
                    d["codigo_insumo"].strip(),
                    d["nombre_insumo"].strip(),
                    d["tipo_insumo"].strip(),
                    existencia,
                    maximo,
                    costo,
                    int(d["id_proveedor"]),
                ),
            )
    except pyodbc.Error as exc:
        return error_response(exc)
    return jsonify(ok=True)


@app.delete("/api/insumos/<int:id_insumo>")
@login_required
def api_insumo_eliminar(id_insumo):
    try:
        with db() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM dbo.MOVIMIENTO_INVENTARIO WHERE IdInsumo=?;", (id_insumo,))
            movimientos = cur.rowcount
            cur.execute("DELETE FROM dbo.Insumo WHERE id_insumo=?;", (id_insumo,))
            if cur.rowcount == 0:
                raise LookupError("No existe el insumo indicado.")
    except LookupError as exc:
        return jsonify(error=str(exc)), 404
    except pyodbc.Error as exc:
        return error_response(exc)
    return jsonify(
        ok=True,
        detalle=f"Insumo eliminado. Tambien se borraron {movimientos} movimiento(s) de inventario.",
    )


# ---------------------------------------------------------------------------
# ADMISIONES
# ---------------------------------------------------------------------------
ADMISION_SELECT = """
SELECT a.IdAdmision,
       a.IdPaciente,
       p.nombre + ' ' + p.apellido AS paciente,
       p.dpi,
       a.IdMedicoExterno,
       ISNULL(me.nombre + ' ' + me.apellido, '(sin medico)') AS medico,
       CONVERT(varchar(19), a.FechaRegistro, 120) AS fecha
FROM dbo.ADMISION a
JOIN dbo.Paciente p ON p.id_paciente = a.IdPaciente
LEFT JOIN dbo.MedicoExterno me ON me.id_medico_externo = a.IdMedicoExterno
ORDER BY a.FechaRegistro DESC, a.IdAdmision DESC;
"""


@app.get("/api/admisiones")
@login_required
def api_admisiones():
    with db() as conn:
        return jsonify(fetch(conn.cursor(), ADMISION_SELECT))


@app.post("/api/admisiones")
@login_required
def api_admision_crear():
    d = request.get_json(silent=True) or {}
    if d.get("id_paciente") in (None, ""):
        return jsonify(error="Debe seleccionar un paciente."), 400
    fecha = (d.get("fecha") or "").replace("T", " ") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    medico = d.get("id_medico_externo") or None
    try:
        with db() as conn:
            conn.cursor().execute(
                "INSERT INTO dbo.ADMISION (IdPaciente, IdMedicoExterno, FechaRegistro) VALUES (?,?,?);",
                (int(d["id_paciente"]), int(medico) if medico else None, fecha),
            )
    except pyodbc.Error as exc:
        return error_response(exc)
    return jsonify(ok=True)


@app.delete("/api/admisiones/<int:id_admision>")
@login_required
def api_admision_eliminar(id_admision):
    try:
        with db() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM dbo.ADMISION WHERE IdAdmision=?;", (id_admision,))
            if cur.rowcount == 0:
                raise LookupError("No existe la admision indicada.")
    except LookupError as exc:
        return jsonify(error=str(exc)), 404
    except pyodbc.Error as exc:
        return error_response(exc)
    return jsonify(ok=True, detalle="Admision eliminada.")


# ---------------------------------------------------------------------------
# CONTACTOS DE EMERGENCIA (ASIGNACION_CONTACTO_EMERGENCIA)
# ---------------------------------------------------------------------------
CONTACTO_SELECT = """
SELECT a.IdAsignacion,
       a.IdPaciente,
       p.nombre + ' ' + p.apellido AS paciente,
       p.dpi,
       a.IdFamiliar,
       f.nombre + ' ' + f.apellido AS contacto,
       f.telefono,
       a.IdParentesco,
       pa.NombreParentesco AS parentesco
FROM dbo.ASIGNACION_CONTACTO_EMERGENCIA a
JOIN dbo.Paciente p ON p.id_paciente = a.IdPaciente
JOIN dbo.FamiliarResponsable f ON f.id_familiar = a.IdFamiliar
JOIN dbo.PARENTESCO pa ON pa.IdParentesco = a.IdParentesco
ORDER BY p.nombre, p.apellido, f.nombre;
"""


@app.get("/api/contactos")
@login_required
def api_contactos():
    with db() as conn:
        return jsonify(fetch(conn.cursor(), CONTACTO_SELECT))


@app.post("/api/contactos")
@login_required
def api_contacto_crear():
    d = request.get_json(silent=True) or {}
    requeridos = ["id_paciente", "id_familiar", "id_parentesco"]
    faltan = [c for c in requeridos if d.get(c) in (None, "")]
    if faltan:
        return jsonify(error="Campos obligatorios faltantes: " + ", ".join(faltan)), 400
    try:
        with db() as conn:
            conn.cursor().execute(
                "INSERT INTO dbo.ASIGNACION_CONTACTO_EMERGENCIA "
                "(IdPaciente, IdFamiliar, IdParentesco) VALUES (?,?,?);",
                (int(d["id_paciente"]), int(d["id_familiar"]), int(d["id_parentesco"])),
            )
    except pyodbc.Error as exc:
        return error_response(exc)
    return jsonify(ok=True)


@app.delete("/api/contactos/<int:id_asignacion>")
@login_required
def api_contacto_eliminar(id_asignacion):
    try:
        with db() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM dbo.ASIGNACION_CONTACTO_EMERGENCIA WHERE IdAsignacion=?;", (id_asignacion,))
            if cur.rowcount == 0:
                raise LookupError("No existe el contacto indicado.")
    except LookupError as exc:
        return jsonify(error=str(exc)), 404
    except pyodbc.Error as exc:
        return error_response(exc)
    return jsonify(ok=True, detalle="Contacto de emergencia eliminado.")


# ---------------------------------------------------------------------------
# MOVIMIENTOS DE INVENTARIO
# ---------------------------------------------------------------------------
MOVIMIENTO_SELECT = """
SELECT m.IdMovimiento,
       m.IdInsumo,
       i.codigo_insumo,
       i.nombre_insumo,
       CONVERT(varchar(19), m.FechaHora, 120) AS fecha,
       m.IdTipoMovimiento,
       tm.NombreTipoMovimiento AS tipo,
       m.Cantidad AS cantidad,
       m.CostoUnitario AS costo_unitario,
       m.Observacion
FROM dbo.MOVIMIENTO_INVENTARIO m
JOIN dbo.Insumo i ON i.id_insumo = m.IdInsumo
JOIN dbo.TIPO_MOVIMIENTO tm ON tm.IdTipoMovimiento = m.IdTipoMovimiento
ORDER BY m.FechaHora DESC, m.IdMovimiento DESC;
"""


@app.get("/api/movimientos")
@login_required
def api_movimientos():
    with db() as conn:
        return jsonify(fetch(conn.cursor(), MOVIMIENTO_SELECT))


@app.post("/api/movimientos")
@login_required
def api_movimiento_crear():
    d = request.get_json(silent=True) or {}
    requeridos = ["id_insumo", "id_tipo_movimiento", "cantidad", "costo_unitario"]
    faltan = [c for c in requeridos if d.get(c) in (None, "")]
    if faltan:
        return jsonify(error="Campos obligatorios faltantes: " + ", ".join(faltan)), 400
    try:
        cantidad = decimal_positivo(d["cantidad"], "La cantidad", permitir_cero=False)
        costo = decimal_positivo(d["costo_unitario"], "El costo unitario")
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    fecha = (d.get("fecha") or "").replace("T", " ") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with db() as conn:
            conn.cursor().execute(
                """
                INSERT INTO dbo.MOVIMIENTO_INVENTARIO
                    (IdInsumo, FechaHora, IdTipoMovimiento, Cantidad, CostoUnitario, Observacion)
                VALUES (?,?,?,?,?,?)
                """,
                (
                    int(d["id_insumo"]),
                    fecha,
                    int(d["id_tipo_movimiento"]),
                    cantidad,
                    costo,
                    (d.get("observacion") or "").strip() or None,
                ),
            )
    except pyodbc.Error as exc:
        return error_response(exc)
    return jsonify(ok=True)


@app.delete("/api/movimientos/<int:id_movimiento>")
@login_required
def api_movimiento_eliminar(id_movimiento):
    try:
        with db() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM dbo.MOVIMIENTO_INVENTARIO WHERE IdMovimiento=?;", (id_movimiento,))
            if cur.rowcount == 0:
                raise LookupError("No existe el movimiento indicado.")
    except LookupError as exc:
        return jsonify(error=str(exc)), 404
    except pyodbc.Error as exc:
        return error_response(exc)
    return jsonify(ok=True, detalle="Movimiento eliminado.")


# ---------------------------------------------------------------------------
# TELEMETRIA (solo lectura)
# El panel clinico lee REGISTRO_TELEMETRIA. Las graficas leen el
# procesamiento PySpark: RESULTADO_PROCESAMIENTO_TELEMETRIA y
# RESUMEN_RIESGO_PACIENTE.
# ---------------------------------------------------------------------------
@app.get("/api/telemetria/analisis")
@login_required
def api_telemetria_analisis():
    vacio = {
        "kpis": {
            "total": 0,
            "pacientes": 0,
            "criticos": 0,
            "moderados": 0,
            "alertas": 0,
            "incompletos": 0,
            "sinteticos": 0,
        },
        "charts": {"riesgo": [], "alertas": []},
        "resumen": [],
    }
    try:
        with db() as conn:
            cur = conn.cursor()
            kpis = fetch(
                cur,
                """
                SELECT
                  (SELECT COUNT(*) FROM dbo.RESULTADO_PROCESAMIENTO_TELEMETRIA) AS total,
                  (SELECT COUNT(*) FROM dbo.RESUMEN_RIESGO_PACIENTE) AS pacientes,
                  (SELECT ISNULL(SUM(RegistrosCriticos), 0) FROM dbo.RESUMEN_RIESGO_PACIENTE) AS criticos,
                  (SELECT ISNULL(SUM(RegistrosModerados), 0) FROM dbo.RESUMEN_RIESGO_PACIENTE) AS moderados,
                  (SELECT ISNULL(SUM(AlertasSpO2), 0) FROM dbo.RESUMEN_RIESGO_PACIENTE) AS alertas,
                  (SELECT ISNULL(SUM(RegistrosIncompletos), 0) FROM dbo.RESUMEN_RIESGO_PACIENTE) AS incompletos,
                  (SELECT ISNULL(SUM(CASE WHEN EsSintetico = 1 THEN 1 ELSE 0 END), 0)
                     FROM dbo.RESULTADO_PROCESAMIENTO_TELEMETRIA) AS sinteticos
                """,
            )[0]
            charts = {
                "riesgo": serie(
                    cur,
                    """
                    SELECT Nivel_Riesgo, COUNT(*)
                    FROM dbo.RESULTADO_PROCESAMIENTO_TELEMETRIA
                    GROUP BY Nivel_Riesgo
                    ORDER BY COUNT(*) DESC;
                    """,
                ),
                "alertas": serie(
                    cur,
                    """
                    SELECT
                      CASE WHEN AlertaSpO2 = 1 THEN N'Con alerta SpO2' ELSE N'Sin alerta SpO2' END,
                      COUNT(*)
                    FROM dbo.RESULTADO_PROCESAMIENTO_TELEMETRIA
                    GROUP BY CASE WHEN AlertaSpO2 = 1 THEN N'Con alerta SpO2' ELSE N'Sin alerta SpO2' END
                    ORDER BY COUNT(*) DESC;
                    """,
                ),
            }
            resumen = fetch(
                cur,
                """
                SELECT r.IdPaciente,
                       CASE
                         WHEN p.id_paciente IS NULL
                           THEN N'Paciente #' + CAST(r.IdPaciente AS varchar(12))
                         ELSE p.nombre + N' ' + p.apellido
                       END AS paciente,
                       ISNULL(p.dpi, N'') AS dpi,
                       r.TotalRegistros,
                       r.RegistrosCriticos,
                       r.RegistrosModerados,
                       r.AlertasSpO2,
                       r.RegistrosIncompletos,
                       CONVERT(varchar(19), r.UltimaMedicion, 120) AS ultima,
                       CONVERT(varchar(19), r.FechaProcesamiento, 120) AS procesado
                FROM dbo.RESUMEN_RIESGO_PACIENTE r
                LEFT JOIN dbo.Paciente p ON p.id_paciente = r.IdPaciente
                ORDER BY r.TotalRegistros DESC, r.IdPaciente;
                """,
            )
    except pyodbc.Error as exc:
        vacio["error"] = friendly_error(exc)
        return jsonify(vacio)
    return jsonify(kpis=kpis, charts=charts, resumen=resumen)


@app.get("/api/telemetria")
@login_required
def api_telemetria():
    with db() as conn:
        return jsonify(
            fetch(
                conn.cursor(),
                """
                SELECT t.IdRegistro,
                       t.IdPaciente,
                       p.nombre + ' ' + p.apellido AS paciente,
                       p.dpi,
                       CONVERT(varchar(19), t.MarcaTiempo, 120) AS marca,
                       t.FrecuenciaCardiaca,
                       t.SaturacionOxigeno,
                       t.AlertaGenerada
                FROM dbo.REGISTRO_TELEMETRIA t
                JOIN dbo.Paciente p ON p.id_paciente = t.IdPaciente
                ORDER BY t.MarcaTiempo DESC, t.IdRegistro DESC;
                """,
            )
        )


if __name__ == "__main__":
    print("=" * 60)
    print(" Hospital W 2.0 - Panel de Administracion")
    print(f" Servidor : {DB_SERVER}")
    print(f" Base     : {DB_NAME}")
    print(" Usuario  : " + ADMIN_USER + "   (clave configurable)")
    print(" Abrir    : http://127.0.0.1:5000")
    print("=" * 60)
    app.run(host="127.0.0.1", port=5000, debug=False)
