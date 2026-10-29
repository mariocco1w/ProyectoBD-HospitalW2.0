"use strict";

/* ==========================================================================
   Hospital W 2.0 - Lógica del panel
   ========================================================================== */

/* ------------------------------- Utilidades ------------------------------ */
const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (ch) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[ch]));
}

const nf = new Intl.NumberFormat("es-GT");
const cf = new Intl.NumberFormat("es-GT", {
  style: "currency", currency: "GTQ", minimumFractionDigits: 2,
});

function toDate(value) {
  if (!value) return null;
  const s = String(value);
  if (/^\d{4}-\d{2}-\d{2}$/.test(s)) {
    const [y, m, d] = s.split("-").map(Number);
    return new Date(y, m - 1, d);
  }
  const d = new Date(s.replace(" ", "T"));
  return Number.isNaN(d.getTime()) ? null : d;
}

function fmtDate(value) {
  const d = toDate(value);
  return d ? d.toLocaleDateString("es-GT", { day: "2-digit", month: "short", year: "numeric" }) : "—";
}

function fmtDateTime(value) {
  const d = toDate(value);
  if (!d) return "—";
  return d.toLocaleString("es-GT", {
    day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit",
  });
}

function edad(value) {
  const d = toDate(value);
  if (!d) return "—";
  const hoy = new Date();
  let a = hoy.getFullYear() - d.getFullYear();
  const m = hoy.getMonth() - d.getMonth();
  if (m < 0 || (m === 0 && hoy.getDate() < d.getDate())) a -= 1;
  return a;
}

function iniciales(texto) {
  const partes = String(texto || "").trim().split(/\s+/);
  const ini = (partes[0]?.[0] || "") + (partes[1]?.[0] || "");
  return ini.toUpperCase() || "?";
}

function badge(texto, tono) {
  return `<span class="badge ${tono || "gray"}">${escapeHtml(texto)}</span>`;
}

function personCell(nombre, sub) {
  return `<div class="cell-person"><span class="ini">${escapeHtml(iniciales(nombre))}</span>` +
    `<div class="meta"><b>${escapeHtml(nombre)}</b><small>${escapeHtml(sub || "")}</small></div></div>`;
}

function generoTono(g) {
  if (g === "Femenino") return "rose";
  if (g === "Masculino") return "blue";
  return "violet";
}

function rolTono(rol) {
  const k = String(rol || "").toLowerCase();
  if (k.includes("medic")) return "blue";
  if (k.includes("enferm")) return "teal";
  if (k.includes("admin")) return "amber";
  if (k.includes("tecnic") || k.includes("técnic")) return "violet";
  return "gray";
}

function movTono(tipo) {
  const k = String(tipo || "").toLowerCase();
  if (k.includes("entrada")) return "blue";
  if (k.includes("salida")) return "rose";
  if (k.includes("ajuste")) return "amber";
  if (k.includes("devol")) return "violet";
  return "gray";
}

function stockCell(f) {
  const max = Number(f.stock_maximo) || 0;
  const pct = max > 0 ? Math.min(100, (Number(f.stock_existencia) / max) * 100) : 0;
  const clase = pct <= 25 ? "low" : pct <= 55 ? "mid" : "ok";
  return `<div class="stock">
      <div class="stock-top"><b>${nf.format(f.stock_existencia)}</b><span>de ${nf.format(max)}</span></div>
      <div class="stock-bar"><span class="${clase}" style="width:${pct}%"></span></div>
    </div>`;
}

function setBusy(btn, busy, texto) {
  if (!btn) return;
  if (busy) {
    btn.dataset.html = btn.innerHTML;
    btn.disabled = true;
    btn.textContent = texto || "Guardando…";
  } else {
    btn.disabled = false;
    if (btn.dataset.html) btn.innerHTML = btn.dataset.html;
  }
}

function formData(form) {
  const data = {};
  new FormData(form).forEach((v, k) => { data[k] = v; });
  form.querySelectorAll('input[type="checkbox"]').forEach((c) => { data[c.name] = c.checked; });
  return data;
}

/* --------------------------------- Iconos -------------------------------- */
const SVG = (paths, size = 19) =>
  `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" ` +
  `stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${paths}</svg>`;

const ICONS = {
  users: SVG('<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>'),
  staff: SVG('<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>'),
  box: SVG('<path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><path d="M3.3 7 12 12l8.7-5M12 22V12"/>'),
  calendar: SVG('<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/>'),
  door: SVG('<path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/><path d="m10 17 5-5-5-5M15 12H3"/>'),
  swap: SVG('<path d="M3 7h13l-3-3M21 17H8l3 3"/><path d="M3 7l3 3M21 17l-3-3"/>'),
  heart: SVG('<path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1-1.1a5.5 5.5 0 0 0-7.8 7.8L12 21l8.8-8.6a5.5 5.5 0 0 0 0-7.8z"/>'),
  bed: SVG('<path d="M2 4v16M2 8h18a2 2 0 0 1 2 2v10M2 17h20M6 8v9"/>'),
  truck: SVG('<rect x="1" y="3" width="15" height="13" rx="1"/><path d="M16 8h4l3 3v5h-7z"/><circle cx="5.5" cy="18.5" r="2.5"/><circle cx="18.5" cy="18.5" r="2.5"/>'),
  check: SVG('<path d="m20 6-11 11-5-5"/>'),
  alert: SVG('<path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><path d="M12 9v4M12 17h.01"/>'),
  info: SVG('<circle cx="12" cy="12" r="9"/><path d="M12 8h.01M11 12h1v4h1"/>'),
  moon: SVG('<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>'),
  sun: SVG('<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>'),
};

/* -------------------------------- Estado --------------------------------- */
const ENDPOINTS = {
  pacientes: "/api/pacientes",
  empleados: "/api/empleados",
  insumos: "/api/insumos",
  admisiones: "/api/admisiones",
  contactos: "/api/contactos",
  movimientos: "/api/movimientos",
  telemetria: "/api/telemetria",
};

const state = {
  view: "dashboard",
  loaded: false,
  catalogos: {},
  data: {
    dashboard: null,
    pacientes: [],
    empleados: [],
    insumos: [],
    admisiones: [],
    contactos: [],
    movimientos: [],
    telemetria: [],
  },
  filtros: {},
  sort: {
    pacientes: { key: "paciente", dir: 1 },
    empleados: { key: "empleado", dir: 1 },
    insumos: { key: "insumo", dir: 1 },
    admisiones: { key: "fecha", dir: -1 },
    contactos: { key: "paciente", dir: 1 },
    movimientos: { key: "fecha", dir: -1 },
    telemetria: { key: "marca", dir: -1 },
  },
  page: {
    pacientes: 1, empleados: 1, insumos: 1, admisiones: 1,
    contactos: 1, movimientos: 1, telemetria: 1,
  },
  confirmResolve: null,
};

