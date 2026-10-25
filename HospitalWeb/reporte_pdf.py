"""Genera el PDF de un reporte del panel (tabla + resumen de movimientos)."""

import os

from fpdf import FPDF
from fpdf.fonts import FontFace

_FONTS = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
_FONT_REGULAR = os.path.join(_FONTS, "arial.ttf")
_FONT_BOLD = os.path.join(_FONTS, "arialbd.ttf")

_TEAL = (15, 118, 110)
_TEXTO = (30, 41, 59)
_MUTED = (100, 116, 139)
_HEADER_BG = (241, 245, 249)


class ReportePDF(FPDF):
    def __init__(self, titulo):
        super().__init__(orientation="L", unit="mm", format="A4")
        self._titulo = titulo
        self.add_font("Arial", "", _FONT_REGULAR)
        self.add_font("Arial", "B", _FONT_BOLD)
        self.set_auto_page_break(auto=True, margin=12)
        self.set_margins(8, 10, 8)
        self.alias_nb_pages()

    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("Arial", "B", 9)
        self.set_text_color(*_TEAL)
        self.cell(0, 6, "Hospital W 2.0 - " + self._titulo, new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(*_TEXTO)
        self.ln(1)

    def footer(self):
        self.set_y(-8)
        self.set_font("Arial", size=8)
        self.set_text_color(*_MUTED)
        self.cell(0, 5, f"Pagina {self.page_no()}/{{nb}}", align="R")


def _seccion(pdf, titulo):
    pdf.ln(3)
    pdf.set_font("Arial", "B", 11)
    pdf.set_text_color(*_TEAL)
    pdf.cell(0, 6, titulo, new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(*_TEXTO)


def _nota(pdf, texto):
    pdf.set_font("Arial", size=9)
    pdf.set_text_color(*_MUTED)
    pdf.multi_cell(0, 5, texto, new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(*_TEXTO)


def _tabla(pdf, encabezados, filas, tamano=7):
    if not filas:
        _nota(pdf, "Sin registros.")
        return
    pdf.set_font("Arial", size=tamano)
    pdf.set_text_color(*_TEXTO)
    estilo = FontFace(emphasis="BOLD", fill_color=_HEADER_BG, color=_MUTED, size_pt=tamano)
    with pdf.table(
        headings_style=estilo,
        text_align="LEFT",
        line_height=4,
        padding=1,
        repeat_headings=1,
        first_row_as_headings=True,
    ) as tabla:
        cabecera = tabla.row()
        for titulo in encabezados:
            cabecera.cell(titulo)
        for fila in filas:
            linea = tabla.row()
            for valor in fila:
                linea.cell(valor)


def construir_pdf(reporte):
    """Devuelve el PDF del reporte como bytes."""
    pdf = ReportePDF(reporte["titulo"])
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.set_text_color(*_TEAL)
    pdf.cell(0, 8, "Hospital W 2.0  ·  " + reporte["titulo"], new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Arial", size=9)
    pdf.set_text_color(*_MUTED)
    pdf.cell(
        0,
        5,
        f"Generado {reporte['generado']} por {reporte.get('usuario') or 'admin'}. "
        f"{len(reporte['filas'])} registro(s) en la tabla.",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.ln(1)
    pdf.set_font("Arial", size=10)
    pdf.set_text_color(*_TEXTO)
    resumen = "    |    ".join(f"{item['etiqueta']}: {item['valor']}" for item in reporte["resumen"])
    pdf.multi_cell(0, 6, resumen, new_x="LMARGIN", new_y="NEXT")

    _seccion(pdf, "Operaciones recientes del panel")
    panel = reporte.get("panel") or []
    if panel:
        _tabla(
            pdf,
            ["Fecha", "Operacion", "Detalle"],
            [[m["fecha"], m["accion"], m["detalle"]] for m in panel],
            tamano=8,
        )
    else:
        _nota(pdf, "Aun no hay ingresos ni eliminaciones registrados desde este panel.")

    _seccion(pdf, reporte.get("actividad_titulo") or "Ultimos movimientos")
    actividad = reporte.get("actividad") or []
    etiqueta = reporte.get("actividad_fecha") or "Fecha"
    if actividad:
        _tabla(
            pdf,
            [etiqueta, "Tipo", "Referencia", "Detalle"],
            [[m["fecha"], m["tipo"], m["sujeto"], m["detalle"]] for m in actividad],
            tamano=8,
        )
    else:
        _nota(pdf, "No hay movimientos recientes en esta tabla.")

    _seccion(pdf, "Tabla completa")
    _tabla(pdf, reporte["encabezados"], reporte["filas"], tamano=7)
    return bytes(pdf.output())
