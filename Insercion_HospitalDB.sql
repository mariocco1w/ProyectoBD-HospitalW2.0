/*
    Proyecto: Hospital W 2.0
    Archivo: 03_Insertar_Datos_Prueba.sql
    Motor: Microsoft SQL Server

    Objetivo:
    Insertar datos sinteticos para probar las tablas,
    relaciones y restricciones del sistema.

    IMPORTANTE:
    La seccion 1-4 requiere las 13 tablas previamente creadas
    y vacias. Si ya contienen datos, esa seccion se omite sola.
    La seccion 5 (tablas nuevas del Excel) es INDEPENDIENTE:
    puede ejecutarse aunque las 13 tablas base ya tengan datos.
    La seccion 5 solo agrega filas; a dbo.Insumo le suma 2
    insumos nuevos (INS-009, INS-010) sin alterar los previos.
*/

USE HospitalW2;
GO

SET NOCOUNT ON;
SET QUOTED_IDENTIFIER ON;
SET ANSI_NULLS ON;
GO

-- 1. VALIDAR QUE LAS TABLAS ESTEN VACIAS
IF EXISTS (SELECT 1 FROM dbo.Turno)
 OR EXISTS (SELECT 1 FROM dbo.Especialidad)
 OR EXISTS (SELECT 1 FROM dbo.Empleado)
 OR EXISTS (SELECT 1 FROM dbo.Sala)
 OR EXISTS (SELECT 1 FROM dbo.AsignacionPersonalSala)
 OR EXISTS (SELECT 1 FROM dbo.Cama)
 OR EXISTS (SELECT 1 FROM dbo.FamiliarResponsable)
 OR EXISTS (SELECT 1 FROM dbo.MedicoExterno)
 OR EXISTS (SELECT 1 FROM dbo.Paciente)
 OR EXISTS (SELECT 1 FROM dbo.Cita)
 OR EXISTS (SELECT 1 FROM dbo.Hospitalizacion)
 OR EXISTS (SELECT 1 FROM dbo.Proveedor)
 OR EXISTS (SELECT 1 FROM dbo.Insumo)
BEGIN
    PRINT 'Las tablas ya contienen datos. Revise la base de datos antes de continuar.';
    RETURN;
END;

