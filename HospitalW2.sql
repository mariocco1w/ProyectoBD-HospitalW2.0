/*
Archivo principal para la base de datos del Hospital W2.0
Objetivo del Archivo: Motor Principal

Creacion del Archivo por:Mario Renato Monroy Cortez - 23000140
*/



IF DB_ID(N'HospitalW2') IS NULL
BEGIN
    CREATE DATABASE HospitalW2;
END;
GO

USE HospitalW2;
GO
SET NOCOUNT ON;
SET QUOTED_IDENTIFIER ON;
SET ANSI_NULLS ON;
GO
-- =====================================================
-- 0. VALIDAR SI LAS TABLAS YA EXISTEN
-- =====================================================
IF OBJECT_ID(N'dbo.Turno', N'U') IS NOT NULL
   OR OBJECT_ID(N'dbo.Especialidad', N'U') IS NOT NULL
   OR OBJECT_ID(N'dbo.Empleado', N'U') IS NOT NULL
   OR OBJECT_ID(N'dbo.Sala', N'U') IS NOT NULL
   OR OBJECT_ID(N'dbo.AsignacionPersonalSala', N'U') IS NOT NULL
   OR OBJECT_ID(N'dbo.Cama', N'U') IS NOT NULL
   OR OBJECT_ID(N'dbo.FamiliarResponsable', N'U') IS NOT NULL
   OR OBJECT_ID(N'dbo.MedicoExterno', N'U') IS NOT NULL
   OR OBJECT_ID(N'dbo.Paciente', N'U') IS NOT NULL
   OR OBJECT_ID(N'dbo.Cita', N'U') IS NOT NULL
   OR OBJECT_ID(N'dbo.Hospitalizacion', N'U') IS NOT NULL
   OR OBJECT_ID(N'dbo.Proveedor', N'U') IS NOT NULL
   OR OBJECT_ID(N'dbo.Insumo', N'U') IS NOT NULL
BEGIN
    PRINT 'Se detectaron tablas existentes. Revise la base de datos antes de ejecutar este script.';
    RETURN;
END;


-- =====================================================
-- 1. TABLA: TURNO
-- =====================================================

CREATE TABLE dbo.Turno
(
    id_turno INT IDENTITY(1,1) NOT NULL,
    nombre_turno VARCHAR(50) NOT NULL,
    hora_inicio TIME(0) NOT NULL,
    hora_fin TIME(0) NOT NULL,

    CONSTRAINT PK_Turno
        PRIMARY KEY CLUSTERED (id_turno),

    CONSTRAINT UQ_Turno_Nombre
        UNIQUE (nombre_turno),

    CONSTRAINT CK_Turno_Horas
        CHECK (hora_inicio <> hora_fin)
);

-- =====================================================
-- 2. TABLA: ESPECIALIDAD
-- =====================================================

CREATE TABLE dbo.Especialidad
(
    id_especialidad INT IDENTITY(1,1) NOT NULL,
    nombre_especialidad VARCHAR(100) NOT NULL,
    descripcion VARCHAR(300) NULL,

    CONSTRAINT PK_Especialidad
        PRIMARY KEY CLUSTERED (id_especialidad),

    CONSTRAINT UQ_Especialidad_Nombre
        UNIQUE (nombre_especialidad)
);

-- =====================================================
-- 3. TABLA: SALA
-- =====================================================

CREATE TABLE dbo.Sala
(
    id_sala INT IDENTITY(1,1) NOT NULL,
    nombre_sala VARCHAR(100) NOT NULL,
    ubicacion_piso VARCHAR(50) NOT NULL,

    CONSTRAINT PK_Sala
        PRIMARY KEY CLUSTERED (id_sala),

    CONSTRAINT UQ_Sala_Nombre
        UNIQUE (nombre_sala)
);

-- =====================================================
-- 4. TABLA: FAMILIAR RESPONSABLE
-- =====================================================