/* --------------------------- Configuración tablas ------------------------ */
const TABLES = {
  pacientes: {
    singular: "paciente",
    idKey: "id_paciente",
    pageSize: 8,
    recordName: (f) => `${f.nombre} ${f.apellido}`,
    detailSub: (f) => `DPI ${f.dpi}`,
    search: (f) => [f.nombre, f.apellido, f.dpi, f.telefono, f.genero, f.familiar],
    columns: [
      { key: "paciente", label: "Paciente", sort: (f) => `${f.nombre} ${f.apellido}`.toLowerCase(),
        render: (f) => personCell(`${f.nombre} ${f.apellido}`, `DPI ${f.dpi}`) },
      { key: "edad", label: "Edad", sort: (f) => edad(f.fecha_nacimiento),
        render: (f) => `<span class="pill">${edad(f.fecha_nacimiento)} años</span>` },
      { key: "genero", label: "Género", sort: (f) => f.genero,
        render: (f) => badge(f.genero, generoTono(f.genero)) },
      { key: "familiar", label: "Familiar responsable", sort: (f) => f.familiar,
        render: (f) => `<span class="truncate" title="${escapeHtml(f.familiar)}">${escapeHtml(f.familiar)}</span>` },
      { key: "citas", label: "Citas", align: "center", sort: (f) => Number(f.citas) || 0,
        render: (f) => badge(f.citas, f.citas ? "teal" : "gray") },
      { key: "hosp", label: "Hosp.", align: "center", sort: (f) => Number(f.hospitalizaciones) || 0,
        render: (f) => badge(f.hospitalizaciones, f.hospitalizaciones ? "blue" : "gray") },
    ],
    detail: (f) => [
      { title: "Datos personales", rows: [
        ["DPI", escapeHtml(f.dpi)],
        ["Nombre completo", escapeHtml(`${f.nombre} ${f.apellido}`)],
        ["Fecha de nacimiento", `${fmtDate(f.fecha_nacimiento)} <span class="pill">${edad(f.fecha_nacimiento)} años</span>`],
        ["Género", badge(f.genero, generoTono(f.genero))],
        ["Adulto mayor", f.es_adulto_mayor ? "Sí" : "No"],
        ["Dirección", escapeHtml(f.direccion)],
        ["Teléfono", escapeHtml(f.telefono)],
      ]},
      { title: "Contacto y referencias", rows: [
        ["Familiar responsable", escapeHtml(f.familiar)],
        ["Médico externo", escapeHtml(f.medico_externo)],
      ]},
      { title: "Actividad", rows: [
        ["Citas", nf.format(f.citas)],
        ["Hospitalizaciones", nf.format(f.hospitalizaciones)],
        ["Admisiones", nf.format(f.admisiones)],
        ["Contactos de emergencia", nf.format(f.contactos)],
        ["Registros de telemetría", nf.format(f.telemetria)],
      ]},
    ],
    cascade: (f) => {
      const partes = [];
      if (f.citas) partes.push(`${f.citas} cita(s)`);
      if (f.hospitalizaciones) partes.push(`${f.hospitalizaciones} hospitalización(es)`);
      if (f.admisiones) partes.push(`${f.admisiones} admisión(es)`);
      if (f.contactos) partes.push(`${f.contactos} contacto(s)`);
      if (f.telemetria) partes.push(`${f.telemetria} registro(s) de telemetría`);
      return partes.length ? `También se eliminarán: ${partes.join(", ")}.` : "";
    },
  },

  empleados: {
    singular: "empleado",
    idKey: "id_empleado",
    pageSize: 8,
    recordName: (f) => `${f.nombre} ${f.apellido}`,
    detailSub: (f) => `NSS ${f.nss}`,
    search: (f) => [f.nombre, f.apellido, f.nss, f.rol, f.nombre_turno, f.nombre_especialidad],
    columns: [
      { key: "empleado", label: "Empleado", sort: (f) => `${f.nombre} ${f.apellido}`.toLowerCase(),
        render: (f) => personCell(`${f.nombre} ${f.apellido}`, `NSS ${f.nss}`) },
      { key: "rol", label: "Rol", sort: (f) => f.rol,
        render: (f) => badge(f.rol, rolTono(f.rol)) },
      { key: "turno", label: "Turno", sort: (f) => f.nombre_turno,
        render: (f) => `<span class="truncate" title="${escapeHtml(f.nombre_turno)}">${escapeHtml(f.nombre_turno)}</span>` },
      { key: "especialidad", label: "Especialidad", sort: (f) => f.nombre_especialidad,
        render: (f) => `<span class="truncate" title="${escapeHtml(f.nombre_especialidad)}">${escapeHtml(f.nombre_especialidad)}</span>` },
      { key: "estado", label: "Estado", align: "center", sort: (f) => Number(f.estado_activo) || 0,
        render: (f) => (f.estado_activo ? badge("Activo", "green") : badge("Inactivo", "gray")) },
      { key: "citas", label: "Citas", align: "center", sort: (f) => Number(f.citas) || 0,
        render: (f) => badge(f.citas, "teal") },
    ],
    detail: (f) => [
      { title: "Datos del empleado", rows: [
        ["NSS", escapeHtml(f.nss)],
        ["Nombre completo", escapeHtml(`${f.nombre} ${f.apellido}`)],
        ["Rol", badge(f.rol, rolTono(f.rol))],
        ["Estado", f.estado_activo ? badge("Activo", "green") : badge("Inactivo", "gray")],
      ]},
      { title: "Asignación", rows: [
        ["Turno", escapeHtml(f.nombre_turno)],
        ["Especialidad", escapeHtml(f.nombre_especialidad)],
      ]},
      { title: "Actividad", rows: [
        ["Citas", nf.format(f.citas)],
        ["Asignaciones a sala", nf.format(f.asignaciones)],
      ]},
    ],
    cascade: (f) => {
      const partes = [];
      if (f.citas) partes.push(`${f.citas} cita(s)`);
      if (f.asignaciones) partes.push(`${f.asignaciones} asignación(es) a sala`);
      return partes.length ? `También se eliminarán: ${partes.join(", ")}.` : "";
    },
  },

  insumos: {
    singular: "insumo",
    idKey: "id_insumo",
    pageSize: 8,
    recordName: (f) => `${f.codigo_insumo} — ${f.nombre_insumo}`,
    detailSub: (f) => f.tipo_insumo,
    search: (f) => [f.codigo_insumo, f.nombre_insumo, f.tipo_insumo, f.proveedor],
    columns: [
      { key: "insumo", label: "Insumo", sort: (f) => f.nombre_insumo.toLowerCase(),
        render: (f) => personCell(f.nombre_insumo, f.codigo_insumo) },
      { key: "tipo", label: "Tipo", sort: (f) => f.tipo_insumo,
        render: (f) => badge(f.tipo_insumo, "gray") },
      { key: "stock", label: "Stock", sort: (f) => Number(f.stock_existencia) || 0,
        render: (f) => stockCell(f) },
      { key: "costo", label: "Costo unitario", align: "right", sort: (f) => Number(f.costo_unitario) || 0,
        render: (f) => cf.format(f.costo_unitario) },
      { key: "proveedor", label: "Proveedor", sort: (f) => f.proveedor,
        render: (f) => `<span class="truncate" title="${escapeHtml(f.proveedor)}">${escapeHtml(f.proveedor)}</span>` },
      { key: "mov", label: "Mov.", align: "center", sort: (f) => Number(f.movimientos) || 0,
        render: (f) => badge(f.movimientos, "violet") },
    ],
    detail: (f) => [
      { title: "Datos del insumo", rows: [
        ["Código", escapeHtml(f.codigo_insumo)],
        ["Nombre", escapeHtml(f.nombre_insumo)],
        ["Tipo", badge(f.tipo_insumo, "gray")],
        ["Proveedor", escapeHtml(f.proveedor)],
      ]},
      { title: "Inventario", rows: [
        ["Stock actual", nf.format(f.stock_existencia)],
        ["Stock máximo", nf.format(f.stock_maximo)],
        ["Costo unitario", cf.format(f.costo_unitario)],
        ["Valor en inventario", cf.format(Number(f.stock_existencia) * Number(f.costo_unitario))],
        ["Movimientos registrados", nf.format(f.movimientos)],
      ]},
    ],
    cascade: (f) => (f.movimientos
      ? `También se eliminarán ${f.movimientos} movimiento(s) de inventario asociados.`
      : ""),
  },

  admisiones: {
    singular: "admisión",
    idKey: "IdAdmision",
    pageSize: 8,
    recordName: (f) => f.paciente,
    detailSub: (f) => `Ingreso del ${fmtDate(f.fecha)}`,
    search: (f) => [f.paciente, f.dpi, f.medico],
    columns: [
      { key: "paciente", label: "Paciente", sort: (f) => String(f.paciente).toLowerCase(),
        render: (f) => personCell(f.paciente, `DPI ${f.dpi}`) },
      { key: "medico", label: "Médico externo", sort: (f) => f.medico,
        render: (f) => `<span class="truncate" title="${escapeHtml(f.medico)}">${escapeHtml(f.medico)}</span>` },
      { key: "fecha", label: "Fecha de admisión", sort: (f) => f.fecha,
        render: (f) => fmtDateTime(f.fecha) },
    ],
    detail: (f) => [
      { title: "Admisión", rows: [
        ["Paciente", escapeHtml(f.paciente)],
        ["DPI", escapeHtml(f.dpi)],
        ["Médico externo", escapeHtml(f.medico)],
        ["Fecha de admisión", fmtDateTime(f.fecha)],
        ["Número de registro", `#${f.IdAdmision}`],
      ]},
    ],
    cascade: () => "",
  },

  contactos: {
    singular: "contacto",
    idKey: "IdAsignacion",
    pageSize: 8,
    recordName: (f) => f.contacto,
    detailSub: (f) => `Contacto de ${f.paciente}`,
    search: (f) => [f.paciente, f.dpi, f.contacto, f.telefono, f.parentesco],
    columns: [
      { key: "paciente", label: "Paciente", sort: (f) => String(f.paciente).toLowerCase(),
        render: (f) => personCell(f.paciente, `DPI ${f.dpi}`) },
      { key: "contacto", label: "Contacto", sort: (f) => String(f.contacto).toLowerCase(),
        render: (f) => personCell(f.contacto, f.telefono) },
      { key: "parentesco", label: "Parentesco", sort: (f) => f.parentesco,
        render: (f) => badge(f.parentesco, "violet") },
    ],
    detail: (f) => [
      { title: "Contacto de emergencia", rows: [
        ["Paciente", escapeHtml(f.paciente)],
        ["DPI", escapeHtml(f.dpi)],
        ["Contacto", escapeHtml(f.contacto)],
        ["Teléfono", escapeHtml(f.telefono)],
        ["Parentesco", badge(f.parentesco, "violet")],
      ]},
    ],
    cascade: () => "",
  },

  movimientos: {
    singular: "movimiento",
    idKey: "IdMovimiento",
    pageSize: 8,
    recordName: (f) => `${f.tipo} · ${f.nombre_insumo}`,
    detailSub: (f) => fmtDateTime(f.fecha),
    search: (f) => [f.nombre_insumo, f.codigo_insumo, f.tipo, f.Observacion],
    columns: [
      { key: "insumo", label: "Insumo", sort: (f) => String(f.nombre_insumo).toLowerCase(),
        render: (f) => personCell(f.nombre_insumo, f.codigo_insumo) },
      { key: "tipo", label: "Tipo", sort: (f) => f.tipo,
        render: (f) => badge(f.tipo, movTono(f.tipo)) },
      { key: "cantidad", label: "Cantidad", align: "right", sort: (f) => Number(f.cantidad) || 0,
        render: (f) => nf.format(f.cantidad) },
      { key: "costo", label: "Costo unit.", align: "right", sort: (f) => Number(f.costo_unitario) || 0,
        render: (f) => cf.format(f.costo_unitario) },
      { key: "total", label: "Total", align: "right", sort: (f) => Number(f.cantidad) * Number(f.costo_unitario),
        render: (f) => `<b>${cf.format(Number(f.cantidad) * Number(f.costo_unitario))}</b>` },
      { key: "fecha", label: "Fecha", sort: (f) => f.fecha,
        render: (f) => fmtDateTime(f.fecha) },
    ],
    detail: (f) => [
      { title: "Movimiento", rows: [
        ["Insumo", escapeHtml(f.nombre_insumo)],
        ["Código", escapeHtml(f.codigo_insumo)],
        ["Tipo", badge(f.tipo, movTono(f.tipo))],
        ["Cantidad", nf.format(f.cantidad)],
        ["Costo unitario", cf.format(f.costo_unitario)],
        ["Total", cf.format(Number(f.cantidad) * Number(f.costo_unitario))],
        ["Fecha", fmtDateTime(f.fecha)],
        ["Observación", escapeHtml(f.Observacion || "—")],
      ]},
    ],
    cascade: () => "",
  },

  telemetria: {
    singular: "registro",
    idKey: "IdRegistro",
    pageSize: 8,
    deletable: false,
    recordName: (f) => f.paciente,
    detailSub: (f) => `Registro #${f.IdRegistro}`,
    search: (f) => [f.paciente, f.dpi],
    columns: [
      { key: "paciente", label: "Paciente", sort: (f) => String(f.paciente).toLowerCase(),
        render: (f) => personCell(f.paciente, `DPI ${f.dpi}`) },
      { key: "marca", label: "Fecha y hora", sort: (f) => f.marca,
        render: (f) => fmtDateTime(f.marca) },
      { key: "fc", label: "Frec. cardíaca", align: "center", sort: (f) => Number(f.FrecuenciaCardiaca) || 0,
        render: (f) => (f.FrecuenciaCardiaca != null ? `<span class="pill">${f.FrecuenciaCardiaca} bpm</span>` : "—") },
      { key: "sat", label: "Saturación", align: "center", sort: (f) => Number(f.SaturacionOxigeno) || 0,
        render: (f) => (f.SaturacionOxigeno != null
          ? `<span class="pill">${Number(f.SaturacionOxigeno).toFixed(1)} %</span>` : "—") },
      { key: "alerta", label: "Alerta", align: "center", sort: (f) => Number(f.AlertaGenerada) || 0,
        render: (f) => (f.AlertaGenerada ? badge("Alerta", "rose") : badge("Normal", "green")) },
    ],
    detail: (f) => [
      { title: "Signos vitales", rows: [
        ["Paciente", escapeHtml(f.paciente)],
        ["DPI", escapeHtml(f.dpi)],
        ["Fecha y hora", fmtDateTime(f.marca)],
        ["Frecuencia cardíaca", f.FrecuenciaCardiaca != null ? `${f.FrecuenciaCardiaca} bpm` : "—"],
        ["Saturación de oxígeno", f.SaturacionOxigeno != null ? `${Number(f.SaturacionOxigeno).toFixed(1)} %` : "—"],
        ["Alerta", f.AlertaGenerada ? badge("Alerta", "rose") : badge("Normal", "green")],
      ]},
    ],
    cascade: () => "",
  },
};