BEGIN TRY
    BEGIN TRANSACTION;

    -- TURNOS
    INSERT INTO dbo.Turno (nombre_turno, hora_inicio, hora_fin)
    VALUES ('Matutino', '06:00', '14:00'),
           ('Vespertino','14:00', '22:00'),
           ('Nocturno', '22:00', '06:00');

    -- ESPECIALIDADES
    INSERT INTO dbo.Especialidad (nombre_especialidad, descripcion)
    VALUES ('Medicina General','Atencion medica general'),
           ('Cardiologia','Atencion de enfermedades cardiovasculares'),
           ('Pediatria','Atencion medica infantil'),
           ('Medicina Interna','Atencion integral de adultos'),
           ('Enfermeria','Area de atencion y cuidados de enfermeria');

    -- SALAS
    INSERT INTO dbo.Sala (nombre_sala, ubicacion_piso)
    VALUES ('Medicina General', 'Piso 1'),
           ('Pediatria',        'Piso 2'),
           ('Cuidados Especiales','Piso 3'),
           ('Recuperacion',     'Piso 1');

    -- FAMILIARES RESPONSABLES
    INSERT INTO dbo.FamiliarResponsable (nombre, apellido, telefono, parentesco, direccion)
    VALUES ('Ana',     'Lopez',    '55510001', 'Hija', 'Zona 1, Guatemala'),
           ('Carlos',  'Mendez',   '55510002', 'Hijo', 'Zona 7, Guatemala'),
           ('Lucia',   'Ramirez',  '55510003', 'Esposa', 'Zona 11, Guatemala'),
           ('Pedro',   'Castillo', '55510004', 'Hermano', 'Mixco, Guatemala'),
           ('Sofia',   'Morales',  '55510005', 'Madre', 'Villa Nueva, Guatemala');

    -- MEDICOS EXTERNOS
    INSERT INTO dbo.MedicoExterno (nombre, apellido, telefono, institucion_procedencia)
    VALUES ('Roberto', 'Garcia', '55520001', 'Clinica Central'),
           ('Elena', 'Hernandez', '55520002', 'Centro Medico del Norte'),
           ('Miguel', 'Torres', '55520003', 'Consulta Medica Independiente');

    -- PROVEEDORES (NITs ajustados a 7 caracteres máximo)
    INSERT INTO dbo.Proveedor (razon_social, telefono, direccion, nit)
    VALUES ('Suministros Medicos del Centro','55530001','Zona 4, Guatemala','1234567'),
           ('Distribuidora Hospitalaria GT','55530002','Zona 12, Guatemala','2345678'),
           ('Equipamiento Clinico Nacional','55530003','Mixco, Guatemala','3456789'),
           ('Farmasuministros Integrales','55530004','Villa Nueva, Guatemala','4567890');

    -- EMPLEADOS
    INSERT INTO dbo.Empleado (nss, nombre, apellido, rol, estado_activo, id_turno, id_especialidad)
    SELECT v.nss, v.nombre, v.apellido, v.rol, 1, t.id_turno, e.id_especialidad
    FROM (VALUES
        ('NSS-TEST-001', 'Laura',   'Perez',   'Medico',       'Matutino', 'Medicina General'),
        ('NSS-TEST-002', 'Andres',  'Gomez',   'Medico',       'Vespertino','Cardiologia'),
        ('NSS-TEST-003', 'Claudia', 'Diaz',    'Medico',       'Matutino', 'Pediatria'),
        ('NSS-TEST-004', 'Daniela', 'Ruiz',    'Enfermeria',   'Nocturno', 'Enfermeria'),
        ('NSS-TEST-005', 'Jorge',   'Santos',  'Enfermeria',   'Matutino', 'Enfermeria'),
        ('NSS-TEST-006', 'Marta',   'Flores',  'Administrativo','Vespertino', NULL),
        ('NSS-TEST-007', 'Oscar',   'Reyes',   'Tecnico',      'Nocturno', NULL),
        ('NSS-TEST-008', 'Paola',   'Vargas',  'Medico',       'Nocturno', 'Medicina Interna')
    ) AS v(nss,nombre,apellido,rol,nombre_turno,nombre_especialidad)
    INNER JOIN dbo.Turno AS t ON t.nombre_turno = v.nombre_turno
    LEFT JOIN dbo.Especialidad AS e ON e.nombre_especialidad = v.nombre_especialidad;

    -- CAMAS
    INSERT INTO dbo.Cama (numero_cama, id_sala)
    SELECT v.numero_cama, s.id_sala
    FROM (VALUES
        ('MG-01', 'Medicina General'), ('MG-02', 'Medicina General'), ('MG-03', 'Medicina General'),
        ('PE-01', 'Pediatria'), ('PE-02', 'Pediatria'), ('PE-03', 'Pediatria'),
        ('CE-01', 'Cuidados Especiales'), ('CE-02', 'Cuidados Especiales'), ('CE-03', 'Cuidados Especiales'),
        ('RE-01', 'Recuperacion'), ('RE-02', 'Recuperacion'), ('RE-03', 'Recuperacion')
    ) AS v(numero_cama, nombre_sala)
    INNER JOIN dbo.Sala AS s ON s.nombre_sala = v.nombre_sala;

    -- PACIENTES
    INSERT INTO dbo.Paciente (dpi, nombre, apellido, fecha_nacimiento, genero, direccion, telefono, es_adulto_mayor, id_familiar, id_medico_externo)
    SELECT v.dpi, v.nombre, v.apellido, v.fecha_nacimiento, v.genero, v.direccion, v.telefono, v.es_adulto_mayor,
           COALESCE(f.id_familiar, (SELECT TOP 1 id_familiar FROM dbo.FamiliarResponsable ORDER BY id_familiar)) AS id_familiar,
           COALESCE(me.id_medico_externo, (SELECT TOP 1 id_medico_externo FROM dbo.MedicoExterno ORDER BY id_medico_externo)) AS id_medico_externo
    FROM (VALUES
        ('DPI-TEST-001', 'Mario',  'Alvarez', CONVERT(DATE,'19500115',112), 'Masculino', 'Zona 1, Guatemala',  '55540001', 1, 'Ana','Lopez','55510001','Roberto','Garcia','Clinica Central'),
        ('DPI-TEST-002', 'Teresa', 'Guzman',  CONVERT(DATE,'19450820',112), 'Femenino',  'Zona 7, Guatemala',  '55540002', 1, 'Carlos','Mendez','55510002','Elena','Hernandez','Centro Medico del Norte'),
        ('DPI-TEST-003', 'Diego',  'Ramirez', CONVERT(DATE,'20150510',112), 'Masculino', 'Zona 11, Guatemala', '55540003', 0, 'Lucia','Ramirez','55510003','Miguel','Torres','Consulta Medica Independiente'),
        ('DPI-TEST-004', 'Valeria','Castillo',CONVERT(DATE,'19980312',112), 'Femenino',  'Mixco, Guatemala',   '55540004', 0, NULL,NULL,NULL,'Roberto','Garcia','Clinica Central'),
        ('DPI-TEST-005', 'Jose',   'Morales', CONVERT(DATE,'19620203',112), 'Masculino', 'Villa Nueva, Guatemala','55540005', 1, 'Sofia','Morales','55510005',NULL,NULL,NULL),
        ('DPI-TEST-006', 'Andrea', 'Herrera', CONVERT(DATE,'19870725',112), 'Femenino',  'Zona 5, Guatemala',  '55540006', 0, NULL,NULL,NULL,'Elena','Hernandez','Centro Medico del Norte'),
        ('DPI-TEST-007', 'Fernando','Cruz',   CONVERT(DATE,'19791130',112), 'Masculino', 'Zona 12, Guatemala', '55540007', 0, 'Pedro','Castillo','55510004',NULL,NULL,NULL),
        ('DPI-TEST-008', 'Isabel', 'Mendoza', CONVERT(DATE,'19551109',112), 'Femenino',  'Zona 3, Guatemala',  '55540008', 1, NULL,NULL,NULL,'Miguel','Torres','Consulta Medica Independiente')
    ) AS v(dpi,nombre,apellido,fecha_nacimiento,genero,direccion,telefono,es_adulto_mayor,nombre_familiar,apellido_familiar,telefono_familiar,nombre_medico,apellido_medico,institucion_medico)
    LEFT JOIN dbo.FamiliarResponsable AS f ON f.nombre = v.nombre_familiar AND f.apellido = v.apellido_familiar AND f.telefono = v.telefono_familiar
    LEFT JOIN dbo.MedicoExterno AS me ON me.nombre = v.nombre_medico AND me.apellido = v.apellido_medico AND me.institucion_procedencia = v.institucion_medico;

    -- ASIGNACIONES DE PERSONAL A SALAS
    INSERT INTO dbo.AsignacionPersonalSala (id_empleado, id_sala, fecha_inicio, fecha_fin)
    SELECT e.id_empleado, s.id_sala, v.fecha_inicio, v.fecha_fin
    FROM (VALUES
        ('NSS-TEST-001','Medicina General', CONVERT(DATETIME2,'2026-01-01T06:00:00'), NULL),
        ('NSS-TEST-002','Cuidados Especiales', CONVERT(DATETIME2,'2026-02-01T14:00:00'), NULL),
        ('NSS-TEST-003','Pediatria', CONVERT(DATETIME2,'2026-01-15T06:00:00'), NULL),
        ('NSS-TEST-004','Medicina General', CONVERT(DATETIME2,'2025-01-01T22:00:00'), CONVERT(DATETIME2,'2025-12-31T22:00:00')),
        ('NSS-TEST-005','Recuperacion', CONVERT(DATETIME2,'2026-03-01T06:00:00'), NULL),
        ('NSS-TEST-008','Cuidados Especiales', CONVERT(DATETIME2,'2026-04-01T22:00:00'), NULL)
    ) AS v(nss,nombre_sala,fecha_inicio,fecha_fin)
    INNER JOIN dbo.Empleado AS e ON e.nss = v.nss
    INNER JOIN dbo.Sala AS s ON s.nombre_sala = v.nombre_sala;

    -- CITAS
    INSERT INTO dbo.Cita (id_paciente, id_empleado, fecha_hora_cita, estado, motivo)
    SELECT p.id_paciente, e.id_empleado, v.fecha_hora_cita, v.estado, v.motivo
    FROM (VALUES
        ('DPI-TEST-001','NSS-TEST-001', CONVERT(DATETIME2,'2026-10-15T08:00:00'),'Confirmada','Control medico general'),
        ('DPI-TEST-002','NSS-TEST-002', CONVERT(DATETIME2,'2026-10-16T15:00:00'),'Programada','Evaluacion cardiovascular'),
        ('DPI-TEST-003','NSS-TEST-003', CONVERT(DATETIME2,'2026-10-17T09:30:00'),'Completada','Consulta pediatrica'),
        ('DPI-TEST-004','NSS-TEST-001', CONVERT(DATETIME2,'2026-09-20T10:00:00'),'Completada','Revision general'),
        ('DPI-TEST-005','NSS-TEST-008', CONVERT(DATETIME2,'2026-10-18T23:00:00'),'Programada','Consulta de medicina interna'),
        ('DPI-TEST-006','NSS-TEST-003', CONVERT(DATETIME2,'2026-10-19T11:00:00'),'Cancelada','Seguimiento de consulta')
    ) AS v(dpi,nss,fecha_hora_cita,estado,motivo)
    INNER JOIN dbo.Paciente AS p ON p.dpi = v.dpi
    INNER JOIN dbo.Empleado AS e ON e.nss = v.nss;

    -- HOSPITALIZACIONES
    INSERT INTO dbo.Hospitalizacion (id_paciente, id_cama, fecha_hora_ingreso, fecha_hora_salida_real, motivo_ingreso, estado)
    SELECT p.id_paciente, c.id_cama, v.fecha_ingreso, v.fecha_salida, v.motivo_ingreso, v.estado
    FROM (VALUES
        ('DPI-TEST-001','Medicina General','MG-01', CONVERT(DATETIME2,'2026-10-10T08:00:00'), CAST(NULL AS DATETIME2), 'Observacion medica','Activa'),
        ('DPI-TEST-002','Cuidados Especiales','CE-01', CONVERT(DATETIME2,'2026-10-12T11:30:00'), CAST(NULL AS DATETIME2), 'Monitoreo cardiovascular','Activa'),
        ('DPI-TEST-005','Medicina General','MG-02', CONVERT(DATETIME2,'2026-10-01T09:00:00'), CONVERT(DATETIME2,'2026-10-04T14:00:00'), 'Recuperacion general','Finalizada'),
        ('DPI-TEST-003','Pediatria','PE-01', CONVERT(DATETIME2,'2026-09-10T10:00:00'), CONVERT(DATETIME2,'2026-09-12T12:00:00'), 'Observacion pediatrica','Finalizada'),
        ('DPI-TEST-006','Recuperacion','RE-01', CONVERT(DATETIME2,'2026-10-05T13:00:00'), CAST(NULL AS DATETIME2), 'Ingreso cancelado antes de la atencion','Cancelada')
    ) AS v(dpi,nombre_sala,numero_cama,fecha_ingreso,fecha_salida,motivo_ingreso,estado)
    INNER JOIN dbo.Paciente AS p ON p.dpi = v.dpi
    INNER JOIN dbo.Sala AS s ON s.nombre_sala = v.nombre_sala
    INNER JOIN dbo.Cama AS c ON c.id_sala = s.id_sala AND c.numero_cama = v.numero_cama;

    -- INSUMOS
    INSERT INTO dbo.Insumo (codigo_insumo, nombre_insumo, tipo_insumo, stock_existencia, stock_maximo, costo_unitario, id_proveedor)
    SELECT v.codigo_insumo, v.nombre_insumo, v.tipo_insumo, v.stock_existencia, v.stock_maximo, v.costo_unitario, p.id_proveedor
    FROM (VALUES
        ('INS-001','Guantes desechables','Proteccion', CAST(10 AS DECIMAL(12,2)), CAST(100 AS DECIMAL(12,2)), CAST(0.75 AS DECIMAL(12,2)),'Suministros Medicos del Centro'),
        ('INS-002','Mascarillas quirurgicas','Proteccion', CAST(80 AS DECIMAL(12,2)), CAST(200 AS DECIMAL(12,2)), CAST(0.50 AS DECIMAL(12,2)),'Suministros Medicos del Centro'),
        ('INS-003','Jeringas desechables','Material medico', CAST(15 AS DECIMAL(12,2)), CAST(150 AS DECIMAL(12,2)), CAST(1.25 AS DECIMAL(12,2)),'Distribuidora Hospitalaria GT'),
        ('INS-004','Gasas esteriles','Curacion', CAST(12 AS DECIMAL(12,2)), CAST(100 AS DECIMAL(12,2)), CAST(2.50 AS DECIMAL(12,2)),'Distribuidora Hospitalaria GT'),
        ('INS-005','Vendas elasticas','Curacion', CAST(45 AS DECIMAL(12,2)), CAST(100 AS DECIMAL(12,2)), CAST(4.00 AS DECIMAL(12,2)),'Equipamiento Clinico Nacional'),
        ('INS-006','Termometros digitales','Equipo medico', CAST(20 AS DECIMAL(12,2)), CAST(40 AS DECIMAL(12,2)), CAST(35.00 AS DECIMAL(12,2)),'Equipamiento Clinico Nacional'),
        ('INS-007','Batas desechables','Proteccion', CAST(5 AS DECIMAL(12,2)), CAST(100 AS DECIMAL(12,2)), CAST(3.50 AS DECIMAL(12,2)),'Farmasuministros Integrales'),
        ('INS-008','Esparadrapo medico','Curacion', CAST(30 AS DECIMAL(12,2)), CAST(80 AS DECIMAL(12,2)), CAST(6.00 AS DECIMAL(12,2)),'Farmasuministros Integrales')
    ) AS v(codigo_insumo,nombre_insumo,tipo_insumo,stock_existencia,stock_maximo,costo_unitario,razon_social)
    INNER JOIN dbo.Proveedor AS p ON p.razon_social = v.razon_social;

    COMMIT TRANSACTION;
    PRINT 'Datos de prueba insertados correctamente.';
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
    PRINT 'Ocurrio un error. La transaccion fue revertida.';
    THROW;