CREATE TABLE dbo.FamiliarResponsable
(
    id_familiar INT IDENTITY(1,1) NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    apellido VARCHAR(100) NOT NULL,
    telefono VARCHAR(25) NOT NULL,
    parentesco VARCHAR(50) NOT NULL,
    direccion VARCHAR(250) NULL,

    CONSTRAINT PK_FamiliarResponsable
        PRIMARY KEY CLUSTERED (id_familiar)
);

-- =====================================================
-- 5. TABLA: MEDICO EXTERNO
-- =====================================================

CREATE TABLE dbo.MedicoExterno
(
    id_medico_externo INT IDENTITY(1,1) NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    apellido VARCHAR(100) NOT NULL,
    telefono VARCHAR(25) NULL,
    institucion_procedencia VARCHAR(150) NULL,

    CONSTRAINT PK_MedicoExterno
        PRIMARY KEY CLUSTERED (id_medico_externo)
);

-- =====================================================
-- 6. TABLA: PROVEEDOR
-- =====================================================

CREATE TABLE dbo.Proveedor
(
    id_proveedor INT IDENTITY(1,1) NOT NULL,
    razon_social VARCHAR(150) NOT NULL,
    telefono VARCHAR(25) NOT NULL,
    direccion VARCHAR(250) NOT NULL,
    nit VARCHAR(20) NOT NULL,

    CONSTRAINT PK_Proveedor
        PRIMARY KEY CLUSTERED (id_proveedor),

    CONSTRAINT UQ_Proveedor_NIT
        UNIQUE (nit)
);

-- =====================================================
-- 7. TABLA: EMPLEADO
-- =====================================================

CREATE TABLE dbo.Empleado
(
    id_empleado INT IDENTITY(1,1) NOT NULL,
    nss VARCHAR(30) NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    apellido VARCHAR(100) NOT NULL,
    rol VARCHAR(30) NOT NULL,
    estado_activo BIT NOT NULL
        CONSTRAINT DF_Empleado_Estado DEFAULT (1),
    id_turno INT NOT NULL,
    id_especialidad INT NULL,

    CONSTRAINT PK_Empleado
        PRIMARY KEY CLUSTERED (id_empleado),

    CONSTRAINT UQ_Empleado_NSS
        UNIQUE (nss),

    CONSTRAINT CK_Empleado_Rol
        CHECK (rol IN (
            'Medico',
            'Enfermeria',
            'Administrativo',
            'Tecnico',
            'Otro'
        )),

    CONSTRAINT FK_Empleado_Turno
        FOREIGN KEY (id_turno)
        REFERENCES dbo.Turno(id_turno),

    CONSTRAINT FK_Empleado_Especialidad
        FOREIGN KEY (id_especialidad)
        REFERENCES dbo.Especialidad(id_especialidad)
);

-- =====================================================
-- 8. TABLA: CAMA
-- =====================================================

CREATE TABLE dbo.Cama
(
    id_cama INT IDENTITY(1,1) NOT NULL,
    numero_cama VARCHAR(20) NOT NULL,
    id_sala INT NOT NULL,

    CONSTRAINT PK_Cama
        PRIMARY KEY CLUSTERED (id_cama),

    CONSTRAINT UQ_Cama_Sala_Numero
        UNIQUE (id_sala, numero_cama),

    CONSTRAINT FK_Cama_Sala
        FOREIGN KEY (id_sala)
        REFERENCES dbo.Sala(id_sala)
);

-- =====================================================
-- 9. TABLA: PACIENTE
-- =====================================================

