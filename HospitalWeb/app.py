"""
Hospital W 2.0 - Panel de Administracion
Backend Flask + pyodbc (SQL Server, autenticacion de Windows).

Permite al administrador consultar, registrar y modificar:
  - Pacientes, admisiones y contactos de emergencia
  - Empleados, con baja logica (el borrado fisico del personal queda rechazado)
  - Insumos y movimientos de inventario, que actualizan la existencia
  - Hospitalizaciones y asignacion de camas
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


def mensaje_tecnico(exc):
    if isinstance(exc, pyodbc.Error) and len(exc.args) > 1:
        return str(exc.args[1])
    return str(exc)


def traducir_error(exc):
    """Convierte errores de SQL Server en un texto util para la interfaz."""
    bajo = mensaje_tecnico(exc).lower()
    reglas = (
        ("uq_empleado_nss", "Ese NSS ya está registrado."),
        ("uq_paciente_dpi", "Ese DPI ya está registrado."),
        ("uq_insumo_codigo", "Ese código de insumo ya está registrado."),
        ("uq_asignacion_contacto", "Ese paciente ya tiene asignado a ese familiar."),
        ("ux_hospitalizacion_cama_activa", "Esa cama ya está ocupada por una hospitalización activa."),
        ("ux_movimiento_idempotencia", "Ese movimiento ya fue registrado y no se aplicó de nuevo."),
        ("51002", "No se puede cambiar el rol porque el empleado tiene citas y debe seguir siendo médico."),
        ("51001", "Una cita solo puede asignarse a un empleado con rol médico."),
        ("ck_insumo_stock", "La existencia debe estar entre 0 y el stock máximo."),
        ("ck_insumo_costo", "El costo no puede ser negativo."),
        ("ck_movimiento_cantidad", "La cantidad debe ser mayor que cero."),
        ("ck_movimiento_costo", "El costo del movimiento no puede ser negativo."),
        ("ck_hospitalizacion_fechas", "La salida no puede ser anterior al ingreso."),
        ("ck_hospitalizacion_consistencia", "El estado de la hospitalización no coincide con la fecha de salida."),
        ("ck_hospitalizacion_estado", "El estado de hospitalización no es válido."),
        ("fk_empleado_turno", "El turno seleccionado no existe."),
        ("fk_empleado_especialidad", "La especialidad seleccionada no existe."),
        ("fk_paciente_familiar", "El familiar responsable no existe."),
        ("fk_paciente_medicoexterno", "El médico externo no existe."),
        ("fk_insumo_proveedor", "El proveedor seleccionado no existe."),
        ("fk_hospitalizacion_cama", "La cama seleccionada no existe."),
        ("fk_hospitalizacion_paciente", "El paciente seleccionado no existe."),
        ("fk_admision_paciente", "El paciente de la admisión no existe."),
        ("fk_admision_medicoexterno", "El médico externo de la admisión no existe."),
        ("fk_asignacion_contacto_familiar", "El familiar del contacto no existe."),
        ("fk_asignacion_contacto_parentesco", "El parentesco seleccionado no existe."),
        ("fk_asignacion_contacto_paciente", "El paciente del contacto no existe."),
        ("fk_movimiento_insumo", "El insumo del movimiento no existe."),
        ("fk_movimiento_tipomovimiento", "El tipo de movimiento no existe."),
        ("foreign key", "Hay una asociación con un registro que no existe."),
        ("unique", "Ya existe un registro con esos datos."),
        ("check constraint", "Algún valor no cumple las reglas de la base de datos."),
    )
    for clave, texto in reglas:
        if clave in bajo:
            return texto
    return "No se pudo guardar la información. Revise los datos e intente otra vez."


def friendly_error(exc):
    return traducir_error(exc)


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not session.get("user"):
            return jsonify(error="Sesion no iniciada."), 401
        return view(*args, **kwargs)

    return wrapper


def error_response(exc):
    tecnico = mensaje_tecnico(exc)
    app.logger.warning("Error de base de datos: %s", tecnico)
    bajo = tecnico.lower()
    codigo = 409 if isinstance(exc, pyodbc.IntegrityError) or "51001" in bajo or "51002" in bajo else 400
    return jsonify(error=traducir_error(exc)), codigo


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
        raise ValueError(f"{nombre} debe ser numérico.")
    if n < 0:
        raise ValueError(f"{nombre} no puede ser negativa.")
    if not permitir_cero and n == 0:
        raise ValueError(f"{nombre} debe ser mayor que cero.")
    return n


def nuevo_stock(actual, maximo, tipo, cantidad):
    """Calcula la existencia resultante de un movimiento.

    Entrada y Devolucion suman. Salida resta y no puede pasar de la
    existencia. Ajuste sustituye la existencia por la cantidad contada:
    el dato histórico «Ajuste por conteo fisico» describe un conteo, y
    la columna Cantidad no guarda un signo. Los movimientos ya guardados
    no se reprocesan.
    """
    actual = Decimal(actual)
    maximo = Decimal(maximo)
    cantidad = Decimal(cantidad)
    nombre = (tipo or "").strip().lower()
    if nombre in ("entrada", "devolucion", "devolución"):
        nuevo = actual + cantidad
    elif nombre == "salida":
        if cantidad > actual:
            raise ValueError("La salida supera la existencia disponible.")
        nuevo = actual - cantidad
    elif nombre == "ajuste":
        nuevo = cantidad
    else:
        raise ValueError("Tipo de movimiento no reconocido.")
    if nuevo < 0:
        raise ValueError("La existencia no puede quedar negativa.")
    if nuevo > maximo:
        raise ValueError("La operación superaría el stock máximo del insumo.")
    return nuevo


def faltantes(datos, campos):
    return [c for c in campos if datos.get(c) in (None, "")]


def entero_id(valor, nombre):
    try:
        return int(valor)
    except (TypeError, ValueError):
        raise ValueError(f"{nombre} no es válido.")


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
            "empleados_activos": fetch(
                cur,
                "SELECT id_empleado, nombre + ' ' + apellido AS nombre_completo, rol "
                "FROM dbo.Empleado WHERE estado_activo = 1 ORDER BY nombre, apellido;",
            ),
            "camas_disponibles": fetch(
                cur,
                """
                SELECT c.id_cama, c.numero_cama, s.nombre_sala
                FROM dbo.Cama c
                JOIN dbo.Sala s ON s.id_sala = c.id_sala
                WHERE NOT EXISTS (
                    SELECT 1 FROM dbo.Hospitalizacion h
                    WHERE h.id_cama = c.id_cama AND h.estado = N'Activa'
                )
                ORDER BY s.nombre_sala, c.numero_cama;
                """,
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


def _validar_paciente(d):
    requeridos = [
        "dpi", "nombre", "apellido", "fecha_nacimiento", "genero",
        "direccion", "telefono", "id_familiar", "id_medico_externo",
    ]
    faltan = faltantes(d, requeridos)
    if faltan:
        raise ValueError("Campos obligatorios faltantes: " + ", ".join(faltan))
    if d["genero"] not in ("Femenino", "Masculino", "Otro"):
        raise ValueError("Género no válido.")
    return (
        d["dpi"].strip(),
        d["nombre"].strip(),
        d["apellido"].strip(),
        d["fecha_nacimiento"],
        d["genero"],
        d["direccion"].strip(),
        d["telefono"].strip(),
        1 if d.get("es_adulto_mayor") else 0,
        entero_id(d["id_familiar"], "El familiar"),
        entero_id(d["id_medico_externo"], "El médico externo"),
    )


@app.put("/api/pacientes/<int:id_paciente>")
@login_required
def api_paciente_editar(id_paciente):
    d = request.get_json(silent=True) or {}
    try:
        valores = _validar_paciente(d)
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    try:
        with db() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE dbo.Paciente
                SET dpi=?, nombre=?, apellido=?, fecha_nacimiento=?, genero=?,
                    direccion=?, telefono=?, es_adulto_mayor=?,
                    id_familiar=?, id_medico_externo=?
                WHERE id_paciente=?
                """,
                (*valores, id_paciente),
            )
            if cur.rowcount == 0:
                raise LookupError("No existe el paciente indicado.")
    except LookupError as exc:
        return jsonify(error=str(exc)), 404
    except pyodbc.Error as exc:
        return error_response(exc)
    return jsonify(ok=True)


