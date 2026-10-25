/*
    Proyecto: Hospital W 2.0
    Archivo:  Migracion_AsigContEm.sql
    Motor:    Microsoft SQL Server

    Agrega la tabla nueva de la revision "Tabla pisada.xlsx":
      AsigContEm -> dbo.ASIGNACION_CONTACTO_EMERGENCIA

    Une pacientes con sus contactos de emergencia (FamiliarResponsable)
    indicando el parentesco. Es idempotente: se puede ejecutar varias veces.
*/
USE HospitalW2;
GO

SET NOCOUNT ON;
GO

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

IF NOT EXISTS (SELECT 1 FROM dbo.ASIGNACION_CONTACTO_EMERGENCIA)
BEGIN
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
END
GO

SELECT COUNT(*) AS asignaciones FROM dbo.ASIGNACION_CONTACTO_EMERGENCIA;
GO
