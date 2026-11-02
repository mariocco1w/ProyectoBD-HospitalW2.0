import os
import sys

import pyodbc
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import app as hospital

PREFIJO = "QAFIN"


def conexion():
    return pyodbc.connect(hospital.CONN_STR, autocommit=True)


def conteos():
    with conexion() as cn:
        cur = cn.cursor()
        cur.execute(
            """
            SELECT
              (SELECT COUNT(*) FROM dbo.Paciente),
              (SELECT COUNT(*) FROM dbo.Empleado),
              (SELECT COUNT(*) FROM dbo.Insumo),
              (SELECT COUNT(*) FROM dbo.ADMISION),
              (SELECT COUNT(*) FROM dbo.ASIGNACION_CONTACTO_EMERGENCIA),
              (SELECT COUNT(*) FROM dbo.MOVIMIENTO_INVENTARIO),
              (SELECT COUNT(*) FROM dbo.Hospitalizacion),
              (SELECT COUNT(*) FROM dbo.Cama),
              (SELECT COUNT(*) FROM dbo.Cita)
            """
        )
        return tuple(cur.fetchone())


def limpiar():
    with conexion() as cn:
        cur = cn.cursor()
        cur.execute(
            "DELETE FROM dbo.MOVIMIENTO_INVENTARIO WHERE IdInsumo IN "
            "(SELECT id_insumo FROM dbo.Insumo WHERE codigo_insumo LIKE ?)",
            (PREFIJO + "%",),
        )
        cur.execute("DELETE FROM dbo.Insumo WHERE codigo_insumo LIKE ?", (PREFIJO + "%",))
        cur.execute(
            "DELETE FROM dbo.Cita WHERE id_paciente IN (SELECT id_paciente FROM dbo.Paciente WHERE dpi LIKE ?) "
            "OR id_empleado IN (SELECT id_empleado FROM dbo.Empleado WHERE nss LIKE ?)",
            (PREFIJO + "%", PREFIJO + "%"),
        )
        cur.execute(
            "DELETE FROM dbo.ASIGNACION_CONTACTO_EMERGENCIA WHERE IdPaciente IN "
            "(SELECT id_paciente FROM dbo.Paciente WHERE dpi LIKE ?)",
            (PREFIJO + "%",),
        )
        cur.execute(
            "DELETE FROM dbo.ADMISION WHERE IdPaciente IN (SELECT id_paciente FROM dbo.Paciente WHERE dpi LIKE ?)",
            (PREFIJO + "%",),
        )
        cur.execute(
            "DELETE FROM dbo.Hospitalizacion WHERE id_paciente IN "
            "(SELECT id_paciente FROM dbo.Paciente WHERE dpi LIKE ?) "
            "OR motivo_ingreso LIKE ?",
            (PREFIJO + "%", PREFIJO + "%"),
        )
        cur.execute(
            "DELETE FROM dbo.REGISTRO_TELEMETRIA WHERE IdPaciente IN "
            "(SELECT id_paciente FROM dbo.Paciente WHERE dpi LIKE ?)",
            (PREFIJO + "%",),
        )
        cur.execute("DELETE FROM dbo.Paciente WHERE dpi LIKE ?", (PREFIJO + "%",))
        cur.execute(
            "DELETE FROM dbo.AsignacionPersonalSala WHERE id_empleado IN "
            "(SELECT id_empleado FROM dbo.Empleado WHERE nss LIKE ?)",
            (PREFIJO + "%",),
        )
        cur.execute("DELETE FROM dbo.Empleado WHERE nss LIKE ?", (PREFIJO + "%",))
        cur.execute("DELETE FROM dbo.Cama WHERE numero_cama LIKE ?", (PREFIJO + "%",))


@pytest.fixture(scope="session")
def base():
    limpiar()
    antes = conteos()
    hospital.app.config["TESTING"] = True
    with hospital.app.test_client() as cliente:
        respuesta = cliente.post(
            "/api/login",
            json={"usuario": hospital.ADMIN_USER, "clave": hospital.ADMIN_PASS},
        )
        assert respuesta.status_code == 200
        catalogos = cliente.get("/api/catalogos").get_json()
        yield {"cliente": cliente, "catalogos": catalogos, "antes": antes}
    limpiar()
    assert conteos() == antes


@pytest.fixture
def cliente(base):
    return base["cliente"]


@pytest.fixture
def catalogos(base):
    return base["catalogos"]
