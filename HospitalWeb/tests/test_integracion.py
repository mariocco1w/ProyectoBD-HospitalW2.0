from threading import Thread

import pyodbc

import app as hospital
from tests.conftest import PREFIJO, conexion


def _id(sql, params=()):
    with conexion() as cn:
        cur = cn.cursor()
        cur.execute(sql, params)
        fila = cur.fetchone()
        return None if fila is None else fila[0]


def test_login_incorrecto_no_dice_sesion_expirada():
    hospital.app.config["TESTING"] = True
    with hospital.app.test_client() as anonimo:
        respuesta = anonimo.post("/api/login", json={"usuario": "nadie", "clave": "incorrecta"})
        assert respuesta.status_code == 401
        assert respuesta.get_json()["error"] == "Usuario o clave incorrectos."
        assert "expir" not in respuesta.get_json()["error"].lower()


def test_api_exige_sesion():
    hospital.app.config["TESTING"] = True
    with hospital.app.test_client() as anonimo:
        assert anonimo.get("/api/empleados").status_code == 401
        assert anonimo.post("/api/hospitalizaciones", json={}).status_code == 401


def test_rf1_alta_edicion_nss_duplicado_y_baja_logica(cliente, catalogos):
    turno = catalogos["turnos"][0]["id_turno"]
    especialidad = catalogos["especialidades"][0]["id_especialidad"]
    nss = PREFIJO + "-E01"
    alta = {
        "nss": nss, "nombre": "Alta", "apellido": "Prueba", "rol": "Medico",
        "id_turno": turno, "id_especialidad": especialidad, "estado_activo": True,
    }
    assert cliente.post("/api/empleados", json=alta).status_code == 200
    empleado_id = _id("SELECT id_empleado FROM dbo.Empleado WHERE nss=?", (nss,))
    editado = dict(alta, nombre="Editado", apellido="Persistente")
    assert cliente.put(f"/api/empleados/{empleado_id}", json=editado).status_code == 200
    fila = None
    with conexion() as cn:
        cur = cn.cursor()
        cur.execute("SELECT nombre, apellido, id_turno, id_especialidad, estado_activo FROM dbo.Empleado WHERE id_empleado=?", (empleado_id,))
        fila = cur.fetchone()
    assert fila[0] == "Editado" and fila[1] == "Persistente"
    assert int(fila[2]) == int(turno) and int(fila[3]) == int(especialidad)

    otro = dict(alta, nss=PREFIJO + "-E02", nombre="Otro")
    assert cliente.post("/api/empleados", json=otro).status_code == 200
    duplicado = cliente.put(
        f"/api/empleados/{empleado_id}",
        json=dict(editado, nss=PREFIJO + "-E02"),
    )
    assert duplicado.status_code == 409
    assert "NSS" in duplicado.get_json()["error"]
    assert "ODBC" not in duplicado.get_json()["error"]

    assert cliente.delete(f"/api/empleados/{empleado_id}").status_code == 405
    baja = cliente.post(f"/api/empleados/{empleado_id}/baja")
    assert baja.status_code == 200
    assert cliente.post(f"/api/empleados/{empleado_id}/baja").status_code == 200
    with conexion() as cn:
        cur = cn.cursor()
        cur.execute("SELECT estado_activo FROM dbo.Empleado WHERE nss=?", (nss,))
        assert cur.fetchone()[0] in (0, False)
        cur.execute("SELECT COUNT(*) FROM dbo.Cita WHERE id_empleado=?", (empleado_id,))
        assert cur.fetchone()[0] == 0
    activos = cliente.get("/api/catalogos").get_json()["empleados_activos"]
    assert all(item["id_empleado"] != empleado_id for item in activos)
    listado = cliente.get("/api/empleados").get_json()
    assert any(item["nss"] == nss and not item["estado_activo"] for item in listado)