CREATE TABLE dbo.Paciente
(
    id_paciente INT IDENTITY(1,1) NOT NULL,
    dpi VARCHAR(20) NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    apellido VARCHAR(100) NOT NULL,
    fecha_nacimiento DATE NOT NULL,
    genero VARCHAR(20) NOT NULL,
    direccion VARCHAR(250) NOT NULL,
    telefono VARCHAR(25) NOT NULL,
    es_adulto_mayor BIT NOT NULL
        CONSTRAINT DF_Paciente_AdultoMayor DEFAULT (0),
    id_familiar INT NULL,
    id_medico_externo INT NULL,

    CONSTRAINT PK_Paciente
        PRIMARY KEY CLUSTERED (id_paciente),

    CONSTRAINT UQ_Paciente_DPI
        UNIQUE (dpi),

    CONSTRAINT CK_Paciente_Genero
        CHECK (genero IN (
            'Femenino',
            'Masculino',
            'Otro',
            'No especificado'
        )),

    CONSTRAINT FK_Paciente_Familiar
        FOREIGN KEY (id_familiar)
        REFERENCES dbo.FamiliarResponsable(id_familiar),

    CONSTRAINT FK_Paciente_MedicoExterno
        FOREIGN KEY (id_medico_externo)
        REFERENCES dbo.MedicoExterno(id_medico_externo)
);

-- =====================================================
-- 10. TABLA: ASIGNACION DE PERSONAL A SALAS
-- =====================================================

CREATE TABLE dbo.AsignacionPersonalSala
(
    id_asignacion INT IDENTITY(1,1) NOT NULL,
    id_empleado INT NOT NULL,
    id_sala INT NOT NULL,
    fecha_inicio DATETIME2(0) NOT NULL
        CONSTRAINT DF_Asignacion_FechaInicio
        DEFAULT (SYSDATETIME()),
    fecha_fin DATETIME2(0) NULL,

    CONSTRAINT PK_AsignacionPersonalSala
        PRIMARY KEY CLUSTERED (id_asignacion),

    CONSTRAINT CK_Asignacion_Fechas
        CHECK (
            fecha_fin IS NULL
            OR fecha_fin >= fecha_inicio
        ),

    CONSTRAINT FK_Asignacion_Empleado
        FOREIGN KEY (id_empleado)
        REFERENCES dbo.Empleado(id_empleado),

    CONSTRAINT FK_Asignacion_Sala
        FOREIGN KEY (id_sala)
        REFERENCES dbo.Sala(id_sala)
);

-- =====================================================
-- 11. TABLA: CITA
-- =====================================================

CREATE TABLE dbo.Cita
(
    id_cita INT IDENTITY(1,1) NOT NULL,
    id_paciente INT NOT NULL,
    id_empleado INT NOT NULL,
    fecha_hora_cita DATETIME2(0) NOT NULL,
    estado VARCHAR(20) NOT NULL
        CONSTRAINT DF_Cita_Estado DEFAULT ('Programada'),
    motivo VARCHAR(300) NULL,

    CONSTRAINT PK_Cita
        PRIMARY KEY CLUSTERED (id_cita),

    CONSTRAINT CK_Cita_Estado
        CHECK (estado IN (
            'Programada',
            'Confirmada',
            'Completada',
            'Cancelada',
            'No asistio'
        )),

    CONSTRAINT FK_Cita_Paciente
        FOREIGN KEY (id_paciente)
        REFERENCES dbo.Paciente(id_paciente),

    CONSTRAINT FK_Cita_Empleado
        FOREIGN KEY (id_empleado)
        REFERENCES dbo.Empleado(id_empleado)
);

-- =====================================================
-- 12. TABLA: HOSPITALIZACION
-- =====================================================

