/*=======================================
Script de validacion de reglas del hospital
Objetivo: Verificacion de rechazos de camas ocupadas o duplicidad de datos
Creado por: Mario Renato Monroy Cortez
=========================================*/
USE HospitalW2;
GO

--COMPROBACION SI SE LE GARANTIZA AL PACIENTE UN MEDICO

CREATE OR ALTER TRIGGER dbo.TR_Cita_SoloMedicos
ON dbo.Cita
AFTER INSERT, UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    
    IF EXISTS(
        SELECT 1
        FROM inserted AS i
        INNER JOIN dbo.Empleado AS e ON e.id_empleado = i.id_empleado
        WHERE e.rol <> 'Medico'
    )
    BEGIN
        THROW 51001, 
              'Operacion Rechazada: una cita debe tener un empleado con rol Medico',
              1;
    END;
END;

--VERIFICACION NO EXISTEN DUPLICIDAD DE CAMAS
SELECT name AS NombreIndice, is_unique AS EsUnico, has_filter AS TieneFiltro,filter_definition AS CondicionFiltro
FROM sys.indexes 
WHERE object_id = OBJECT_ID('dbo.Hospitalizacion')
AND name = 'UX_Hospitalizacion_Cama_Activa';
--Busca camas con mas de una hospitalizacion
SELECT id_cama,
    COUNT(*) AS HospitalizacionesActivas
    FROM dbo.Hospitalizacion
    WHERE estado = 'Activa'
    GROUP BY id_cama
    HAVING COUNT (*) >1;
    GO

    --COMPROBACION DE REALIZACION DE CITAS INVALIDAS
    DECLARE @IdCita INT;
    DECLARE @IdEmpleadoNoMedico INT;

    SELECT TOP(1)
        @IdCita = id_cita
        FROM dbo.Cita
        ORDER BY id_cita;

    SELECT TOP(1)
    @IdEmpleadoNoMedico = id_empleado
    FROM dbo.Empleado
    WHERE rol <> 'Medico'
    ORDER BY id_empleado;

    IF @IdCita IS NULL
    BEGIN
        PRINT 'Prueba Omitida: no existen citas';
    END
    ELSE IF @IdEmpleadoNoMedico IS NULL
    BEGIN
        PRINT 'PRUEBA OMITIDA:no existe un empleado no medico';
    END
    ELSE
    BEGIN
        BEGIN TRY
            UPDATE dbo.Cita
            SET id_empleado = @IdEmpleadoNoMedico
            WHERE id_cita = @IdCita;

        PRINT 'ERROR: se permitio una cita con un empleado no medico';
        END TRY
        BEgin CATCH
        IF ERROR_NUMBER() = 51001
            PRINT 'PRUEBA CORRECTA'
        ELSE
            PRINT CONCAT(
                        'SE produjo otro error',
                          ERROR_MESSAGE()
                          );
                    END CATCH
                END;
        GO

--coMPROBACION RECHAZO SI CAMA ES UTILIZADA

DECLARE @IdHospitalizacion INT;
DECLARE @IdCamaOcupada INT;

SELECT TOP (1)
    @IdHospitalizacion = h2.id_hospitalizacion,
    @IdCamaOcupada = h1.id_cama
FROM dbo.Hospitalizacion AS h1
INNER JOIN dbo.Hospitalizacion AS h2
    ON h1.estado = 'Activa'
   AND h2.estado = 'Activa'
   AND h1.id_hospitalizacion <> h2.id_hospitalizacion
   AND h1.id_cama <> h2.id_cama
ORDER BY h1.id_hospitalizacion, h2.id_hospitalizacion;

IF @IdHospitalizacion IS NULL
BEGIN
    PRINT 'PRUEBA OMITIDA: no hay dos hospitalizaciones activas en camas diferentes.';
END
ELSE
BEGIN
    BEGIN TRY
        UPDATE dbo.Hospitalizacion
        SET id_cama = @IdCamaOcupada
        WHERE id_hospitalizacion = @IdHospitalizacion;

        PRINT 'ERROR: se permitio asignar una cama ocupada.';
    END TRY
    BEGIN CATCH
        IF ERROR_NUMBER() IN (2601, 2627)
            PRINT 'PRUEBA CORRECTA: el indice rechazo la cama duplicada.';
        ELSE
            PRINT CONCAT(
                'Se produjo otro error: ',
                ERROR_MESSAGE()
            );
    END CATCH;
END;
GO

--COMPROBACION FINAL; VERIFICACION LAS SITAS EXISTENTES SIGAN ASIGNADAS A MEDICOS Y QUE NO 
--EXISTAN CAMAS DUPLICADAS

--SE esperan 0 filas
SELECT c.id_cita, e.id_empleado, e.nombre,e.apellido,e.rol
FROM dbo.Cita AS c
INNER JOIN dbo.Empleado AS e
    ON e.id_empleado = c.id_empleado
    WHERE e.rol <> 'Medico';

SELECT id_cama, COUNT(*) AS TotalActivas
FROM dbo.Hospitalizacion
WHERE estado = 'Activa'
GROUP BY id_cama
HAVING COUNT(*) > 1;

--Confirmacion datos de pruebas sigan intactos
SELECT 'Cita' AS Tabla, COUNT(*) AS Total
FROM dbo.Cita
UNION ALL
SELECT 'Hospitalizacion', COUNT(*)
FROM dbo.Hospitalizacion;
Go

--================PROTECCION PARA CITAS===================================
CREATE OR ALTER TRIGGER dbo.TR_Empleado_ConCitas_Medico
ON dbo.Empleado
AFTER UPDATE
AS
BEGIN
SET NOCOUNT ON;
    IF EXISTS(
                SELECT 1
                FROM inserted AS i
                INNER JOIN dbo.Cita AS c
                    ON c.id_empleado = i.id_empleado 
                    WHERE i.rol <> 'Medico'
                    )
                    BEGIN
                    THROW 51002, 'Operacion rechazada: un empleado con citas asignadas debe conservar el rol Medico',
                    1;
                END;
            END;
            GO