def test_rf1_no_cambia_el_rol_de_un_medico_con_citas(cliente, catalogos):
    turno = catalogos["turnos"][0]["id_turno"]
    familiar = catalogos["familiares"][0]["id_familiar"]
    medico = catalogos["medicos"][0]["id_medico_externo"]
    nss = PREFIJO + "-E03"
    dpi = PREFIJO + "-P03"
    assert cliente.post("/api/empleados", json={
        "nss": nss, "nombre": "Medico", "apellido": "Citas", "rol": "Medico",
        "id_turno": turno, "estado_activo": True,
    }).status_code == 200
    assert cliente.post("/api/pacientes", json={
        "dpi": dpi, "nombre": "Paciente", "apellido": "Cita",
        "fecha_nacimiento": "1991-01-01", "genero": "Femenino",
        "direccion": "Dir", "telefono": "55550101",
        "id_familiar": familiar, "id_medico_externo": medico,
    }).status_code == 200
    empleado_id = _id("SELECT id_empleado FROM dbo.Empleado WHERE nss=?", (nss,))
    paciente_id = _id("SELECT id_paciente FROM dbo.Paciente WHERE dpi=?", (dpi,))
    with conexion() as cn:
        cn.cursor().execute(
            "INSERT INTO dbo.Cita (id_paciente, id_empleado, fecha_hora_cita, motivo) VALUES (?,?,?,?)",
            (paciente_id, empleado_id, "2026-11-02 10:00:00", PREFIJO),
        )
    respuesta = cliente.put(f"/api/empleados/{empleado_id}", json={
        "nss": nss, "nombre": "Medico", "apellido": "Citas", "rol": "Enfermeria",
        "id_turno": turno, "estado_activo": True,
    })
    assert respuesta.status_code == 409
    assert "médico" in respuesta.get_json()["error"].lower() or "medico" in respuesta.get_json()["error"].lower()
    assert _id("SELECT rol FROM dbo.Empleado WHERE id_empleado=?", (empleado_id,)) == "Medico"


def test_rf2_edicion_dpi_admision_y_contacto(cliente, catalogos):
    familiar = catalogos["familiares"][0]["id_familiar"]
    familiar2 = catalogos["familiares"][1]["id_familiar"]
    medico = catalogos["medicos"][0]["id_medico_externo"]
    medico2 = catalogos["medicos"][1]["id_medico_externo"]
    parentesco = catalogos["parentescos"][0]["IdParentesco"]
    parentesco2 = catalogos["parentescos"][1]["IdParentesco"]
    dpi = PREFIJO + "-P01"
    cuerpo = {
        "dpi": dpi, "nombre": "Paciente", "apellido": "Inicial",
        "fecha_nacimiento": "1992-02-02", "genero": "Masculino",
        "direccion": "Direccion inicial", "telefono": "55550001",
        "es_adulto_mayor": False, "id_familiar": familiar, "id_medico_externo": medico,
    }
    assert cliente.post("/api/pacientes", json=cuerpo).status_code == 200
    paciente_id = _id("SELECT id_paciente FROM dbo.Paciente WHERE dpi=?", (dpi,))
    cambio = dict(cuerpo, apellido="Editado", direccion="Direccion nueva", telefono="55550099", id_medico_externo=medico2)
    assert cliente.put(f"/api/pacientes/{paciente_id}", json=cambio).status_code == 200
    with conexion() as cn:
        cur = cn.cursor()
        cur.execute("SELECT apellido, direccion, telefono, id_medico_externo FROM dbo.Paciente WHERE id_paciente=?", (paciente_id,))
        fila = cur.fetchone()
    assert fila[0] == "Editado" and fila[1] == "Direccion nueva" and fila[2] == "55550099"
    assert int(fila[3]) == int(medico2)

    assert cliente.post("/api/pacientes", json=dict(cuerpo, dpi=PREFIJO + "-P02")).status_code == 200
    duplicado = cliente.put(f"/api/pacientes/{paciente_id}", json=dict(cambio, dpi=PREFIJO + "-P02"))
    assert duplicado.status_code == 409 and "DPI" in duplicado.get_json()["error"]
    inexistente = cliente.put(f"/api/pacientes/{paciente_id}", json=dict(cambio, id_familiar=999999))
    assert inexistente.status_code == 409
    assert cliente.put(f"/api/pacientes/{paciente_id}", json=dict(cambio, id_medico_externo=999999)).status_code == 409

    assert cliente.post("/api/admisiones", json={
        "id_paciente": paciente_id, "id_medico_externo": medico, "fecha": "2026-11-02T08:15:00",
    }).status_code == 200
    admision_id = _id("SELECT IdAdmision FROM dbo.ADMISION WHERE IdPaciente=?", (paciente_id,))
    assert cliente.put(f"/api/admisiones/{admision_id}", json={
        "id_paciente": paciente_id, "id_medico_externo": medico2,
    }).status_code == 200
    with conexion() as cn:
        cur = cn.cursor()
        cur.execute("SELECT IdMedicoExterno, CONVERT(varchar(19), FechaRegistro, 120) FROM dbo.ADMISION WHERE IdAdmision=?", (admision_id,))
        medico_guardado, fecha = cur.fetchone()
    assert int(medico_guardado) == int(medico2)
    assert fecha == "2026-11-02 08:15:00"

    assert cliente.post("/api/contactos", json={
        "id_paciente": paciente_id, "id_familiar": familiar, "id_parentesco": parentesco,
    }).status_code == 200
    contacto_id = _id(
        "SELECT IdAsignacion FROM dbo.ASIGNACION_CONTACTO_EMERGENCIA WHERE IdPaciente=? AND IdFamiliar=?",
        (paciente_id, familiar),
    )
    assert cliente.put(f"/api/contactos/{contacto_id}", json={
        "id_paciente": paciente_id, "id_familiar": familiar2, "id_parentesco": parentesco2,
    }).status_code == 200
    assert int(_id("SELECT IdParentesco FROM dbo.ASIGNACION_CONTACTO_EMERGENCIA WHERE IdAsignacion=?", (contacto_id,))) == int(parentesco2)
    repetido = cliente.post("/api/contactos", json={
        "id_paciente": paciente_id, "id_familiar": familiar2, "id_parentesco": parentesco,
    })
    assert repetido.status_code == 409