CREATE TABLE dbo.Hospitalizacion
(
    id_hospitalizacion INT IDENTITY(1,1) NOT NULL,
    id_paciente INT NOT NULL,
    id_cama INT NOT NULL,
    fecha_hora_ingreso DATETIME2(0) NOT NULL
        CONSTRAINT DF_Hospitalizacion_Ingreso
        DEFAULT (SYSDATETIME()),
    fecha_hora_salida_real DATETIME2(0) NULL,
    motivo_ingreso VARCHAR(300) NOT NULL,
    estado VARCHAR(20) NOT NULL
        CONSTRAINT DF_Hospitalizacion_Estado DEFAULT ('Activa'),

    CONSTRAINT PK_Hospitalizacion
        PRIMARY KEY CLUSTERED (id_hospitalizacion),

    CONSTRAINT CK_Hospitalizacion_Estado
        CHECK (estado IN (
            'Activa',
            'Finalizada',
            'Cancelada'
        )),

    CONSTRAINT CK_Hospitalizacion_Fechas
        CHECK (
            fecha_hora_salida_real IS NULL
            OR fecha_hora_salida_real >= fecha_hora_ingreso
        ),

    CONSTRAINT CK_Hospitalizacion_Consistencia
        CHECK (
            (estado = 'Activa'
                AND fecha_hora_salida_real IS NULL)
            OR
            (estado = 'Finalizada'
                AND fecha_hora_salida_real IS NOT NULL)
            OR
            (estado = 'Cancelada')
        ),

    CONSTRAINT FK_Hospitalizacion_Paciente
        FOREIGN KEY (id_paciente)
        REFERENCES dbo.Paciente(id_paciente),

    CONSTRAINT FK_Hospitalizacion_Cama
        FOREIGN KEY (id_cama)
        REFERENCES dbo.Cama(id_cama)
);

-- Una cama solo puede tener una hospitalizacion activa.
CREATE UNIQUE NONCLUSTERED INDEX
    UX_Hospitalizacion_Cama_Activa
ON dbo.Hospitalizacion(id_cama)
WHERE estado = 'Activa';

-- =====================================================
-- 13. TABLA: INSUMO
-- =====================================================

CREATE TABLE dbo.Insumo
(
    id_insumo INT IDENTITY(1,1) NOT NULL,
    codigo_insumo VARCHAR(40) NOT NULL,
    nombre_insumo VARCHAR(150) NOT NULL,
    tipo_insumo VARCHAR(80) NOT NULL,
    stock_existencia DECIMAL(12,2) NOT NULL
        CONSTRAINT DF_Insumo_Stock DEFAULT (0),
    stock_maximo DECIMAL(12,2) NOT NULL,
    costo_unitario DECIMAL(12,2) NOT NULL,
    id_proveedor INT NOT NULL,

    CONSTRAINT PK_Insumo
        PRIMARY KEY CLUSTERED (id_insumo),

    CONSTRAINT UQ_Insumo_Codigo
        UNIQUE (codigo_insumo),

    CONSTRAINT CK_Insumo_Stock
        CHECK (
            stock_existencia >= 0
            AND stock_maximo > 0
            AND stock_existencia <= stock_maximo
        ),

    CONSTRAINT CK_Insumo_Costo
        CHECK (costo_unitario >= 0),

    CONSTRAINT FK_Insumo_Proveedor
        FOREIGN KEY (id_proveedor)
        REFERENCES dbo.Proveedor(id_proveedor)
);

-- =====================================================
-- 14. RESUMEN DE VALIDACION
-- =====================================================

SELECT
    TABLE_SCHEMA AS Esquema,
    TABLE_NAME AS Tabla
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_TYPE = 'BASE TABLE'
  AND TABLE_SCHEMA = 'dbo'
ORDER BY TABLE_NAME;

PRINT 'Proceso de creacion de tablas finalizado.';
GO

/* =====================================================
   15. TABLAS NUEVAS (segun "Tablas proyecto pro.xlsx" / "Tabla pisada.xlsx")
   -----------------------------------------------------
   Estas tablas provienen del diseno del Excel y se
   agregan SOLO si no existen (comparacion por nombre).

   Omitidas porque YA existen con el mismo nombre:
     TURNO, ESPECIALIDAD, PACIENTE, SALA, CAMA,
     HOSPITALIZACION, CITA, PROVEEDOR

   Eliminadas por duplicar tablas originales (regla del
   usuario: "que sean las mismas que las tablas originales"):
     PERSONAL          ~ Empleado
     SUMINISTRO        ~ Insumo
     MEDICO_REFERENTE  ~ MedicoExterno
     CONTACTO_EMERGENCIA ~ FamiliarResponsable
     ESTADO_CITA, ESTADO_HOSPITALIZACION
                      ~ estados hoy en CHECK de Cita/Hospitalizacion

   Por eso ADMISION apunta ahora a dbo.MedicoExterno y
   MOVIMIENTO_INVENTARIO a dbo.Insumo (antes apuntaban a
   MEDICO_REFERENTE y SUMINISTRO, que ya no existen).

   Tabla agregada en la revision "Tabla pisada.xlsx":
     AsigContEm (Asignacion Contacto Emergencia)
       -> dbo.ASIGNACION_CONTACTO_EMERGENCIA
     En el Excel apunta a CONTACTO_EMERGENCIA (IdContacto);
     como esa tabla se unifico con FamiliarResponsable, la
     llave foranea se adapto a dbo.FamiliarResponsable.

   Nota: se conservan los nombres y columnas del Excel.
   Las llaves foraneas hacia tablas ya existentes usan
   sus nombres reales (ej. Paciente.id_paciente).
   ===================================================== */

