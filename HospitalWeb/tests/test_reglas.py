from decimal import Decimal

import app as hospital


def test_nuevo_stock_entrada_salida_ajuste_y_devolucion():
    assert hospital.nuevo_stock(10, 100, "Entrada", 5) == Decimal(15)
    assert hospital.nuevo_stock(10, 100, "Salida", 4) == Decimal(6)
    assert hospital.nuevo_stock(10, 100, "Devolucion", 3) == Decimal(13)
    assert hospital.nuevo_stock(10, 100, "Ajuste", 7) == Decimal(7)


def test_nuevo_stock_rechaza_salida_excesiva_y_maximo():
    with __import__("pytest").raises(ValueError, match="supera la existencia"):
        hospital.nuevo_stock(10, 100, "Salida", 11)
    with __import__("pytest").raises(ValueError, match="stock máximo"):
        hospital.nuevo_stock(10, 12, "Entrada", 5)


def test_cantidad_cero_y_negativa_tienen_mensajes_distintos():
    with __import__("pytest").raises(ValueError, match="mayor que cero"):
        hospital.decimal_positivo(0, "La cantidad", permitir_cero=False)
    with __import__("pytest").raises(ValueError, match="negativa"):
        hospital.decimal_positivo(-1, "La cantidad", permitir_cero=False)


def test_traduccion_no_expone_el_texto_del_controlador():
    class Error(Exception):
        pass

    error = hospital.pyodbc.IntegrityError(
        "23000",
        "[Microsoft][ODBC Driver 18 for SQL Server][SQL Server]Violation of UNIQUE KEY constraint 'UQ_Empleado_NSS'.",
    )
    texto = hospital.traducir_error(error)
    assert texto == "Ese NSS ya está registrado."
    assert "ODBC" not in texto
    assert "Microsoft" not in texto