def test_rf3_cama_ocupada_asignacion_controlada_y_cierre(cliente, catalogos):
    familiar = catalogos["familiares"][0]["id_familiar"]
    medico = catalogos["medicos"][0]["id_medico_externo"]
    ocupada = _id("SELECT TOP 1 id_cama FROM dbo.Hospitalizacion WHERE estado=N'Activa'")
    assert ocupada is not None
    dpi = PREFIJO + "-PH1"
    assert cliente.post("/api/pacientes", json={
        "dpi": dpi, "nombre": "Hosp", "apellido": "Uno",
        "fecha_nacimiento": "1980-04-04", "genero": "Femenino",
        "direccion": "Dir", "telefono": "55550202",
        "id_familiar": familiar, "id_medico_externo": medico,
    }).status_code == 200
    paciente = _id("SELECT id_paciente FROM dbo.Paciente WHERE dpi=?", (dpi,))
    rechazo = cliente.post("/api/hospitalizaciones", json={
        "id_paciente": paciente, "id_cama": ocupada, "motivo_ingreso": PREFIJO + " no debe ocupar cama real",
    })
    assert rechazo.status_code == 409
    assert _id("SELECT COUNT(*) FROM dbo.Hospitalizacion WHERE motivo_ingreso LIKE ?", (PREFIJO + "%",)) == 0

    sala = _id("SELECT TOP 1 id_sala FROM dbo.Sala")
    with conexion() as cn:
        cn.cursor().execute(
            "INSERT INTO dbo.Cama (numero_cama, id_sala) VALUES (?, ?)",
            (PREFIJO + "-C1", sala),
        )
    cama = _id("SELECT id_cama FROM dbo.Cama WHERE numero_cama=?", (PREFIJO + "-C1",))
    libres = cliente.get("/api/camas/disponibles").get_json()
    assert any(item["id_cama"] == cama for item in libres)

    alta = cliente.post("/api/hospitalizaciones", json={
        "id_paciente": paciente, "id_cama": cama, "motivo_ingreso": PREFIJO + " ingreso controlado",
    })
    assert alta.status_code == 200
    cuerpo = alta.get_json()
    assert cuerpo["estado"] == "Activa" and cuerpo["ingreso"]
    ingreso_id = cuerpo["id_hospitalizacion"]

    dpi2 = PREFIJO + "-PH2"
    assert cliente.post("/api/pacientes", json={
        "dpi": dpi2, "nombre": "Hosp", "apellido": "Dos",
        "fecha_nacimiento": "1981-05-05", "genero": "Masculino",
        "direccion": "Dir", "telefono": "55550303",
        "id_familiar": familiar, "id_medico_externo": medico,
    }).status_code == 200
    paciente2 = _id("SELECT id_paciente FROM dbo.Paciente WHERE dpi=?", (dpi2,))
    segunda = cliente.post("/api/hospitalizaciones", json={
        "id_paciente": paciente2, "id_cama": cama, "motivo_ingreso": PREFIJO + " segunda",
    })
    assert segunda.status_code == 409
    assert _id(
        "SELECT COUNT(*) FROM dbo.Hospitalizacion WHERE id_cama=? AND estado=N'Activa'",
        (cama,),
    ) == 1

    assert cliente.post(f"/api/hospitalizaciones/{ingreso_id}/finalizar").status_code == 200
    assert cliente.post(f"/api/hospitalizaciones/{ingreso_id}/finalizar").status_code == 409
    with conexion() as cn:
        cur = cn.cursor()
        cur.execute(
            "SELECT estado, fecha_hora_salida_real FROM dbo.Hospitalizacion WHERE id_hospitalizacion=?",
            (ingreso_id,),
        )
        estado, salida = cur.fetchone()
    assert estado == "Finalizada" and salida is not None
    libres = cliente.get("/api/camas/disponibles").get_json()
    assert any(item["id_cama"] == cama for item in libres)
    historial = cliente.get("/api/hospitalizaciones?estado=Finalizada").get_json()
    assert any(item["id_hospitalizacion"] == ingreso_id and item["salida"] for item in historial)