@app.delete("/api/pacientes/<int:id_paciente>")
@login_required
def api_paciente_eliminar(id_paciente):
    try:
        with db() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT
                  (SELECT COUNT(*) FROM dbo.Cita WHERE id_paciente=?) +
                  (SELECT COUNT(*) FROM dbo.Hospitalizacion WHERE id_paciente=?) +
                  (SELECT COUNT(*) FROM dbo.ADMISION WHERE IdPaciente=?) +
                  (SELECT COUNT(*) FROM dbo.ASIGNACION_CONTACTO_EMERGENCIA WHERE IdPaciente=?) +
                  (SELECT COUNT(*) FROM dbo.REGISTRO_TELEMETRIA WHERE IdPaciente=?)
                """,
                (id_paciente, id_paciente, id_paciente, id_paciente, id_paciente),
            )
            historial = int(cur.fetchone()[0])
            if historial:
                return jsonify(
                    error="Este paciente tiene historial clínico. No se elimina para conservar "
                    "admisiones, hospitalizaciones, contactos, citas y telemetría."
                ), 409
            cur.execute("DELETE FROM dbo.Paciente WHERE id_paciente=?;", (id_paciente,))
            if cur.rowcount == 0:
                raise LookupError("No existe el paciente indicado.")
    except LookupError as exc:
        return jsonify(error=str(exc)), 404
    except pyodbc.Error as exc:
        return error_response(exc)
    return jsonify(ok=True, detalle="Paciente eliminado. No tenía historial asociado.")


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


def _valores_empleado(d):
    requeridos = ["nss", "nombre", "apellido", "rol", "id_turno"]
    vacios = faltantes(d, requeridos)
    if vacios:
        raise ValueError("Campos obligatorios faltantes: " + ", ".join(vacios))
    if d["rol"] not in ("Medico", "Enfermeria", "Administrativo", "Tecnico", "Otro"):
        raise ValueError("Rol no válido.")
    id_especialidad = d.get("id_especialidad") or None
    return (
        d["nss"].strip(),
        d["nombre"].strip(),
        d["apellido"].strip(),
        d["rol"],
        1 if d.get("estado_activo", True) else 0,
        entero_id(d["id_turno"], "El turno"),
        entero_id(id_especialidad, "La especialidad") if id_especialidad else None,
    )


@app.put("/api/empleados/<int:id_empleado>")
@login_required
def api_empleado_editar(id_empleado):
    d = request.get_json(silent=True) or {}
    try:
        valores = _valores_empleado(d)
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    try:
        with db() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE dbo.Empleado
                SET nss=?, nombre=?, apellido=?, rol=?, estado_activo=?,
                    id_turno=?, id_especialidad=?
                WHERE id_empleado=?
                """,
                (*valores, id_empleado),
            )
            if cur.rowcount == 0:
                raise LookupError("No existe el empleado indicado.")
    except LookupError as exc:
        return jsonify(error=str(exc)), 404
    except pyodbc.Error as exc:
        return error_response(exc)
    return jsonify(ok=True)