-- ------------------------- PUESTO -------------------------
IF OBJECT_ID(N'dbo.PUESTO', N'U') IS NULL
CREATE TABLE dbo.PUESTO
(
    IdPuesto      INT IDENTITY(1,1) NOT NULL,
    NombrePuesto  VARCHAR(100) NOT NULL,

    CONSTRAINT PK_PUESTO PRIMARY KEY CLUSTERED (IdPuesto),
    CONSTRAINT UQ_PUESTO_Nombre UNIQUE (NombrePuesto)
);

-- ----------------------- PARENTESCO -----------------------
IF OBJECT_ID(N'dbo.PARENTESCO', N'U') IS NULL
CREATE TABLE dbo.PARENTESCO
(
    IdParentesco      INT IDENTITY(1,1) NOT NULL,
    NombreParentesco  VARCHAR(50) NOT NULL,

    CONSTRAINT PK_PARENTESCO PRIMARY KEY CLUSTERED (IdParentesco),
    CONSTRAINT UQ_PARENTESCO_Nombre UNIQUE (NombreParentesco)
);

-- --------------------- CENTRO_MEDICO ----------------------
IF OBJECT_ID(N'dbo.CENTRO_MEDICO', N'U') IS NULL
CREATE TABLE dbo.CENTRO_MEDICO
(
    IdCentroMedico      INT IDENTITY(1,1) NOT NULL,
    NombreCentroMedico  VARCHAR(150) NOT NULL,

    CONSTRAINT PK_CENTRO_MEDICO PRIMARY KEY CLUSTERED (IdCentroMedico),
    CONSTRAINT UQ_CENTRO_MEDICO_Nombre UNIQUE (NombreCentroMedico)
);

-- ------------------------ TIPO_SALA -----------------------
IF OBJECT_ID(N'dbo.TIPO_SALA', N'U') IS NULL
CREATE TABLE dbo.TIPO_SALA
(
    IdTipoSala      INT IDENTITY(1,1) NOT NULL,
    NombreTipoSala  VARCHAR(100) NOT NULL,

    CONSTRAINT PK_TIPO_SALA PRIMARY KEY CLUSTERED (IdTipoSala),
    CONSTRAINT UQ_TIPO_SALA_Nombre UNIQUE (NombreTipoSala)
);

-- ---------------------- TIPO_MOVIMIENTO (siguiente) --------
-- (Se eliminaron aqui ESTADO_HOSPITALIZACION y ESTADO_CITA:
--  son duplicados de los CHECK de Hospitalizacion y Cita.)
IF OBJECT_ID(N'dbo.TIPO_MOVIMIENTO', N'U') IS NULL
CREATE TABLE dbo.TIPO_MOVIMIENTO
(
    IdTipoMovimiento      INT IDENTITY(1,1) NOT NULL,
    NombreTipoMovimiento  VARCHAR(50) NOT NULL,

    CONSTRAINT PK_TIPO_MOVIMIENTO PRIMARY KEY CLUSTERED (IdTipoMovimiento),
    CONSTRAINT UQ_TIPO_MOVIMIENTO_Nombre UNIQUE (NombreTipoMovimiento)
);