END CATCH;

-- 4. RESUMEN DE REGISTROS INSERTADOS
SELECT 'Turno' AS Tabla, COUNT(*) AS Total FROM dbo.Turno
UNION ALL SELECT 'Especialidad', COUNT(*) FROM dbo.Especialidad
UNION ALL SELECT 'Empleado', COUNT(*) FROM dbo.Empleado
UNION ALL SELECT 'Sala', COUNT(*) FROM dbo.Sala
UNION ALL SELECT 'AsignacionPersonalSala', COUNT(*) FROM dbo.AsignacionPersonalSala
UNION ALL SELECT 'Cama', COUNT(*) FROM dbo.Cama
UNION ALL SELECT 'FamiliarResponsable', COUNT(*) FROM dbo.FamiliarResponsable
UNION ALL SELECT 'MedicoExterno', COUNT(*) FROM dbo.MedicoExterno
UNION ALL SELECT 'Paciente', COUNT(*) FROM dbo.Paciente
UNION ALL SELECT 'Cita', COUNT(*) FROM dbo.Cita
UNION ALL SELECT 'Hospitalizacion', COUNT(*) FROM dbo.Hospitalizacion
UNION ALL SELECT 'Proveedor', COUNT(*) FROM dbo.Proveedor
UNION ALL SELECT 'Insumo', COUNT(*) FROM dbo.Insumo
ORDER BY Tabla;
GO