@app.post("/api/empleados/<int:id_empleado>/baja")
@login_required
def api_empleado_baja(id_empleado):
    """Baja lógica e idempotente. No borra citas ni asignaciones."""
    try:
        with db() as conn:
            cur = conn.cursor()
            cur.execute(
                "UPDATE dbo.Empleado SET estado_activo=0 WHERE id_empleado=?;",
                (id_empleado,),
            )
            if cur.rowcount == 0:
                cur.execute("SELECT estado_activo FROM dbo.Empleado WHERE id_empleado=?;", (id_empleado,))
                if cur.fetchone() is None:
                    raise LookupError("No existe el empleado indicado.")
    except LookupError as exc:
        return jsonify(error=str(exc)), 404
    except pyodbc.Error as exc:
        return error_response(exc)
    return jsonify(ok=True, detalle="Empleado inactivo. Su historial de citas y asignaciones se conserva.")


@app.delete("/api/empleados/<int:id_empleado>")
@login_required
def api_empleado_eliminar(id_empleado):
    return jsonify(
        error="La baja del personal es lógica y conserva el historial. Use la acción Dar de baja."
    ), 405


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


def _valores_insumo(d):
    requeridos = [
        "codigo_insumo", "nombre_insumo", "tipo_insumo",
        "stock_existencia", "stock_maximo", "costo_unitario", "id_proveedor",
    ]
    vacios = faltantes(d, requeridos)
    if vacios:
        raise ValueError("Campos obligatorios faltantes: " + ", ".join(vacios))
    existencia = decimal_positivo(d["stock_existencia"], "La existencia")
    maximo = decimal_positivo(d["stock_maximo"], "El stock máximo", permitir_cero=False)
    costo = decimal_positivo(d["costo_unitario"], "El costo unitario")
    if existencia > maximo:
        raise ValueError("La existencia no puede ser mayor que el stock máximo.")
    return (
        d["codigo_insumo"].strip(),
        d["nombre_insumo"].strip(),
        d["tipo_insumo"].strip(),
        existencia,
        maximo,
        costo,
        entero_id(d["id_proveedor"], "El proveedor"),
    )