/* --------------------------- Gráficas del panel -------------------------- */
const CHART_DEFS = [
  { key: "pacientes_genero", title: "Pacientes por género", desc: "Distribución del total de pacientes.", center: "Pacientes", icon: "users", tone: "teal" },
  { key: "pacientes_edad", title: "Pacientes por edad", desc: "Agrupados por rango de edad.", center: "Pacientes", icon: "heart", tone: "rose" },
  { key: "citas_estado", title: "Citas por estado", desc: "Situación actual de las citas.", center: "Citas", icon: "calendar", tone: "violet" },
  { key: "hospitalizaciones_estado", title: "Hospitalizaciones", desc: "Estado de las hospitalizaciones.", center: "Registros", icon: "bed", tone: "blue" },
  { key: "insumos_tipo", title: "Insumos por tipo", desc: "Cantidad de insumos por categoría.", center: "Insumos", icon: "box", tone: "amber" },
  { key: "insumos_proveedor", title: "Insumos por proveedor", desc: "Distribución por proveedor.", center: "Insumos", icon: "truck", tone: "green" },
  { key: "empleados_rol", title: "Empleados por rol", desc: "Composición del personal.", center: "Empleados", icon: "staff", tone: "blue" },
  { key: "movimientos_tipo", title: "Movimientos por tipo", desc: "Entradas, salidas y ajustes.", center: "Movimientos", icon: "swap", tone: "rose" },
];