/* =====================================================
   5. DATOS DE PRUEBA PARA LAS TABLAS NUEVAS
      (segun "Tablas proyecto pro.xlsx")
   -----------------------------------------------------
   Seccion INDEPENDIENTE de las 13 tablas base:
   - Corre aunque las 13 tablas base ya tengan datos.
   - Se omite sola si las tablas nuevas ya tienen datos.
   - Solo agrega filas (a dbo.Insumo le suma INS-009/INS-010).
   - Usa llaves naturales (DPI, razon social, codigo_insumo,
     nombres de turno/especialidad/puesto).

   Tablas ELIMINADAS por duplicar originales (no se insertan):
     PERSONAL, SUMINISTRO, MEDICO_REFERENTE,
     CONTACTO_EMERGENCIA, ESTADO_CITA, ESTADO_HOSPITALIZACION
   Por eso ADMISION usa dbo.MedicoExterno y MOVIMIENTO_INVENTARIO
   usa dbo.Insumo.

   Revision "Tabla pisada.xlsx": se agrega la tabla
   ASIGNACION_CONTACTO_EMERGENCIA (AsigContEm).
   ===================================================== */

-- 5.1 VALIDAR QUE LAS TABLAS NUEVAS ESTEN VACIAS
IF EXISTS (SELECT 1 FROM dbo.PUESTO)
 OR EXISTS (SELECT 1 FROM dbo.PARENTESCO)
 OR EXISTS (SELECT 1 FROM dbo.CENTRO_MEDICO)
 OR EXISTS (SELECT 1 FROM dbo.TIPO_SALA)
 OR EXISTS (SELECT 1 FROM dbo.TIPO_MOVIMIENTO)
 OR EXISTS (SELECT 1 FROM dbo.TELEFONO)
 OR EXISTS (SELECT 1 FROM dbo.DIRECCION)
 OR EXISTS (SELECT 1 FROM dbo.ADMISION)
 OR EXISTS (SELECT 1 FROM dbo.MOVIMIENTO_INVENTARIO)
 OR EXISTS (SELECT 1 FROM dbo.REGISTRO_TELEMETRIA)
 OR EXISTS (SELECT 1 FROM dbo.ASIGNACION_CONTACTO_EMERGENCIA)