-- ------------------------- TELEFONO -----------------------
-- Referencia polimorfica (TipoEntidad + IdEntidad); sin FK.
IF OBJECT_ID(N'dbo.TELEFONO', N'U') IS NULL
CREATE TABLE dbo.TELEFONO
(
    IdTelefono      INT IDENTITY(1,1) NOT NULL,
    TipoEntidad     VARCHAR(30) NOT NULL,
    IdEntidad       INT NOT NULL,
    NumeroTelefono  VARCHAR(25) NOT NULL,
    TipoTelefono    VARCHAR(30) NULL,

    CONSTRAINT PK_TELEFONO PRIMARY KEY CLUSTERED (IdTelefono)
);

-- ------------------------ DIRECCION -----------------------
-- Referencia polimorfica (TipoEntidad); sin FK.
IF OBJECT_ID(N'dbo.DIRECCION', N'U') IS NULL
CREATE TABLE dbo.DIRECCION
(
    IdDireccion        INT IDENTITY(1,1) NOT NULL,
    TipoEntidad        VARCHAR(30) NOT NULL,
    DireccionCompleta  VARCHAR(250) NOT NULL,
    Zona               VARCHAR(50) NULL,
    Municipio          VARCHAR(100) NULL,
    Departamento       VARCHAR(100) NULL,
    Pais               VARCHAR(100) NULL,
    TipoDireccion      VARCHAR(30) NULL,
    EsPrincipal        BIT NOT NULL
        CONSTRAINT DF_DIRECCION_EsPrincipal DEFAULT (0),

    CONSTRAINT PK_DIRECCION PRIMARY KEY CLUSTERED (IdDireccion)
);

-- (Se eliminaron aqui PERSONAL, CONTACTO_EMERGENCIA y
--  MEDICO_REFERENTE: duplican a Empleado, FamiliarResponsable
--  y MedicoExterno respectivamente. Ver cabecera de la seccion.)

-- ------------------------ ADMISION ------------------------
-- Antes referenciaba a MEDICO_REFERENTE (eliminada); ahora
-- usa la tabla original dbo.MedicoExterno.
IF OBJECT_ID(N'dbo.ADMISION', N'U') IS NULL
CREATE TABLE dbo.ADMISION
(
    IdAdmision         INT IDENTITY(1,1) NOT NULL,
    IdPaciente         INT NOT NULL,
    IdMedicoExterno    INT NULL,
    FechaRegistro      DATETIME2(0) NOT NULL
        CONSTRAINT DF_ADMISION_FechaRegistro DEFAULT (SYSDATETIME()),

    CONSTRAINT PK_ADMISION PRIMARY KEY CLUSTERED (IdAdmision),

    CONSTRAINT FK_ADMISION_Paciente
        FOREIGN KEY (IdPaciente) REFERENCES dbo.Paciente(id_paciente),
    CONSTRAINT FK_ADMISION_MedicoExterno
        FOREIGN KEY (IdMedicoExterno) REFERENCES dbo.MedicoExterno(id_medico_externo)
);

-- (Se elimino aqui SUMINISTRO: duplica a Insumo.
--  Ver cabecera de la seccion.)

