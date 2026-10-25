------verificacion dataframe

USE HospitalW2;
GO

-- 1. Estado general de la telemetría procesada
SELECT
    COUNT(*) AS TotalRegistros,
    COUNT(DISTINCT IdRegistroProcesado) AS IDsUnicos,
    COUNT(DISTINCT IdPaciente) AS Pacientes,
    MIN(MarcaTiempo) AS PrimeraMedicion,
    MAX(MarcaTiempo) AS UltimaMedicion
FROM dbo.RESULTADO_PROCESAMIENTO_TELEMETRIA;
GO

-- 2. Distribución por riesgo y condición sintética
SELECT
    Nivel_Riesgo,
    EsSintetico,
    COUNT(*) AS TotalRegistros
FROM dbo.RESULTADO_PROCESAMIENTO_TELEMETRIA
GROUP BY Nivel_Riesgo, EsSintetico
ORDER BY Nivel_Riesgo, EsSintetico;
GO

-- 3. Calidad de los datos procesados
SELECT
    SUM(CASE WHEN IdPaciente IS NULL THEN 1 ELSE 0 END)
        AS PacientesNulos,
    SUM(CASE WHEN MarcaTiempo IS NULL THEN 1 ELSE 0 END)
        AS FechasNulas,
    SUM(CASE WHEN FrecuenciaCardiaca IS NULL THEN 1 ELSE 0 END)
        AS FrecuenciasNulas,
    SUM(CASE WHEN SaturacionOxigeno IS NULL THEN 1 ELSE 0 END)
        AS SaturacionesNulas,
    SUM(CASE WHEN AlertaSpO2 = 1 THEN 1 ELSE 0 END)
        AS AlertasSpO2
FROM dbo.RESULTADO_PROCESAMIENTO_TELEMETRIA;
GO

-- 4. Verificar los resúmenes almacenados
SELECT
    COUNT(*) AS TotalPacientesResumidos,
    SUM(TotalRegistros) AS RegistrosContabilizados
FROM dbo.RESUMEN_RIESGO_PACIENTE;
GO
-------------------------------------------------

-- A. Pacientes con mayor cantidad de registros críticos
SELECT TOP (5)
    IdPaciente,
    TotalRegistros,
    RegistrosCriticos,
    RegistrosModerados,
    AlertasSpO2,
    RegistrosIncompletos
FROM dbo.RESUMEN_RIESGO_PACIENTE
ORDER BY RegistrosCriticos DESC, AlertasSpO2 DESC;
GO

-- B. Distribución porcentual de los niveles de riesgo
SELECT
    Nivel_Riesgo,
    COUNT(*) AS TotalRegistros,
    CAST(
        100.0 * COUNT(*) /
        NULLIF(
            (SELECT COUNT(*)
             FROM dbo.RESULTADO_PROCESAMIENTO_TELEMETRIA),
            0
        ) AS DECIMAL(6,2)
    ) AS Porcentaje
FROM dbo.RESULTADO_PROCESAMIENTO_TELEMETRIA
GROUP BY Nivel_Riesgo
ORDER BY TotalRegistros DESC;
GO

-- C. Alertas de saturación por paciente
SELECT
    IdPaciente,
    COUNT(*) AS TotalMediciones,
    SUM(CASE WHEN AlertaSpO2 = 1 THEN 1 ELSE 0 END)
        AS AlertasSpO2,
    MIN(SaturacionOxigeno) AS SaturacionMinima,
    AVG(SaturacionOxigeno) AS SaturacionPromedio
FROM dbo.RESULTADO_PROCESAMIENTO_TELEMETRIA
GROUP BY IdPaciente
ORDER BY AlertasSpO2 DESC;
GO