BEGIN
    PRINT 'Las tablas nuevas ya contienen datos. Se omite la seccion 5.';
    RETURN;
END;

BEGIN TRY
    BEGIN TRANSACTION;

    -- 5.2 CATALOGOS SIMPLES
    INSERT INTO dbo.PUESTO (NombrePuesto)
    VALUES ('Medico General'),
           ('Medico Especialista'),
           ('Enfermero(a)'),
           ('Tecnico de Laboratorio'),
           ('Administrativo'),
           ('Recepcionista');

    INSERT INTO dbo.PARENTESCO (NombreParentesco)
    VALUES ('Madre'), ('Padre'), ('Esposa'), ('Esposo'),
           ('Hija'), ('Hijo'), ('Hermana'), ('Hermano'),
           ('Tutor'), ('Otro');

    INSERT INTO dbo.CENTRO_MEDICO (NombreCentroMedico)
    VALUES ('Hospital Roosevelt'),
           ('Hospital General San Juan de Dios'),
           ('Clinica Central'),
           ('Centro Medico del Norte'),
           ('IGSS');

    INSERT INTO dbo.TIPO_SALA (NombreTipoSala)
    VALUES ('Hospitalizacion'), ('Cuidados Intensivos'),
           ('Recuperacion'), ('Consulta Externa'), ('Emergencia');

    INSERT INTO dbo.TIPO_MOVIMIENTO (NombreTipoMovimiento)
    VALUES ('Entrada'), ('Salida'), ('Ajuste'), ('Devolucion');

    -- 5.3 INSUMOS ADICIONALES EN LA TABLA BASE dbo.Insumo
    --     (necesarios para los movimientos de inventario)
    INSERT INTO dbo.Insumo (codigo_insumo, nombre_insumo, tipo_insumo, stock_existencia, stock_maximo, costo_unitario, id_proveedor)
    SELECT v.codigo, v.nombre, v.tipo, v.stock, v.maximo, v.costo, pr.id_proveedor
    FROM (VALUES
        ('INS-009','Solucion salina 500ml','Solucion',      CAST(200 AS DECIMAL(12,2)), CAST(400 AS DECIMAL(12,2)), CAST(12.50 AS DECIMAL(12,2)),'Farmasuministros Integrales'),
        ('INS-010','Alcohol gel 1L',       'Desinfectante', CAST(80  AS DECIMAL(12,2)), CAST(150 AS DECIMAL(12,2)), CAST(30.00 AS DECIMAL(12,2)),'Equipamiento Clinico Nacional')
    ) AS v(codigo,nombre,tipo,stock,maximo,costo,razon_social)
    INNER JOIN dbo.Proveedor AS pr ON pr.razon_social = v.razon_social;

    -- 5.4 ADMISION (FK -> Paciente, dbo.MedicoExterno)
    --     Los medicos se resuelven por nombre+apellido de la tabla
    --     original MedicoExterno (NULL si no hay coincidencia).
    INSERT INTO dbo.ADMISION (IdPaciente, IdMedicoExterno, FechaRegistro)
    SELECT p.id_paciente, me.id_medico_externo, v.fecha
    FROM (VALUES
        ('DPI-TEST-001','Dr. Roberto Garcia',   CONVERT(DATETIME2,'2026-10-10T08:00:00')),
        ('DPI-TEST-002','Dra. Elena Hernandez', CONVERT(DATETIME2,'2026-10-12T11:30:00')),
        ('DPI-TEST-003','Dr. Miguel Torres',    CONVERT(DATETIME2,'2026-09-10T10:00:00')),
        ('DPI-TEST-005','Dr. Roberto Garcia',   CONVERT(DATETIME2,'2026-10-01T09:00:00')),
        ('DPI-TEST-006','Dra. Ana Castillo',    CONVERT(DATETIME2,'2026-10-05T13:00:00'))
    ) AS v(dpi, medico, fecha)
    INNER JOIN dbo.Paciente AS p ON p.dpi = v.dpi
    LEFT JOIN dbo.MedicoExterno AS me
        ON (me.nombre + ' ' + me.apellido)
           = REPLACE(REPLACE(v.medico, 'Dra. ', ''), 'Dr. ', '');

    -- 5.5 MOVIMIENTO_INVENTARIO (FK -> dbo.Insumo, TIPO_MOVIMIENTO)
    --     Se resuelve el insumo por codigo_insumo original.
    INSERT INTO dbo.MOVIMIENTO_INVENTARIO (IdInsumo, FechaHora, IdTipoMovimiento, Cantidad, CostoUnitario, Observacion)
    SELECT i.id_insumo, v.fecha, tm.IdTipoMovimiento, v.cantidad, v.costo, v.obs
    FROM (VALUES
        ('INS-001', CONVERT(DATETIME2,'2026-10-05T09:00:00'),'Entrada', CAST(100 AS DECIMAL(12,2)), CAST(45.00 AS DECIMAL(12,2)),'Compra inicial (guantes)'),
        ('INS-002', CONVERT(DATETIME2,'2026-10-06T10:30:00'),'Entrada', CAST(50  AS DECIMAL(12,2)), CAST(85.00 AS DECIMAL(12,2)),'Compra de reposicion (mascarillas)'),
        ('INS-009', CONVERT(DATETIME2,'2026-10-07T08:15:00'),'Entrada', CAST(200 AS DECIMAL(12,2)), CAST(12.50 AS DECIMAL(12,2)),'Reposicion de stock (solucion salina)'),
        ('INS-001', CONVERT(DATETIME2,'2026-10-08T14:00:00'),'Salida',  CAST(20  AS DECIMAL(12,2)), CAST(45.00 AS DECIMAL(12,2)),'Consumo sala de emergencia (guantes)'),
        ('INS-010', CONVERT(DATETIME2,'2026-10-09T11:00:00'),'Ajuste',  CAST(5   AS DECIMAL(12,2)), CAST(30.00 AS DECIMAL(12,2)),'Ajuste por conteo fisico (alcohol gel)')
    ) AS v(codigo_insumo, fecha, tipo_mov, cantidad, costo, obs)
    INNER JOIN dbo.Insumo AS i            ON i.codigo_insumo = v.codigo_insumo
    INNER JOIN dbo.TIPO_MOVIMIENTO AS tm  ON tm.NombreTipoMovimiento = v.tipo_mov;

    -- 5.6 REGISTRO_TELEMETRIA (FK -> Paciente)
    INSERT INTO dbo.REGISTRO_TELEMETRIA (IdPaciente, MarcaTiempo, FrecuenciaCardiaca, SaturacionOxigeno, AlertaGenerada)
    SELECT p.id_paciente, v.marca, v.fc, v.sat, v.alerta
    FROM (VALUES
        ('DPI-TEST-001', CONVERT(DATETIME2,'2026-10-14T07:00:00'), 78,  CAST(97.50 AS DECIMAL(5,2)), CAST(0 AS BIT)),
        ('DPI-TEST-001', CONVERT(DATETIME2,'2026-10-14T12:00:00'), 82,  CAST(96.00 AS DECIMAL(5,2)), CAST(0 AS BIT)),
        ('DPI-TEST-002', CONVERT(DATETIME2,'2026-10-14T08:00:00'), 105, CAST(94.00 AS DECIMAL(5,2)), CAST(1 AS BIT)),
        ('DPI-TEST-002', CONVERT(DATETIME2,'2026-10-14T13:00:00'), 98,  CAST(95.50 AS DECIMAL(5,2)), CAST(0 AS BIT)),
        ('DPI-TEST-005', CONVERT(DATETIME2,'2026-10-03T09:00:00'), 76,  CAST(98.00 AS DECIMAL(5,2)), CAST(0 AS BIT))
    ) AS v(dpi, marca, fc, sat, alerta)
    INNER JOIN dbo.Paciente AS p ON p.dpi = v.dpi;

    -- 5.7 TELEFONO (referencia polimorfica: TipoEntidad + IdEntidad)
    --     Solo entidades que existen (Paciente); PERSONAL fue eliminada.
    INSERT INTO dbo.TELEFONO (TipoEntidad, IdEntidad, NumeroTelefono, TipoTelefono)
    SELECT 'Paciente', p.id_paciente, v.numero, v.tipo
    FROM (VALUES
        ('DPI-TEST-001','55541001','Casa'),
        ('DPI-TEST-002','55542002','Casa'),
        ('DPI-TEST-003','55543003','Madre')
    ) AS v(dpi, numero, tipo)
    INNER JOIN dbo.Paciente AS p ON p.dpi = v.dpi;

    -- 5.8 DIRECCION (referencia polimorfica por TipoEntidad; el Excel no incluye IdEntidad)
    INSERT INTO dbo.DIRECCION (TipoEntidad, DireccionCompleta, Zona, Municipio, Departamento, Pais, TipoDireccion, EsPrincipal)
    VALUES ('Paciente',  'Zona 1, Guatemala',  'Zona 1',  'Guatemala', 'Guatemala', 'Guatemala', 'Casa',   1),
           ('Paciente',  'Zona 7, Guatemala',  'Zona 7',  'Guatemala', 'Guatemala', 'Guatemala', 'Casa',   1),
           ('Proveedor', 'Zona 12, Guatemala', 'Zona 12', 'Guatemala', 'Guatemala', 'Guatemala', 'Bodega', 1);

    COMMIT TRANSACTION;
    PRINT 'Datos de prueba de las tablas nuevas insertados correctamente.';
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
    PRINT 'Ocurrio un error en las tablas nuevas. La transaccion fue revertida.';
    THROW;