const KPI_DEFS = [
  { key: "pacientes", label: "Pacientes", sub: () => "registrados", icon: "users", tone: "teal" },
  { key: "empleados", label: "Empleados", sub: (k) => `${k.empleados_activos} activos`, icon: "staff", tone: "blue" },
  { key: "insumos", label: "Insumos", sub: (k) => `${k.stock_bajo} con stock bajo`, icon: "box", tone: "amber" },
  { key: "citas", label: "Citas", sub: (k) => `${k.hosp_activas} hosp. activas`, icon: "calendar", tone: "violet" },
  { key: "admisiones", label: "Admisiones", sub: () => "ingresos registrados", icon: "door", tone: "teal" },
  { key: "movimientos", label: "Movimientos", sub: () => "de inventario", icon: "swap", tone: "rose" },
];

const PALETA = [
  "#0e7490", "#14b8a6", "#f59e0b", "#8b5cf6", "#e11d48",
  "#0ea5e9", "#84cc16", "#ec4899", "#6366f1", "#f97316",
];

const COLOR_MAP = {
  "Femenino": "#ec4899", "Masculino": "#0ea5e9", "Otro": "#8b5cf6",
  "Activa": "#10b981", "Finalizada": "#64748b", "Cancelada": "#e11d48",
  "Programada": "#0ea5e9", "Confirmada": "#14b8a6", "Completada": "#10b981",
  "No asistio": "#f59e0b", "No asistió": "#f59e0b",
  "Entrada": "#0ea5e9", "Salida": "#e11d48", "Ajuste": "#f59e0b",
  "Devolucion": "#8b5cf6", "Devolución": "#8b5cf6",
  "Medico": "#0e7490", "Médico": "#0e7490", "Enfermeria": "#14b8a6",
  "Enfermería": "#14b8a6", "Administrativo": "#f59e0b", "Tecnico": "#8b5cf6",
  "Técnico": "#8b5cf6",
  "Bajo": "#10b981", "Moderado": "#f59e0b", "Crítico": "#e11d48", "Critico": "#e11d48",
  "Con alerta SpO2": "#e11d48", "Sin alerta SpO2": "#10b981",
};

const colorFor = (label, i) => COLOR_MAP[label] || PALETA[i % PALETA.length];

/* --------------------------------- API ----------------------------------- */
async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (res.status === 401) {
    showLogin();
    throw new Error("La sesión expiró. Vuelva a iniciar sesión.");
  }
  let payload = null;
  try { payload = await res.json(); } catch (_) { /* sin cuerpo */ }
  if (!res.ok) {
    throw new Error((payload && payload.error) || `Error ${res.status} (${res.statusText}).`);
  }
  return payload;
}

/* ------------------------------- Sesión ---------------------------------- */
async function doLogin() {
  const usuario = $("#login-user").value.trim();
  const clave = $("#login-pass").value;
  if (!usuario || !clave) {
    notify("Datos incompletos", "Escriba usuario y clave para continuar.", "warn");
    return;
  }
  const btn = $("#login .btn-primary");
  setBusy(btn, true, "Ingresando…");
  try {
    await api("/api/login", { method: "POST", body: JSON.stringify({ usuario, clave }) });
    await enterApp();
  } catch (err) {
    notify("No se pudo iniciar sesión", err.message, "error", true);
  } finally {
    setBusy(btn, false);
  }
}

async function doLogout() {
  try { await api("/api/logout", { method: "POST" }); } catch (_) { /* ignorar */ }
  showLogin();
}

function showLogin() {
  $("#app").classList.add("hidden");
  $("#login").classList.remove("hidden");
  $("#login-pass").value = "";
  state.loaded = false;
}

async function enterApp() {
  $("#login").classList.add("hidden");
  $("#app").classList.remove("hidden");
  setToday();
  try {
    await cargarTodo();
    showView("dashboard");
  } catch (err) {
    notify("No se pudieron cargar los datos", err.message, "error", true);
  }
}

/* --------------------------- Carga de información ------------------------ */
async function cargarTodo() {
  const [dashboard, pacientes, empleados, insumos, admisiones, contactos, movimientos, telemetria, analisis, catalogos] =
    await Promise.all([
      api("/api/dashboard"),
      api("/api/pacientes"),
      api("/api/empleados"),
      api("/api/insumos"),
      api("/api/admisiones"),
      api("/api/contactos"),
      api("/api/movimientos"),
      api("/api/telemetria"),
      api("/api/telemetria/analisis"),
      api("/api/catalogos"),
    ]);

  state.data = { dashboard, pacientes, empleados, insumos, admisiones, contactos, movimientos, telemetria, analisis };
  state.catalogos = catalogos;
  state.loaded = true;
  llenarCatalogos();
  renderAll();
}

async function recargar(nombres = []) {
  const tareas = nombres.map((n) =>
    api(ENDPOINTS[n]).then((filas) => { state.data[n] = filas; })
  );
  tareas.push(api("/api/dashboard").then((d) => { state.data.dashboard = d; }));
  if (nombres.includes("pacientes") || nombres.includes("insumos")) {
    tareas.push(api("/api/catalogos").then((c) => { state.catalogos = c; llenarCatalogos(); }));
  }
  await Promise.all(tareas);
  renderAll();
}

async function actualizarTodo() {
  const btn = $("#btn-refresh");
  btn.disabled = true;
  try {
    await cargarTodo();
    notify("Datos actualizados", "La información se recargó desde la base de datos.", "info");
  } catch (err) {
    notify("Error al actualizar", err.message, "error", true);
  } finally {
    btn.disabled = false;
  }
}

/* ------------------------------- Navegación ------------------------------ */
const VIEWS = {
  dashboard: { title: "Resumen general", sub: "Vista general del hospital" },
  pacientes: { title: "Pacientes", sub: "Gestión de pacientes registrados" },
  admisiones: { title: "Admisiones", sub: "Registro de ingresos de pacientes" },
  contactos: { title: "Contactos de emergencia", sub: "Contactos asignados a cada paciente" },
  empleados: { title: "Empleados", sub: "Administración del personal" },
  insumos: { title: "Insumos", sub: "Control de inventario" },
  movimientos: { title: "Movimientos de inventario", sub: "Entradas, salidas y ajustes" },
  telemetria: { title: "Telemetría", sub: "Mediciones procesadas con PySpark" },
};

