
/*
    Proyecto: Hospital W 2.0
    Archivo: 04_Verificar_Integridad.sql
    Objetivo: Validar los datos insertados.
    Este script es de solo lectura.
*/

USE HospitalW2;
GO

-- 1. Contar registros por tabla
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

-- 2. Buscar citas asignadas a empleados que no son medicos
SELECT
    c.id_cita,
    p.nombre AS NombrePaciente,
    p.apellido AS ApellidoPaciente,
    e.nombre AS NombreEmpleado,
    e.apellido AS ApellidoEmpleado,
    e.rol
FROM dbo.Cita AS c
INNER JOIN dbo.Paciente AS p
    ON p.id_paciente = c.id_paciente
INNER JOIN dbo.Empleado AS e
    ON e.id_empleado = c.id_empleado
WHERE e.rol <> 'Medico';
GO

-- 3. Mostrar camas y su ocupacion actual
SELECT
    s.nombre_sala,
    ca.numero_cama,
    CASE
        WHEN h.id_hospitalizacion IS NOT NULL
            THEN 'Ocupada'
        ELSE 'Disponible'
    END AS EstadoCama,
    p.nombre AS NombrePaciente,
    p.apellido AS ApellidoPaciente
FROM dbo.Cama AS ca
INNER JOIN dbo.Sala AS s
    ON s.id_sala = ca.id_sala
LEFT JOIN dbo.Hospitalizacion AS h
    ON h.id_cama = ca.id_cama
   AND h.estado = 'Activa'
LEFT JOIN dbo.Paciente AS p
    ON p.id_paciente = h.id_paciente
ORDER BY s.nombre_sala, ca.numero_cama;
GO

-- 4. Buscar hospitalizaciones con datos incoherentes
SELECT *
FROM dbo.Hospitalizacion
WHERE
    (estado = 'Activa' AND fecha_hora_salida_real IS NOT NULL)
    OR
    (estado = 'Finalizada' AND fecha_hora_salida_real IS NULL)
    OR
    (fecha_hora_salida_real IS NOT NULL
     AND fecha_hora_salida_real < fecha_hora_ingreso);
GO

-- 5. Consultar inventario y detectar stock critico
SELECT
    i.codigo_insumo,
    i.nombre_insumo,
    i.stock_existencia,
    i.stock_maximo,
    CAST(i.stock_maximo * 0.15 AS DECIMAL(12,2))
        AS UmbralCritico,
    p.razon_social AS Proveedor,
    p.telefono AS TelefonoProveedor
FROM dbo.Insumo AS i
INNER JOIN dbo.Proveedor AS p
    ON p.id_proveedor = i.id_proveedor
WHERE i.stock_existencia < i.stock_maximo * 0.15
ORDER BY i.stock_existencia ASC;
GO

-- 6. Consultar historial de citas por paciente
SELECT
    p.id_paciente,
    p.nombre,
    p.apellido,
    c.fecha_hora_cita,
    c.estado,
    e.nombre AS NombreMedico,
    e.apellido AS ApellidoMedico
FROM dbo.Paciente AS p
INNER JOIN dbo.Cita AS c
    ON c.id_paciente = p.id_paciente
INNER JOIN dbo.Empleado AS e
    ON e.id_empleado = c.id_empleado
ORDER BY p.id_paciente, c.fecha_hora_cita DESC;
GO

-- 7. Revisar asignaciones de personal a salas
SELECT
    e.id_empleado,
    e.nombre,
    e.apellido,
    e.rol,
    s.nombre_sala,
    a.fecha_inicio,
    a.fecha_fin
FROM dbo.AsignacionPersonalSala AS a
INNER JOIN dbo.Empleado AS e
    ON e.id_empleado = a.id_empleado
INNER JOIN dbo.Sala AS s
    ON s.id_sala = a.id_sala
ORDER BY e.id_empleado, a.fecha_inicio DESC;
GO