END CATCH;

    -- 5.9 ASIGNACION_CONTACTO_EMERGENCIA (AsigContEm)
    --     Contactos de emergencia por paciente con su parentesco.
    INSERT INTO dbo.ASIGNACION_CONTACTO_EMERGENCIA (IdPaciente, IdFamiliar, IdParentesco)
    SELECT p.id_paciente, f.id_familiar, pa.IdParentesco
    FROM (VALUES
        ('DPI-TEST-001','Ana Lopez',     'Hija'),
        ('DPI-TEST-001','Sofia Morales', 'Madre'),
        ('DPI-TEST-002','Carlos Mendez', 'Hijo'),
        ('DPI-TEST-003','Lucia Ramirez', 'Esposa'),
        ('DPI-TEST-004','Ana Lopez',     'Hija'),
        ('DPI-TEST-005','Sofia Morales', 'Madre'),
        ('DPI-TEST-006','Ana Lopez',     'Hija'),
        ('DPI-TEST-007','Pedro Castillo','Hermano'),
        ('DPI-TEST-008','Ana Lopez',     'Hija')
    ) AS v(dpi, familiar, parentesco)
    INNER JOIN dbo.Paciente AS p
        ON p.dpi = v.dpi
    INNER JOIN dbo.FamiliarResponsable AS f
        ON f.nombre = LEFT(v.familiar, CHARINDEX(' ', v.familiar) - 1)
       AND f.apellido = SUBSTRING(v.familiar, CHARINDEX(' ', v.familiar) + 1, 100)
    INNER JOIN dbo.PARENTESCO AS pa
        ON pa.NombreParentesco = v.parentesco;

    -- 5.10 RESUMEN DE LAS TABLAS NUEVAS (solo las que quedan)