def test_rf3_dos_asignaciones_simultaneas(catalogos):
    familiar = catalogos["familiares"][0]["id_familiar"]
    medico = catalogos["medicos"][0]["id_medico_externo"]
    hospital.app.config["TESTING"] = True
    with hospital.app.test_client() as cliente:
        cliente.post("/api/login", json={"usuario": hospital.ADMIN_USER, "clave": hospital.ADMIN_PASS})
        for indice, dpi in enumerate((PREFIJO + "-PS1", PREFIJO + "-PS2"), start=1):
            assert cliente.post("/api/pacientes", json={
                "dpi": dpi, "nombre": "Sim", "apellido": str(indice),
                "fecha_nacimiento": "1970-01-01", "genero": "Otro",
                "direccion": "Dir", "telefono": f"5555040{indice}",
                "id_familiar": familiar, "id_medico_externo": medico,
            }).status_code == 200
    sala = _id("SELECT TOP 1 id_sala FROM dbo.Sala")
    with conexion() as cn:
        cn.cursor().execute("INSERT INTO dbo.Cama (numero_cama, id_sala) VALUES (?, ?)", (PREFIJO + "-C2", sala))
    cama = _id("SELECT id_cama FROM dbo.Cama WHERE numero_cama=?", (PREFIJO + "-C2",))
    pacientes = [
        _id("SELECT id_paciente FROM dbo.Paciente WHERE dpi=?", (PREFIJO + "-PS1",)),
        _id("SELECT id_paciente FROM dbo.Paciente WHERE dpi=?", (PREFIJO + "-PS2",)),
    ]
    resultados = []

    def intentar(id_paciente):
        try:
            with hospital.db() as cn:
                hospital.asignar_hospitalizacion(cn, id_paciente, cama, PREFIJO + " simultanea")
            resultados.append("ok")
        except (ValueError, pyodbc.Error):
            resultados.append("rechazo")

    hilos = [Thread(target=intentar, args=(paciente,)) for paciente in pacientes]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join()
    assert sorted(resultados) == ["ok", "rechazo"]
    assert _id("SELECT COUNT(*) FROM dbo.Hospitalizacion WHERE id_cama=? AND estado=N'Activa'", (cama,)) == 1