@app.put("/api/insumos/<int:id_insumo>")
@login_required
def api_insumo_editar(id_insumo):
    d = request.get_json(silent=True) or {}
    try:
        valores = _valores_insumo(d)
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    try:
        with db() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE dbo.Insumo
                SET codigo_insumo=?, nombre_insumo=?, tipo_insumo=?,
                    stock_existencia=?, stock_maximo=?, costo_unitario=?, id_proveedor=?
                WHERE id_insumo=?
                """,
                (*valores, id_insumo),
            )
            if cur.rowcount == 0:
                raise LookupError("No existe el insumo indicado.")
    except LookupError as exc:
        return jsonify(error=str(exc)), 404
    except pyodbc.Error as exc:
        return error_response(exc)
    return jsonify(ok=True)


@app.delete("/api/insumos/<int:id_insumo>")
@login_required
def api_insumo_eliminar(id_insumo):
    try:
        with db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM dbo.MOVIMIENTO_INVENTARIO WHERE IdInsumo=?;", (id_insumo,))
            movimientos = int(cur.fetchone()[0])
            if movimientos:
                return jsonify(
                    error="Este insumo tiene movimientos. El historial se conserva y el insumo no se elimina."
                ), 409
            cur.execute("DELETE FROM dbo.Insumo WHERE id_insumo=?;", (id_insumo,))
            if cur.rowcount == 0:
                raise LookupError("No existe el insumo indicado.")
    except LookupError as exc:
        return jsonify(error=str(exc)), 404
    except pyodbc.Error as exc:
        return error_response(exc)
    return jsonify(ok=True, detalle="Insumo eliminado. No tenía movimientos.")


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


@app.put("/api/admisiones/<int:id_admision>")
@login_required
def api_admision_editar(id_admision):
    """Actualiza paciente y médico. La fecha de registro no se modifica."""
    d = request.get_json(silent=True) or {}
    if d.get("id_paciente") in (None, ""):
        return jsonify(error="Debe seleccionar un paciente."), 400
    medico = d.get("id_medico_externo") or None
    try:
        with db() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE dbo.ADMISION
                SET IdPaciente=?, IdMedicoExterno=?
                WHERE IdAdmision=?
                """,
                (entero_id(d["id_paciente"], "El paciente"), int(medico) if medico else None, id_admision),
            )
            if cur.rowcount == 0:
                raise LookupError("No existe la admisión indicada.")
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    except LookupError as exc:
        return jsonify(error=str(exc)), 404
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


