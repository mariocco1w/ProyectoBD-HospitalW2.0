/*
    Migracion incremental y reversible.
    Agrega una clave opcional para no aplicar dos veces el mismo movimiento
    de inventario cuando el navegador reintenta el envio.

    No modifica filas existentes: la columna nace NULL.
    El indice unico filtrado ignora los NULL, asi que los movimientos
    anteriores siguen siendo validos.

    Reversion:
        DROP INDEX UX_MOVIMIENTO_Idempotencia ON dbo.MOVIMIENTO_INVENTARIO;
        ALTER TABLE dbo.MOVIMIENTO_INVENTARIO DROP COLUMN ClaveIdempotencia;
*/
USE HospitalW2;
GO

IF COL_LENGTH(N'dbo.MOVIMIENTO_INVENTARIO', N'ClaveIdempotencia') IS NULL
BEGIN
    ALTER TABLE dbo.MOVIMIENTO_INVENTARIO
        ADD ClaveIdempotencia VARCHAR(64) NULL;
END
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = N'UX_MOVIMIENTO_Idempotencia'
      AND object_id = OBJECT_ID(N'dbo.MOVIMIENTO_INVENTARIO')
)
BEGIN
    CREATE UNIQUE NONCLUSTERED INDEX UX_MOVIMIENTO_Idempotencia
        ON dbo.MOVIMIENTO_INVENTARIO (ClaveIdempotencia)
        WHERE ClaveIdempotencia IS NOT NULL;
END
GO
