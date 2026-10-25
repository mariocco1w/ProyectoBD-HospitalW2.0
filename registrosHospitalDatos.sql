
USE HospitalW2;
GO

-- Tabla 1: resultados individuales del procesamiento PySpark
IF OBJECT_ID('dbo.RESULTADO_PROCESAMIENTO_TELEMETRIA', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.RESULTADO_PROCESAMIENTO_TELEMETRIA (
        IdRegistroProcesado INT NOT NULL PRIMARY KEY,
        IdPaciente INT NOT NULL,
        MarcaTiempo DATETIME2 NOT NULL,
        FrecuenciaCardiaca INT NULL,
        SaturacionOxigeno FLOAT NULL,
        AlertaGeneradaOriginal BIT NOT NULL,
        AlertaSpO2 BIT NULL,
        Nivel_Riesgo VARCHAR(20) NOT NULL,
        EsSintetico BIT NOT NULL,
        FechaProcesamiento DATETIME2 NOT NULL
            CONSTRAINT DF_ResultadoTelemetria_Fecha
            DEFAULT SYSDATETIME()
    );
END;
GO

-- Tabla 2: resumen analítico por paciente
IF OBJECT_ID('dbo.RESUMEN_RIESGO_PACIENTE', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.RESUMEN_RIESGO_PACIENTE (
        IdPaciente INT NOT NULL PRIMARY KEY,
        TotalRegistros INT NOT NULL,
        RegistrosCriticos INT NOT NULL,
        RegistrosModerados INT NOT NULL,
        AlertasSpO2 INT NOT NULL,
        RegistrosIncompletos INT NOT NULL,
        UltimaMedicion DATETIME2 NOT NULL,
        FechaProcesamiento DATETIME2 NOT NULL
            CONSTRAINT DF_ResumenRiesgo_Fecha
            DEFAULT SYSDATETIME()
    );
END;
GO

USE HospitalW2;
GO

SELECT
    OBJECT_ID('dbo.RESULTADO_PROCESAMIENTO_TELEMETRIA', 'U')
        AS TablaResultadosExiste,
    OBJECT_ID('dbo.RESUMEN_RIESGO_PACIENTE', 'U')
        AS TablaResumenExiste;



USE HospitalW2;
GO

SELECT
    'RESULTADO_PROCESAMIENTO_TELEMETRIA' AS Tabla,
    COUNT(*) AS TotalRegistros
FROM dbo.RESULTADO_PROCESAMIENTO_TELEMETRIA

UNION ALL

SELECT
    'RESUMEN_RIESGO_PACIENTE',
    COUNT(*)
FROM dbo.RESUMEN_RIESGO_PACIENTE;
GO


USE HospitalW2;
GO

SELECT
    COUNT(*) AS TotalRegistros,
    COUNT(DISTINCT IdRegistroProcesado) AS IDsUnicos,
    SUM(CASE WHEN EsSintetico = 0 THEN 1 ELSE 0 END)
        AS RegistrosOriginales,
    SUM(CASE WHEN EsSintetico = 1 THEN 1 ELSE 0 END)
        AS RegistrosSinteticos
FROM dbo.RESULTADO_PROCESAMIENTO_TELEMETRIA;

SELECT COUNT(*) AS TotalPacientesResumen
FROM dbo.RESUMEN_RIESGO_PACIENTE;

SELECT Nivel_Riesgo, COUNT(*) AS Total
FROM dbo.RESULTADO_PROCESAMIENTO_TELEMETRIA
GROUP BY Nivel_Riesgo
ORDER BY Nivel_Riesgo;
GO


-------------------------------------------

USE HospitalW2;
GO

SELECT COUNT(*) AS RegistrosActuales
FROM dbo.RESULTADO_PROCESAMIENTO_TELEMETRIA;

SELECT COUNT(*) AS ResumenesActuales
FROM dbo.RESUMEN_RIESGO_PACIENTE;
GO