SELECT 'PUESTO' AS Tabla, COUNT(*) AS Total FROM dbo.PUESTO
UNION ALL SELECT 'PARENTESCO', COUNT(*) FROM dbo.PARENTESCO
UNION ALL SELECT 'CENTRO_MEDICO', COUNT(*) FROM dbo.CENTRO_MEDICO
UNION ALL SELECT 'TIPO_SALA', COUNT(*) FROM dbo.TIPO_SALA
UNION ALL SELECT 'TIPO_MOVIMIENTO', COUNT(*) FROM dbo.TIPO_MOVIMIENTO
UNION ALL SELECT 'TELEFONO', COUNT(*) FROM dbo.TELEFONO
UNION ALL SELECT 'DIRECCION', COUNT(*) FROM dbo.DIRECCION
UNION ALL SELECT 'ADMISION', COUNT(*) FROM dbo.ADMISION
UNION ALL SELECT 'MOVIMIENTO_INVENTARIO', COUNT(*) FROM dbo.MOVIMIENTO_INVENTARIO
UNION ALL SELECT 'REGISTRO_TELEMETRIA', COUNT(*) FROM dbo.REGISTRO_TELEMETRIA
UNION ALL SELECT 'ASIGNACION_CONTACTO', COUNT(*) FROM dbo.ASIGNACION_CONTACTO_EMERGENCIA
ORDER BY Tabla;