def test_rf4_edicion_y_movimientos_actualizan_stock(cliente, catalogos):
    proveedor = catalogos["proveedores"][0]["id_proveedor"]
    tipos = {item["NombreTipoMovimiento"]: item["IdTipoMovimiento"] for item in catalogos["tipos_movimiento"]}
    codigo = PREFIJO + "-I01"
    assert cliente.post("/api/insumos", json={
        "codigo_insumo": codigo, "nombre_insumo": "Gasas prueba", "tipo_insumo": "Curacion",
        "stock_existencia": "10", "stock_maximo": "20", "costo_unitario": "4.50",
        "id_proveedor": proveedor,
    }).status_code == 200
    insumo_id = _id("SELECT id_insumo FROM dbo.Insumo WHERE codigo_insumo=?", (codigo,))
    assert cliente.put(f"/api/insumos/{insumo_id}", json={
        "codigo_insumo": codigo, "nombre_insumo": "Gasas editadas", "tipo_insumo": "Curacion",
        "stock_existencia": "10", "stock_maximo": "30", "costo_unitario": "5",
        "id_proveedor": proveedor,
    }).status_code == 200
    assert _id("SELECT nombre_insumo FROM dbo.Insumo WHERE id_insumo=?", (insumo_id,)) == "Gasas editadas"

    def mover(tipo, cantidad, clave=None):
        return cliente.post("/api/movimientos", json={
            "id_insumo": insumo_id, "id_tipo_movimiento": tipos[tipo],
            "cantidad": cantidad, "costo_unitario": "5",
            "observacion": PREFIJO, "clave_idempotencia": clave,
        })

    assert mover("Entrada", "5").status_code == 200
    assert float(_id("SELECT stock_existencia FROM dbo.Insumo WHERE id_insumo=?", (insumo_id,))) == 15
    assert mover("Salida", "2").status_code == 200
    assert float(_id("SELECT stock_existencia FROM dbo.Insumo WHERE id_insumo=?", (insumo_id,))) == 13
    assert mover("Devolucion", "1").status_code == 200
    assert float(_id("SELECT stock_existencia FROM dbo.Insumo WHERE id_insumo=?", (insumo_id,))) == 14
    assert mover("Ajuste", "8").status_code == 200
    assert float(_id("SELECT stock_existencia FROM dbo.Insumo WHERE id_insumo=?", (insumo_id,))) == 8
    assert mover("Salida", "0").status_code == 400
    assert "mayor que cero" in mover("Salida", "0").get_json()["error"]
    assert mover("Salida", "-1").status_code == 400
    excesiva = mover("Salida", "50")
    assert excesiva.status_code == 400
    assert "existencia" in excesiva.get_json()["error"]
    assert float(_id("SELECT stock_existencia FROM dbo.Insumo WHERE id_insumo=?", (insumo_id,))) == 8
    tope = mover("Entrada", "100")
    assert tope.status_code == 400
    assert mover("Entrada", "1", "clave-qafin-1").status_code == 200
    repetido = mover("Entrada", "1", "clave-qafin-1")
    assert repetido.status_code == 200 and repetido.get_json()["duplicado"] is True
    assert float(_id("SELECT stock_existencia FROM dbo.Insumo WHERE id_insumo=?", (insumo_id,))) == 9
    assert cliente.post("/api/insumos", json={
        "codigo_insumo": PREFIJO + "-I02", "nombre_insumo": "Sin proveedor", "tipo_insumo": "X",
        "stock_existencia": "1", "stock_maximo": "5", "costo_unitario": "1", "id_proveedor": 999999,
    }).status_code == 409
    assert cliente.delete(f"/api/movimientos/1").status_code == 405


def test_rf4_salidas_simultaneas_no_dejan_stock_negativo(cliente, catalogos):
    proveedor = catalogos["proveedores"][0]["id_proveedor"]
    salida = next(item["IdTipoMovimiento"] for item in catalogos["tipos_movimiento"] if item["NombreTipoMovimiento"] == "Salida")
    codigo = PREFIJO + "-I03"
    assert cliente.post("/api/insumos", json={
        "codigo_insumo": codigo, "nombre_insumo": "Carrera", "tipo_insumo": "QA",
        "stock_existencia": "10", "stock_maximo": "10", "costo_unitario": "1",
        "id_proveedor": proveedor,
    }).status_code == 200
    insumo_id = _id("SELECT id_insumo FROM dbo.Insumo WHERE codigo_insumo=?", (codigo,))
    resultados = []

    def intentar():
        try:
            with hospital.db() as cn:
                hospital.registrar_movimiento(cn, insumo_id, salida, 10, 1, PREFIJO + " simultanea")
            resultados.append("ok")
        except ValueError:
            resultados.append("rechazo")

    hilos = [Thread(target=intentar), Thread(target=intentar)]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join()
    assert sorted(resultados) == ["ok", "rechazo"]
    assert float(_id("SELECT stock_existencia FROM dbo.Insumo WHERE id_insumo=?", (insumo_id,))) == 0