-- ------------------ MOVIMIENTO_INVENTARIO -----------------
-- Antes referenciaba a SUMINISTRO (eliminada); ahora
-- usa la tabla original dbo.Insumo.
IF OBJECT_ID(N'dbo.MOVIMIENTO_INVENTARIO', N'U') IS NULL
CREATE TABLE dbo.MOVIMIENTO_INVENTARIO
(
    IdMovimiento      INT IDENTITY(1,1) NOT NULL,
    IdInsumo          INT NOT NULL,
    FechaHora         DATETIME2(0) NOT NULL
        CONSTRAINT DF_MOVIMIENTO_FechaHora DEFAULT (SYSDATETIME()),
    IdTipoMovimiento  INT NOT NULL,
    Cantidad          DECIMAL(12,2) NOT NULL,
    CostoUnitario     DECIMAL(12,2) NOT NULL
        CONSTRAINT DF_MOVIMIENTO_Costo DEFAULT (0),
    Observacion       VARCHAR(300) NULL,

    CONSTRAINT PK_MOVIMIENTO_INVENTARIO PRIMARY KEY CLUSTERED (IdMovimiento),
    CONSTRAINT CK_MOVIMIENTO_Cantidad CHECK (Cantidad > 0),
    CONSTRAINT CK_MOVIMIENTO_Costo CHECK (CostoUnitario >= 0),

    CONSTRAINT FK_MOVIMIENTO_Insumo
        FOREIGN KEY (IdInsumo) REFERENCES dbo.Insumo(id_insumo),
    CONSTRAINT FK_MOVIMIENTO_TipoMovimiento
        FOREIGN KEY (IdTipoMovimiento) REFERENCES dbo.TIPO_MOVIMIENTO(IdTipoMovimiento)
);

-- ------------------- REGISTRO_TELEMETRIA ------------------
IF OBJECT_ID(N'dbo.REGISTRO_TELEMETRIA', N'U') IS NULL
CREATE TABLE dbo.REGISTRO_TELEMETRIA
(
    IdRegistro          INT IDENTITY(1,1) NOT NULL,
    IdPaciente          INT NOT NULL,
    MarcaTiempo         DATETIME2(0) NOT NULL
        CONSTRAINT DF_TELEMETRIA_MarcaTiempo DEFAULT (SYSDATETIME()),
    FrecuenciaCardiaca  INT NULL,
    SaturacionOxigeno   DECIMAL(5,2) NULL,
    AlertaGenerada      BIT NOT NULL
        CONSTRAINT DF_TELEMETRIA_Alerta DEFAULT (0),

    CONSTRAINT PK_REGISTRO_TELEMETRIA PRIMARY KEY CLUSTERED (IdRegistro),

    CONSTRAINT FK_REGISTRO_TELEMETRIA_Paciente
        FOREIGN KEY (IdPaciente) REFERENCES dbo.Paciente(id_paciente)
);

-- ------------- ASIGNACION_CONTACTO_EMERGENCIA --------------
-- Origen: "AsigContEm" en "Tabla pisada.xlsx".
-- Une un paciente con sus contactos de emergencia (FamiliarResponsable)
-- e indica el parentesco de cada contacto.
IF OBJECT_ID(N'dbo.ASIGNACION_CONTACTO_EMERGENCIA', N'U') IS NULL
CREATE TABLE dbo.ASIGNACION_CONTACTO_EMERGENCIA
(
    IdAsignacion  INT IDENTITY(1,1) NOT NULL,
    IdPaciente    INT NOT NULL,
    IdFamiliar    INT NOT NULL,
    IdParentesco  INT NOT NULL,

    CONSTRAINT PK_ASIGNACION_CONTACTO_EMERGENCIA
        PRIMARY KEY CLUSTERED (IdAsignacion),
    CONSTRAINT UQ_ASIGNACION_CONTACTO
        UNIQUE (IdPaciente, IdFamiliar),

    CONSTRAINT FK_ASIGNACION_CONTACTO_Paciente
        FOREIGN KEY (IdPaciente) REFERENCES dbo.Paciente(id_paciente),
    CONSTRAINT FK_ASIGNACION_CONTACTO_Familiar
        FOREIGN KEY (IdFamiliar) REFERENCES dbo.FamiliarResponsable(id_familiar),
    CONSTRAINT FK_ASIGNACION_CONTACTO_Parentesco
        FOREIGN KEY (IdParentesco) REFERENCES dbo.PARENTESCO(IdParentesco)
);
GO

-- =====================================================
-- 16. RESUMEN FINAL DE TABLAS
-- =====================================================
SELECT
    TABLE_SCHEMA AS Esquema,
    TABLE_NAME AS Tabla
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_TYPE = 'BASE TABLE'
  AND TABLE_SCHEMA = 'dbo'
ORDER BY TABLE_NAME;
GO