@app.put("/api/contactos/<int:id_asignacion>")
@login_required
def api_contacto_editar(id_asignacion):
    d = request.get_json(silent=True) or {}
    vacios = faltantes(d, ["id_paciente", "id_familiar", "id_parentesco"])
    if vacios:
        return jsonify(error="Campos obligatorios faltantes: " + ", ".join(vacios)), 400
    try:
        valores = (
            entero_id(d["id_paciente"], "El paciente"),
            entero_id(d["id_familiar"], "El familiar"),
            entero_id(d["id_parentesco"], "El parentesco"),
        )
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    try:
        with db() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE dbo.ASIGNACION_CONTACTO_EMERGENCIA
                SET IdPaciente=?, IdFamiliar=?, IdParentesco=?
                WHERE IdAsignacion=?
                """,
                (*valores, id_asignacion),
            )
            if cur.rowcount == 0:
                raise LookupError("No existe el contacto indicado.")
    except LookupError as exc:
        return jsonify(error=str(exc)), 404
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


def registrar_movimiento(conn, id_insumo, id_tipo, cantidad, costo, observacion=None, fecha=None, clave=None):
    """Inserta el movimiento y actualiza la existencia en la misma transacción.

    Bloquea la fila del insumo para que dos salidas simultáneas no consuman
    dos veces el mismo stock. Si la clave ya existe, no vuelve a descontar.
    """
    cur = conn.cursor()
    clave = (clave or "").strip() or None
    if clave:
        cur.execute(
            "SELECT IdMovimiento FROM dbo.MOVIMIENTO_INVENTARIO WITH (UPDLOCK, HOLDLOCK) "
            "WHERE ClaveIdempotencia=?;",
            (clave,),
        )
        previo = cur.fetchone()
        if previo:
            return {"duplicado": True, "id_movimiento": int(previo[0])}

    cur.execute(
        """
        SELECT stock_existencia, stock_maximo
        FROM dbo.Insumo WITH (UPDLOCK, ROWLOCK)
        WHERE id_insumo=?
        """,
        (id_insumo,),
    )
    insumo = cur.fetchone()
    if insumo is None:
        raise ValueError("El insumo seleccionado no existe.")
    cur.execute(
        "SELECT NombreTipoMovimiento FROM dbo.TIPO_MOVIMIENTO WHERE IdTipoMovimiento=?;",
        (id_tipo,),
    )
    tipo_fila = cur.fetchone()
    if tipo_fila is None:
        raise ValueError("El tipo de movimiento no existe.")
    actual, maximo = insumo
    tipo = tipo_fila[0]
    nuevo = nuevo_stock(actual, maximo, tipo, cantidad)
    momento = fecha or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute(
        """
        INSERT INTO dbo.MOVIMIENTO_INVENTARIO
            (IdInsumo, FechaHora, IdTipoMovimiento, Cantidad, CostoUnitario, Observacion, ClaveIdempotencia)
        OUTPUT inserted.IdMovimiento
        VALUES (?,?,?,?,?,?,?)
        """,
        (id_insumo, momento, id_tipo, cantidad, costo, observacion, clave),
    )
    id_movimiento = int(cur.fetchone()[0])
    cur.execute(
        "UPDATE dbo.Insumo SET stock_existencia=? WHERE id_insumo=?;",
        (nuevo, id_insumo),
    )
    return {
        "duplicado": False,
        "id_movimiento": id_movimiento,
        "stock_existencia": float(nuevo),
        "tipo": tipo,
    }


@app.post("/api/movimientos")
@login_required
def api_movimiento_crear():
    d = request.get_json(silent=True) or {}
    vacios = faltantes(d, ["id_insumo", "id_tipo_movimiento", "cantidad", "costo_unitario"])
    if vacios:
        return jsonify(error="Campos obligatorios faltantes: " + ", ".join(vacios)), 400
    try:
        cantidad = decimal_positivo(d["cantidad"], "La cantidad", permitir_cero=False)
        costo = decimal_positivo(d["costo_unitario"], "El costo unitario")
        id_insumo = entero_id(d["id_insumo"], "El insumo")
        id_tipo = entero_id(d["id_tipo_movimiento"], "El tipo de movimiento")
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    fecha = (d.get("fecha") or "").replace("T", " ") or None
    clave = (d.get("clave_idempotencia") or request.headers.get("Idempotency-Key") or "").strip() or None
    try:
        with db() as conn:
            resultado = registrar_movimiento(
                conn,
                id_insumo,
                id_tipo,
                cantidad,
                costo,
                (d.get("observacion") or "").strip() or None,
                fecha,
                clave,
            )
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    except pyodbc.Error as exc:
        return error_response(exc)
    return jsonify(ok=True, **resultado)


@app.delete("/api/movimientos/<int:id_movimiento>")
@login_required
def api_movimiento_eliminar(id_movimiento):
    return jsonify(
        error="Los movimientos forman el historial de inventario y no se eliminan. "
        "Registre una entrada, salida, devolución o ajuste para corregir la existencia."
    ), 405


# ---------------------------------------------------------------------------
# HOSPITALIZACION Y CAMAS
# ---------------------------------------------------------------------------
HOSPITALIZACION_SELECT = """
SELECT h.id_hospitalizacion,
       h.id_paciente,
       p.nombre + ' ' + p.apellido AS paciente,
       p.dpi,
       h.id_cama,
       c.numero_cama,
       s.nombre_sala,
       CONVERT(varchar(19), h.fecha_hora_ingreso, 120) AS ingreso,
       CONVERT(varchar(19), h.fecha_hora_salida_real, 120) AS salida,
       h.motivo_ingreso,
       h.estado