def test_rechazos_y_borrado_no_alteran_registros_ajenos(cliente, catalogos):
    """Un alta inválida o un borrado de prueba no cambia filas que no son QAFIN."""
    turno = catalogos["turnos"][0]["id_turno"]
    familiar = catalogos["familiares"][0]["id_familiar"]
    medico = catalogos["medicos"][0]["id_medico_externo"]
    parentesco = catalogos["parentescos"][0]["IdParentesco"]
    ancla = _id("SELECT TOP 1 id_paciente FROM dbo.Paciente WHERE dpi NOT LIKE 'QAFIN%'")
    pacientes_reales = _id("SELECT COUNT(*) FROM dbo.Paciente WHERE dpi NOT LIKE 'QAFIN%'")
    empleados_reales = _id("SELECT COUNT(*) FROM dbo.Empleado WHERE nss NOT LIKE 'QAFIN%'")
    stock_real = _id(
        "SELECT SUM(stock_existencia) FROM dbo.Insumo WHERE codigo_insumo NOT LIKE 'QAFIN%'"
    )

    nss = PREFIJO + "-AISL"
    alta = {
        "nss": nss, "nombre": "Aislado", "apellido": "Uno", "rol": "Enfermeria",
        "id_turno": turno, "estado_activo": True,
    }
    assert cliente.post("/api/empleados", json=alta).status_code == 200
    duplicado = cliente.post("/api/empleados", json=alta)
    assert duplicado.status_code == 409 and "NSS" in duplicado.get_json()["error"]
    assert "ODBC" not in duplicado.get_json()["error"]
    turno_falso = cliente.post("/api/empleados", json=dict(alta, nss=PREFIJO + "-AISL2", id_turno=999999))
    assert turno_falso.status_code == 409
    assert _id("SELECT COUNT(*) FROM dbo.Empleado WHERE nss=?", (nss,)) == 1

    cuerpo = {
        "dpi": PREFIJO + "-AISL1", "nombre": "Aislado", "apellido": "Paciente",
        "fecha_nacimiento": "1990-01-01", "genero": "Femenino",
        "direccion": "Dir", "telefono": "55551111",
        "id_familiar": familiar, "id_medico_externo": medico,
    }
    assert cliente.post("/api/pacientes", json=cuerpo).status_code == 200
    assert cliente.post("/api/pacientes", json=dict(cuerpo, dpi=PREFIJO + "-AISL2", telefono="55552222")).status_code == 200
    vacío = _id("SELECT id_paciente FROM dbo.Paciente WHERE dpi=?", (PREFIJO + "-AISL1",))
    con_historia = _id("SELECT id_paciente FROM dbo.Paciente WHERE dpi=?", (PREFIJO + "-AISL2",))
    assert cliente.post("/api/admisiones", json={"id_paciente": 999999, "fecha": "2026-11-02T09:00:00"}).status_code == 409
    assert cliente.post("/api/admisiones", json={
        "id_paciente": con_historia, "id_medico_externo": medico, "fecha": "2026-11-02T09:00:00",
    }).status_code == 200
    assert cliente.post("/api/contactos", json={
        "id_paciente": con_historia, "id_familiar": familiar, "id_parentesco": 999999,
    }).status_code == 409
    assert cliente.delete(f"/api/pacientes/{con_historia}").status_code == 409
    assert cliente.delete(f"/api/pacientes/{vacío}").status_code == 200
    assert _id("SELECT id_paciente FROM dbo.Paciente WHERE dpi=?", (PREFIJO + "-AISL2",)) == con_historia
    assert _id("SELECT COUNT(*) FROM dbo.ADMISION WHERE IdPaciente=?", (con_historia,)) == 1
    assert _id("SELECT id_paciente FROM dbo.Paciente WHERE id_paciente=?", (ancla,)) == ancla
    assert _id("SELECT COUNT(*) FROM dbo.Paciente WHERE dpi NOT LIKE 'QAFIN%'") == pacientes_reales
    assert _id("SELECT COUNT(*) FROM dbo.Empleado WHERE nss NOT LIKE 'QAFIN%'") == empleados_reales
    assert _id("SELECT SUM(stock_existencia) FROM dbo.Insumo WHERE codigo_insumo NOT LIKE 'QAFIN%'") == stock_real