function showView(name) {
  if (!VIEWS[name]) return;
  state.view = name;
  $$(".view").forEach((v) => v.classList.add("hidden"));
  const view = document.getElementById(`view-${name}`);
  if (view) view.classList.remove("hidden");
  $$(".nav-item").forEach((b) => b.classList.toggle("active", b.dataset.view === name));
  $("#page-title").textContent = VIEWS[name].title;
  $("#page-sub").textContent = VIEWS[name].sub;
  if (name === "dashboard") renderDashboard();
  else renderTable(name);
  if (name === "telemetria") renderTelemetria();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

/* ------------------------------- Catálogos ------------------------------- */
function llenarCatalogos() {
  const c = state.catalogos || {};

  const fill = (id, items, opts = {}) => {
    const sel = document.getElementById(id);
    if (!sel) return;
    const actual = sel.value;
    let html = opts.placeholder ? `<option value="">${escapeHtml(opts.placeholder)}</option>` : "";
    html += (items || []).map((it) => {
      const value = opts.value ? opts.value(it) : it;
      const label = opts.label ? opts.label(it) : it;
      return `<option value="${escapeHtml(String(value))}">${escapeHtml(String(label))}</option>`;
    }).join("");
    sel.innerHTML = html;
    if (actual && Array.from(sel.options).some((o) => o.value === actual)) sel.value = actual;
  };

  fill("sel-genero", c.generos);
  fill("sel-rol", c.roles);
  fill("sel-familiar", c.familiares, { value: (f) => f.id_familiar, label: (f) => `${f.nombre_completo} — ${f.telefono}` });
  fill("sel-medico", c.medicos, { value: (m) => m.id_medico_externo, label: (m) => m.nombre_completo });
  fill("sel-turno", c.turnos, { value: (t) => t.id_turno, label: (t) => t.nombre_turno });
  fill("sel-especialidad", c.especialidades, { placeholder: "Sin especialidad", value: (e) => e.id_especialidad, label: (e) => e.nombre_especialidad });
  fill("sel-proveedor", c.proveedores, { value: (p) => p.id_proveedor, label: (p) => p.razon_social });
  fill("sel-adm-paciente", c.pacientes_opciones, { placeholder: "Seleccione un paciente", value: (p) => p.id_paciente, label: (p) => p.nombre_completo });
  fill("sel-adm-medico", c.medicos, { placeholder: "Sin médico externo", value: (m) => m.id_medico_externo, label: (m) => m.nombre_completo });
  fill("sel-con-paciente", c.pacientes_opciones, { placeholder: "Seleccione un paciente", value: (p) => p.id_paciente, label: (p) => p.nombre_completo });
  fill("sel-con-familiar", c.familiares, { placeholder: "Seleccione un contacto", value: (f) => f.id_familiar, label: (f) => `${f.nombre_completo} — ${f.telefono}` });
  fill("sel-con-parentesco", c.parentescos, { placeholder: "Seleccione parentesco", value: (p) => p.IdParentesco, label: (p) => p.NombreParentesco });
  fill("sel-mov-insumo", c.insumos, { placeholder: "Seleccione un insumo", value: (i) => i.id_insumo, label: (i) => `${i.codigo_insumo} — ${i.nombre_insumo}` });
  fill("sel-mov-tipo", c.tipos_movimiento, { placeholder: "Seleccione tipo", value: (t) => t.IdTipoMovimiento, label: (t) => t.NombreTipoMovimiento });
}

/* -------------------------------- Tablas --------------------------------- */
function renderAll() {
  renderDashboard();
  renderTelemetria();
  Object.keys(TABLES).forEach(renderTable);
}

function renderTable(name) {
  const cfg = TABLES[name];
  const tabla = document.getElementById(`tbl-${name}`);
  if (!tabla) return;

  const todos = state.data[name] || [];
  const q = (state.filtros[name] || "").trim().toLowerCase();
  let filas = todos.slice();
  if (q) {
    filas = filas.filter((f) =>
      cfg.search(f).some((v) => String(v ?? "").toLowerCase().includes(q))
    );
  }

  const orden = state.sort[name];
  if (orden) {
    const col = cfg.columns.find((c) => c.key === orden.key);
    if (col && col.sort) {
      filas.sort((a, b) => {
        const va = col.sort(a);
        const vb = col.sort(b);
        if (typeof va === "number" && typeof vb === "number") return (va - vb) * orden.dir;
        return String(va).localeCompare(String(vb), "es", { numeric: true }) * orden.dir;
      });
    }
  }

  const size = cfg.pageSize || 8;
  const paginas = Math.max(1, Math.ceil(filas.length / size));
  const pagina = Math.min(state.page[name] || 1, paginas);
  state.page[name] = pagina;
  const visibles = filas.slice((pagina - 1) * size, pagina * size);

  const head = cfg.columns.map((c) => {
    const activa = orden && orden.key === c.key;
    const flecha = c.sort ? (activa ? (orden.dir === 1 ? "▲" : "▼") : "↕") : "";
    return `<th class="${c.align || ""} ${c.sort ? "sortable" : ""} ${activa ? "sorted" : ""}"` +
      (c.sort ? ` onclick="ordenar('${name}','${c.key}')"` : "") + `>` +
      `${escapeHtml(c.label)}${c.sort ? `<span class="arrow">${flecha}</span>` : ""}</th>`;
  }).join("");

  const body = visibles.length
    ? visibles.map((f) => {
        const id = f[cfg.idKey];
        const celdas = cfg.columns.map((c) =>
          `<td${c.align ? ` class="${c.align}"` : ""}>${c.render(f)}</td>`
        ).join("");
        const eliminar = cfg.deletable === false ? "" : `
          <button class="icon-btn danger" title="Eliminar" onclick="event.stopPropagation();pedirEliminar('${name}','${id}')">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6"/><path d="M10 11v6M14 11v6"/></svg>
          </button>`;
        return `<tr onclick="verDetalle('${name}','${id}')">${celdas}
          <td class="actions-cell">
            <button class="icon-btn" title="Ver detalle" onclick="event.stopPropagation();verDetalle('${name}','${id}')">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z"/><circle cx="12" cy="12" r="3"/></svg>
            </button>${eliminar}
          </td></tr>`;
      }).join("")
    : `<tr class="no-click"><td colspan="${cfg.columns.length + 1}"><div class="empty">` +
      `${q ? "No se encontraron resultados para la búsqueda." : "Todavía no hay registros."}</div></td></tr>`;

  tabla.innerHTML = `<thead><tr>${head}<th class="right">Acciones</th></tr></thead><tbody>${body}</tbody>`;

  const contador = document.getElementById(`count-${name}`);
  if (contador) contador.textContent = q ? `${filas.length} de ${todos.length}` : todos.length;

  const info = document.getElementById(`info-${name}`);
  if (info) info.textContent = q ? `${filas.length} coincidencia(s)` : `${todos.length} registro(s)`;

  const pager = document.getElementById(`pager-${name}`);
  if (pager) {
    if (filas.length <= size) {
      pager.innerHTML = "";
    } else {
      const desde = (pagina - 1) * size + 1;
      const hasta = Math.min(pagina * size, filas.length);
      pager.innerHTML = `<div class="pager">
        <span>Mostrando ${desde}–${hasta} de ${filas.length}</span>
        <div class="pager-btns">
          <button ${pagina <= 1 ? "disabled" : ""} onclick="pagina('${name}',-1)" title="Anterior">‹</button>
          <span>Página ${pagina} de ${paginas}</span>
          <button ${pagina >= paginas ? "disabled" : ""} onclick="pagina('${name}',1)" title="Siguiente">›</button>
        </div>
      </div>`;
    }
  }
}

function ordenar(name, key) {
  const actual = state.sort[name] || {};
  state.sort[name] = {
    key,
    dir: actual.key === key ? -actual.dir : 1,
  };
  renderTable(name);
}

function pagina(name, delta) {
  state.page[name] = (state.page[name] || 1) + delta;
  renderTable(name);
}

function filtrar(name, valor) {
  state.filtros[name] = valor;
  state.page[name] = 1;
  renderTable(name);
}

/* -------------------------------- Dashboard ------------------------------ */
function renderDashboard() {
  const d = state.data.dashboard;
  if (!d) return;
  const k = d.kpis || {};

  const kpis = $("#kpi-grid");
  if (kpis) {
    kpis.innerHTML = KPI_DEFS.map((def) => {
      const valor = k[def.key] ?? 0;
      return `<div class="stat">
        <div class="stat-head"><span class="ico ${def.tone}">${ICONS[def.icon]}</span></div>
        <div class="num">${nf.format(valor)}</div>
        <div class="lbl">${escapeHtml(def.label)}<small>${escapeHtml(def.sub(k))}</small></div>
      </div>`;
    }).join("");
  }

  const grid = $("#charts-grid");
  if (!grid) return;
  const charts = d.charts || {};
  grid.innerHTML = CHART_DEFS.map((c) => `
    <div class="chart-card">
      <div class="card-head">
        <span class="ico ${c.tone}">${ICONS[c.icon]}</span>
        <div><h3>${escapeHtml(c.title)}</h3><p class="desc">${escapeHtml(c.desc)}</p></div>
      </div>
      <div class="chart-body" id="chart-${c.key}"></div>
    </div>`).join("");

  CHART_DEFS.forEach((c) => {
    const cont = document.getElementById(`chart-${c.key}`);
    if (cont) donutChart(cont, charts[c.key] || [], c);
  });

  const hora = $("#hero-time");
  if (hora) {
    hora.textContent = new Date().toLocaleString("es-GT", {
      day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit",
    });
  }

  renderSparkResumen();
}

const TEL_CHARTS = [
  { key: "riesgo", title: "Mediciones por nivel de riesgo", desc: "Clasificación que calculó PySpark.", center: "Mediciones", icon: "heart", tone: "rose" },
  { key: "alertas", title: "Alertas de saturación", desc: "Mediciones con y sin alerta de SpO2.", center: "Mediciones", icon: "heart", tone: "teal" },
];

const TEL_KPIS = [
  { key: "total", label: "Mediciones", sub: (k) => `${nf.format(k.sinteticos || 0)} sintéticas`, icon: "heart", tone: "teal" },
  { key: "pacientes", label: "Pacientes", sub: () => "en el resumen de riesgo", icon: "users", tone: "blue" },
  { key: "criticos", label: "Críticos", sub: (k) => `${nf.format(k.moderados || 0)} moderados`, icon: "heart", tone: "rose" },
  { key: "alertas", label: "Alertas SpO2", sub: (k) => `${nf.format(k.incompletos || 0)} incompletos`, icon: "heart", tone: "amber" },
];

function kpisPySpark(k) {
  return TEL_KPIS.map((def) => `
    <div class="stat">
      <div class="stat-head"><span class="ico ${def.tone}">${ICONS[def.icon]}</span></div>
      <div class="num">${nf.format(k[def.key] ?? 0)}</div>
      <div class="lbl">${escapeHtml(def.label)}<small>${escapeHtml(def.sub(k))}</small></div>
    </div>`).join("");
}

function topCriticos(resumen) {
  return [...(resumen || [])]
    .sort((a, b) => (Number(b.RegistrosCriticos) || 0) - (Number(a.RegistrosCriticos) || 0)
      || (Number(a.IdPaciente) || 0) - (Number(b.IdPaciente) || 0))
    .slice(0, 5);
}

function pintarGraficasPySpark(grid, prefix) {
  if (!grid) return;
  const data = state.data.analisis || { charts: {}, resumen: [] };
  const charts = data.charts || {};
  const resumen = data.resumen || [];
  grid.innerHTML = TEL_CHARTS.map((c) => `
    <div class="chart-card">
      <div class="card-head">
        <span class="ico ${c.tone}">${ICONS[c.icon]}</span>
        <div><h3>${escapeHtml(c.title)}</h3><p class="desc">${escapeHtml(c.desc)}</p></div>
      </div>
      <div class="chart-body" id="${prefix}-chart-${c.key}"></div>
    </div>`).join("") + `
    <div class="chart-card chart-wide">
      <div class="card-head">
        <span class="ico rose">${ICONS.alert}</span>
        <div><h3>Top 5 con saturación crítica</h3><p class="desc">Pacientes con más mediciones de SpO2 inferior al 90 %, el mismo criterio del procesamiento PySpark.</p></div>
      </div>
      <div class="chart-body" id="${prefix}-chart-top5"></div>
    </div>
    <div class="chart-card chart-wide">
      <div class="card-head">
        <span class="ico blue">${ICONS.users}</span>
        <div><h3>Volumen por paciente</h3><p class="desc">Críticos, moderados y el resto de mediciones de cada paciente.</p></div>
      </div>
      <div class="chart-body" id="${prefix}-chart-pacientes"></div>
    </div>`;
  TEL_CHARTS.forEach((c) => {
    const cont = document.getElementById(`${prefix}-chart-${c.key}`);
    if (cont) donutChart(cont, charts[c.key] || [], c);
  });
  const top = document.getElementById(`${prefix}-chart-top5`);
  if (top) renderBarrasPaciente(top, topCriticos(resumen), { campo: "RegistrosCriticos", color: "#e11d48", leyenda: "Crítico" });
  const barras = document.getElementById(`${prefix}-chart-pacientes`);
  if (barras) renderBarrasPaciente(barras, resumen);
}

function renderSparkResumen() {
  const data = state.data.analisis || { kpis: {}, charts: {}, resumen: [] };
  const kpis = $("#spark-kpis");
  if (kpis) kpis.innerHTML = kpisPySpark(data.kpis || {});
  pintarGraficasPySpark($("#spark-charts"), "spark");
}

function renderTelemetria() {
  const data = state.data.analisis || { kpis: {}, charts: {}, resumen: [] };
  const k = data.kpis || {};
  const kpis = $("#tel-kpis");
  if (kpis) kpis.innerHTML = kpisPySpark(k);

  const aviso = $("#tel-notice");
  if (aviso && data.error) {
    aviso.querySelector("div").innerHTML = `<b>No se pudo leer el procesamiento.</b> ${escapeHtml(data.error)}`;
  }

  pintarGraficasPySpark($("#tel-charts"), "tel");

  const filas = data.resumen || [];
  const badgeCount = $("#count-riesgo");
  if (badgeCount) badgeCount.textContent = nf.format(filas.length);
  const tabla = $("#tbl-riesgo");
  if (!tabla) return;
  const cuerpo = filas.length
    ? filas.map((f) => {
        const ficha = f.dpi ? `DPI ${f.dpi}` : "Sin ficha en Paciente";
        return `<tr>
          <td>${personCell(f.paciente, ficha)}</td>
          <td class="center">${nf.format(f.TotalRegistros)}</td>
          <td class="center">${badge(nf.format(f.RegistrosCriticos), "rose")}</td>
          <td class="center">${badge(nf.format(f.RegistrosModerados), "amber")}</td>
          <td class="center">${nf.format(f.AlertasSpO2)}</td>
          <td class="center">${nf.format(f.RegistrosIncompletos)}</td>
          <td>${fmtDateTime(f.ultima)}</td>
        </tr>`;
      }).join("")
    : `<tr><td colspan="7"><div class="empty"><p>No hay resumen de riesgo cargado.</p></div></td></tr>`;
  tabla.innerHTML = `<thead><tr>
      <th>Paciente</th><th class="center">Total</th><th class="center">Críticos</th>
      <th class="center">Moderados</th><th class="center">Alertas SpO2</th>
      <th class="center">Incompletos</th><th>Última medición</th>
    </tr></thead><tbody>${cuerpo}</tbody>`;
}

function renderBarrasPaciente(cont, filas, opciones = {}) {
  if (!filas.length) {
    cont.innerHTML = `<div class="chart-empty">Sin datos para mostrar.</div>`;
    return;
  }
  const campo = opciones.campo;
  const maximo = Math.max(...filas.map((f) => Number(campo ? f[campo] : f.TotalRegistros) || 0), 1);
  const rows = filas.map((f) => {
    const total = Number(f.TotalRegistros) || 0;
    const crit = Number(f.RegistrosCriticos) || 0;
    const mod = Number(f.RegistrosModerados) || 0;
    const sub = f.dpi ? f.dpi : `Id ${f.IdPaciente}`;
    if (campo) {
      const valor = Number(f[campo]) || 0;
      const ancho = (valor / maximo) * 100;
      return `<div class="bar-row">
        <div class="bar-name" title="${escapeHtml(f.paciente)}">${escapeHtml(f.paciente)}<small>${escapeHtml(sub)}</small></div>
        <div class="bar-track" title="${nf.format(valor)} ${escapeHtml(opciones.leyenda || "")}">
          <span style="width:${ancho}%;background:${opciones.color || "#e11d48"}"></span>
        </div>
        <div class="bar-meta">${nf.format(valor)}</div>
      </div>`;
    }
    const resto = Math.max(total - crit - mod, 0);
    const ancho = (total / maximo) * 100;
    const parte = (n) => (total ? (n / total) * ancho : 0);
    return `<div class="bar-row">
      <div class="bar-name" title="${escapeHtml(f.paciente)}">${escapeHtml(f.paciente)}<small>${escapeHtml(sub)}</small></div>
      <div class="bar-track" title="${nf.format(total)} mediciones">
        <span class="crit" style="width:${parte(crit)}%"></span>
        <span class="mod" style="width:${parte(mod)}%"></span>
        <span class="rest" style="width:${parte(resto)}%"></span>
      </div>
      <div class="bar-meta">${nf.format(total)}</div>
    </div>`;
  }).join("");
  const leyenda = campo
    ? `<div class="bar-legend"><span><i style="background:${opciones.color || "#e11d48"}"></i>${escapeHtml(opciones.leyenda || "Valor")}</span></div>`
    : `<div class="bar-legend">
      <span><i style="background:#e11d48"></i>Crítico</span>
      <span><i style="background:#f59e0b"></i>Moderado</span>
      <span><i style="background:#10b981"></i>Resto</span>
    </div>`;
  cont.innerHTML = `<div class="bar-list">${rows}</div>${leyenda}`;
  cont.style.flexDirection = "column";
  cont.style.alignItems = "stretch";
}

function donutChart(cont, serie, def) {
  const datos = (serie || []).filter((d) => Number(d.value) > 0);
  const total = datos.reduce((s, d) => s + Number(d.value || 0), 0);

  if (!datos.length || total <= 0) {
    cont.innerHTML = `<div class="chart-empty">Sin datos para mostrar.</div>`;
    return;
  }

  let acumulado = 0;
  const segmentos = datos.map((d, i) => {
    const valor = Number(d.value) || 0;
    const pct = (valor / total) * 100;
    const color = colorFor(d.label, i);
    const offset = 25 - acumulado;
    acumulado += pct;
    return `<circle class="seg" cx="21" cy="21" r="15.9155" fill="transparent"
        stroke="${color}" stroke-width="6.2" stroke-dasharray="${pct} ${100 - pct}"
        stroke-dashoffset="${offset}">
        <title>${escapeHtml(d.label)}: ${nf.format(valor)} (${pct.toFixed(1)} %)</title>
      </circle>`;
  }).join("");

  const leyenda = datos.map((d, i) => {
    const valor = Number(d.value) || 0;
    const pct = total ? (valor / total) * 100 : 0;
    return `<li>
      <span class="sw" style="background:${colorFor(d.label, i)}"></span>
      <span class="nm" title="${escapeHtml(d.label)}">${escapeHtml(d.label)}</span>
      <b>${nf.format(valor)}</b><small>${pct.toFixed(0)} %</small>
    </li>`;
  }).join("");

  cont.innerHTML = `
    <div class="donut">
      <svg viewBox="0 0 42 42" role="img" aria-label="${escapeHtml(def.title)}">
        <circle cx="21" cy="21" r="15.9155" fill="transparent" stroke="var(--surface-3)" stroke-width="6.2"></circle>
        ${segmentos}
      </svg>
      <div class="donut-center"><b>${nf.format(total)}</b><small>${escapeHtml(def.center || "Total")}</small></div>
    </div>
    <ul class="legend">${leyenda}</ul>`;
}

/* --------------------------------- Detalle ------------------------------- */
function verDetalle(name, id) {
  const cfg = TABLES[name];
  const fila = (state.data[name] || []).find(
    (x) => String(x[cfg.idKey]) === String(id)
  );
  if (!fila) return;

  const secciones = cfg.detail(fila);
  $("#drawer-title").textContent = cfg.recordName(fila);
  $("#drawer-sub").textContent = cfg.detailSub ? cfg.detailSub(fila) : "";
  $("#drawer-body").innerHTML = secciones.map((sec) => `
    <div class="detail-section">
      ${sec.title ? `<h4>${escapeHtml(sec.title)}</h4>` : ""}
      <div class="detail-list">
        ${sec.rows.map(([k, v]) => `<div class="row"><span class="k">${escapeHtml(k)}</span><span class="v">${v}</span></div>`).join("")}
      </div>
    </div>`).join("");
  $("#drawer").classList.remove("hidden");
}

function cerrarDetalle(ev) {
  if (ev && ev.target !== ev.currentTarget) return;
  $("#drawer").classList.add("hidden");
}

/* ------------------------------- Confirmar ------------------------------- */
function confirmar({ title, html, confirmText }) {
  return new Promise((resolve) => {
    state.confirmResolve = resolve;
    $("#confirm-title").textContent = title;
    $("#confirm-body").innerHTML = html;
    $("#confirm-btn").textContent = confirmText || "Eliminar";
    $("#confirm").classList.remove("hidden");
  });
}

function responderConfirm(ok) {
  $("#confirm").classList.add("hidden");
  const resolver = state.confirmResolve;
  state.confirmResolve = null;
  if (resolver) resolver(ok);
}

async function pedirEliminar(name, id) {
  const cfg = TABLES[name];
  const fila = (state.data[name] || []).find(
    (x) => String(x[cfg.idKey]) === String(id)
  );
  if (!fila) return;

  const extra = cfg.cascade ? cfg.cascade(fila) : "";
  const ok = await confirmar({
    title: `¿Eliminar ${cfg.singular}?`,
    html: `Se eliminará <b>${escapeHtml(cfg.recordName(fila))}</b> de forma permanente.` +
      (extra ? `<div class="cascade">${escapeHtml(extra)}</div>` : ""),
    confirmText: "Sí, eliminar",
  });
  if (!ok) return;

  try {
    const res = await api(`${ENDPOINTS[name]}/${id}`, { method: "DELETE" });
    await recargar([name]);
    cerrarDetalle();
    notify("Registro eliminado", (res && res.detalle) || `${cfg.singular} eliminado correctamente.`, "ok");
  } catch (err) {
    notify("No se pudo eliminar", err.message, "error", true);
  }
}

/* ---------------------------- Notificaciones ----------------------------- */
const NOTIF_ICONS = { ok: "check", error: "alert", info: "info", warn: "alert" };

function notify(title, message, type = "ok", persist = false) {
  const wrap = $("#notifs");
  if (!wrap) return;
  const el = document.createElement("div");
  el.className = `notif ${type}`;
  el.innerHTML = `
    <span class="n-ico">${ICONS[NOTIF_ICONS[type] || "info"]}</span>
    <div class="n-body">
      <b>${escapeHtml(title)}</b>
      <p>${escapeHtml(message || "")}</p>
      <time>${new Date().toLocaleTimeString("es-GT", { hour: "2-digit", minute: "2-digit" })}</time>
    </div>
    <button class="n-x" aria-label="Cerrar">×</button>`;

  wrap.appendChild(el);

  const cerrar = () => {
    el.style.opacity = "0";
    el.style.transform = "translateY(6px)";
    setTimeout(() => el.remove(), 160);
  };
  el.querySelector(".n-x").onclick = cerrar;
  while (wrap.children.length > 5) wrap.firstElementChild.remove();
  if (!persist && type !== "error") setTimeout(cerrar, 6000);
}

/* --------------------------------- Formularios --------------------------- */
async function crearPaciente(e) {
  e.preventDefault();
  const form = e.target;
  const datos = formData(form);
  const btn = form.querySelector('button[type="submit"]');
  setBusy(btn, true);
  try {
    await api("/api/pacientes", { method: "POST", body: JSON.stringify(datos) });
    const nombre = `${datos.nombre} ${datos.apellido}`;
    form.reset();
    await recargar(["pacientes"]);
    notify("Paciente registrado", `${nombre} se guardó correctamente.`, "ok");
  } catch (err) {
    notify("No se pudo guardar el paciente", err.message, "error", true);
  } finally {
    setBusy(btn, false);
  }
}

async function crearEmpleado(e) {
  e.preventDefault();
  const form = e.target;
  const datos = formData(form);
  const btn = form.querySelector('button[type="submit"]');
  setBusy(btn, true);
  try {
    await api("/api/empleados", { method: "POST", body: JSON.stringify(datos) });
    const nombre = `${datos.nombre} ${datos.apellido}`;
    form.reset();
    $("#chk-activo").checked = true;
    await recargar(["empleados"]);
    notify("Empleado registrado", `${nombre} se guardó correctamente.`, "ok");
  } catch (err) {
    notify("No se pudo guardar el empleado", err.message, "error", true);
  } finally {
    setBusy(btn, false);
  }
}

async function crearInsumo(e) {
  e.preventDefault();
  const form = e.target;
  const datos = formData(form);
  const btn = form.querySelector('button[type="submit"]');
  setBusy(btn, true);
  try {
    await api("/api/insumos", { method: "POST", body: JSON.stringify(datos) });
    const nombre = datos.nombre_insumo;
    form.reset();
    await recargar(["insumos"]);
    notify("Insumo registrado", `${nombre} se guardó en el inventario.`, "ok");
  } catch (err) {
    notify("No se pudo guardar el insumo", err.message, "error", true);
  } finally {
    setBusy(btn, false);
  }
}

async function crearAdmision(e) {
  e.preventDefault();
  const form = e.target;
  const datos = formData(form);
  const btn = form.querySelector('button[type="submit"]');
  setBusy(btn, true);
  try {
    await api("/api/admisiones", { method: "POST", body: JSON.stringify(datos) });
    form.reset();
    await recargar(["admisiones"]);
    notify("Admisión registrada", "El ingreso del paciente se guardó correctamente.", "ok");
  } catch (err) {
    notify("No se pudo registrar la admisión", err.message, "error", true);
  } finally {
    setBusy(btn, false);
  }
}

async function crearContacto(e) {
  e.preventDefault();
  const form = e.target;
  const datos = formData(form);
  const btn = form.querySelector('button[type="submit"]');
  setBusy(btn, true);
  try {
    await api("/api/contactos", { method: "POST", body: JSON.stringify(datos) });
    form.reset();
    await recargar(["contactos"]);
    notify("Contacto asignado", "El contacto de emergencia se guardó correctamente.", "ok");
  } catch (err) {
    notify("No se pudo asignar el contacto", err.message, "error", true);
  } finally {
    setBusy(btn, false);
  }
}

async function crearMovimiento(e) {
  e.preventDefault();
  const form = e.target;
  const datos = formData(form);
  const btn = form.querySelector('button[type="submit"]');
  setBusy(btn, true);
  try {
    await api("/api/movimientos", { method: "POST", body: JSON.stringify(datos) });
    form.reset();
    await recargar(["movimientos", "insumos"]);
    notify("Movimiento registrado", "El movimiento de inventario se guardó correctamente.", "ok");
  } catch (err) {
    notify("No se pudo registrar el movimiento", err.message, "error", true);
  } finally {
    setBusy(btn, false);
  }
}

/* ---------------------------------- Tema --------------------------------- */
function applyTheme(tema) {
  const t = tema === "dark" ? "dark" : "light";
  document.documentElement.dataset.theme = t;
  try { localStorage.setItem("hw2-theme", t); } catch (_) { /* ignorar */ }
  const btn = $("#btn-theme");
  if (btn) btn.innerHTML = t === "dark" ? ICONS.sun : ICONS.moon;
}

function toggleTheme() {
  const actual = document.documentElement.dataset.theme === "dark" ? "dark" : "light";
  applyTheme(actual === "dark" ? "light" : "dark");
}

function setToday() {
  const hoy = new Date();
  const etiqueta = $("#today-label");
  if (etiqueta) {
    etiqueta.textContent = hoy.toLocaleDateString("es-GT", {
      weekday: "long", day: "numeric", month: "long", year: "numeric",
    });
  }
  const hora = $("#hero-time");
  if (hora) {
    hora.textContent = hoy.toLocaleString("es-GT", {
      day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit",
    });
  }
}

/* ---------------------------------- Init --------------------------------- */
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") {
    cerrarDetalle();
    if (!$("#confirm").classList.contains("hidden")) responderConfirm(false);
  }
});

document.getElementById("login-pass").addEventListener("keydown", (e) => {
  if (e.key === "Enter") doLogin();
});

document.addEventListener("DOMContentLoaded", async () => {
  let tema = "light";
  try { tema = localStorage.getItem("hw2-theme") || "light"; } catch (_) { /* ignorar */ }
  applyTheme(tema);
  setToday();

  try {
    const me = await api("/api/me");
    if (me && me.user) await enterApp();
  } catch (_) {
    /* sin sesión: se queda en el login */
  }
});