FROM dbo.Hospitalizacion h
JOIN dbo.Paciente p ON p.id_paciente = h.id_paciente
JOIN dbo.Cama c ON c.id_cama = h.id_cama
JOIN dbo.Sala s ON s.id_sala = c.id_sala
"""


@app.get("/api/hospitalizaciones")
@login_required
def api_hospitalizaciones():
    estado = (request.args.get("estado") or "").strip()
    paciente = (request.args.get("paciente") or "").strip()
    sql = HOSPITALIZACION_SELECT
    params = []
    filtros = []
    if estado:
        filtros.append("h.estado = ?")
        params.append(estado)
    if paciente:
        filtros.append("(p.nombre + ' ' + p.apellido LIKE ? OR p.dpi LIKE ?)")
        params.extend([f"%{paciente}%", f"%{paciente}%"])
    if filtros:
        sql += " WHERE " + " AND ".join(filtros)
    sql += " ORDER BY h.fecha_hora_ingreso DESC, h.id_hospitalizacion DESC;"
    with db() as conn:
        return jsonify(fetch(conn.cursor(), sql, tuple(params)))


@app.get("/api/camas/disponibles")
@login_required
def api_camas_disponibles():
    with db() as conn:
        return jsonify(fetch(
            conn.cursor(),
            """
            SELECT c.id_cama, c.numero_cama, s.nombre_sala, s.ubicacion_piso
            FROM dbo.Cama c
            JOIN dbo.Sala s ON s.id_sala = c.id_sala
            WHERE NOT EXISTS (
                SELECT 1 FROM dbo.Hospitalizacion h
                WHERE h.id_cama = c.id_cama AND h.estado = N'Activa'
            )
            ORDER BY s.nombre_sala, c.numero_cama;
            """,
        ))


def asignar_hospitalizacion(conn, id_paciente, id_cama, motivo):
    """Ocupa una cama libre dentro de la transacción ya abierta."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT c.id_cama
        FROM dbo.Cama c WITH (UPDLOCK, HOLDLOCK)
        WHERE c.id_cama = ?
          AND NOT EXISTS (
              SELECT 1
              FROM dbo.Hospitalizacion h WITH (UPDLOCK, HOLDLOCK)
              WHERE h.id_cama = c.id_cama AND h.estado = N'Activa'
          )
        """,
        (id_cama,),
    )
    if cur.fetchone() is None:
        cur.execute("SELECT 1 FROM dbo.Cama WHERE id_cama=?;", (id_cama,))
        if cur.fetchone() is None:
            raise LookupError("La cama seleccionada no existe.")
        raise ValueError("Esa cama ya está ocupada o no está disponible.")
    cur.execute("SELECT 1 FROM dbo.Paciente WHERE id_paciente=?;", (id_paciente,))
    if cur.fetchone() is None:
        raise LookupError("El paciente seleccionado no existe.")
    cur.execute(
        """
        INSERT INTO dbo.Hospitalizacion (id_paciente, id_cama, motivo_ingreso)
        OUTPUT inserted.id_hospitalizacion, inserted.estado,
               CONVERT(varchar(19), inserted.fecha_hora_ingreso, 120)
        VALUES (?, ?, ?)
        """,
        (id_paciente, id_cama, motivo),
    )
    ingreso_id, estado, fecha = cur.fetchone()
    return {"id_hospitalizacion": int(ingreso_id), "estado": estado, "ingreso": fecha}


@app.post("/api/hospitalizaciones")
@login_required
def api_hospitalizacion_crear():
    d = request.get_json(silent=True) or {}
    vacios = faltantes(d, ["id_paciente", "id_cama", "motivo_ingreso"])
    if vacios:
        return jsonify(error="Campos obligatorios faltantes: " + ", ".join(vacios)), 400
    motivo = str(d.get("motivo_ingreso") or "").strip()
    if not motivo:
        return jsonify(error="Indique el motivo de ingreso."), 400
    if len(motivo) > 300:
        return jsonify(error="El motivo admite como máximo 300 caracteres."), 400
    try:
        id_paciente = entero_id(d["id_paciente"], "El paciente")
        id_cama = entero_id(d["id_cama"], "La cama")
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    try:
        with db() as conn:
            resultado = asignar_hospitalizacion(conn, id_paciente, id_cama, motivo)
    except LookupError as exc:
        return jsonify(error=str(exc)), 404
    except ValueError as exc:
        return jsonify(error=str(exc)), 409
    except pyodbc.Error as exc:
        return error_response(exc)
    return jsonify(ok=True, **resultado)


@app.post("/api/hospitalizaciones/<int:id_hospitalizacion>/finalizar")
@login_required
def api_hospitalizacion_finalizar(id_hospitalizacion):
    try:
        with db() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT estado
                FROM dbo.Hospitalizacion WITH (UPDLOCK, HOLDLOCK)
                WHERE id_hospitalizacion=?
                """,
                (id_hospitalizacion,),
            )
            fila = cur.fetchone()
            if fila is None:
                raise LookupError("No existe la hospitalización indicada.")
            if fila[0] != "Activa":
                return jsonify(error="Esta hospitalización ya no está activa y no vuelve a finalizarse."), 409
            cur.execute(
                """
                UPDATE dbo.Hospitalizacion
                SET estado = N'Finalizada',
                    fecha_hora_salida_real = SYSDATETIME()
                WHERE id_hospitalizacion = ? AND estado = N'Activa'
                """,
                (id_hospitalizacion,),
            )
            if cur.rowcount == 0:
                return jsonify(error="Esta hospitalización ya no está activa y no vuelve a finalizarse."), 409
    except LookupError as exc:
        return jsonify(error=str(exc)), 404
    except pyodbc.Error as exc:
        return error_response(exc)
    return jsonify(ok=True, detalle="Hospitalización finalizada. La cama queda disponible.")


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
