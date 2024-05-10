CREATE TABLE "secop"."contratos_clean" WITH (table_type = 'ICEBERG', format='parquet', location='s3://raw-secop/contratos_clean/', is_external=false) AS (

WITH temp1 AS (


    SELECT
        id_unico,
        CASE
            WHEN nivel_entidad = 'TERRITORIAL' THEN 'Territorial'
            WHEN nivel_entidad = 'NACIONAL' THEN 'Nacional'
            ELSE nivel_entidad  -- Keep the original value if no match found
        END AS nivel_entidad,
        nombre_entidad,
        SUBSTRING(nit_entidad FROM 1 FOR 9) AS nit_entidad,
        CASE 
            WHEN departamento_entidad = 'Norte de Santander' THEN 'Norte De Santander'
            WHEN departamento_entidad = 'San Andrés Providencia y Santa Catalina' THEN 'San Andrés, Providencia y Santa Catalina'
            ELSE departamento_entidad
        END AS departamento_entidad,
        municipio_entidad,
        estado_proceso,
        modalidad_contratacion,
        objeto_contratar,
        CASE 
            WHEN tipo_contrato = 'Otro' THEN 'Otro Tipo de Contrato' 
            WHEN tipo_contrato =  'Prestación de servicios' THEN 'Prestación de Servicios'
            WHEN tipo_contrato = 'Suministros' THEN'Suministro'  
            ELSE tipo_contrato
        END AS tipo_contrato,
        fecha_firma_contrato,
        fecha_inicio_ejec_contrato,
        fecha_fin_ejec_contrato,
        id_contrato,
        id_proceso,
        CAST(valor_contrato AS double) AS valor_contrato,
        date_diff('day', fecha_inicio_ejec_contrato, fecha_fin_ejec_contrato) AS duracion_dias,
        date_diff('day', fecha_inicio_ejec_contrato, fecha_fin_ejec_contrato) / 30 AS duracion_meses,
        CASE 
            WHEN valor_contrato IS NOT NULL THEN (valor_contrato / 1000000)
            ELSE valor_contrato 
        END AS valor_contrato_millones,
        CAST(dias_adicionados_contrato AS double) AS dias_adicionados_contrato,
        CAST(monto_adicionado_contrato AS double) AS monto_adicionado_contrato,
        tipo_doc_proveedor,
        REGEXP_REPLACE(doc_proveedor, '[^0-9]', '') AS doc_proveedor,
        nombre_proveedor,
        es_grupo,
        es_pyme,
        tipo_doc_representante_legal,
        REGEXP_REPLACE(doc_representante_legal, '[^0-9]', '') AS doc_representante_legal,
        nombre_representante_legal,
        CASE 
            WHEN genero_representante_legal = '2' THEN 'Hombre'
            WHEN genero_representante_legal = '1' THEN 'Mujer'
            WHEN genero_representante_legal = 'N' THEN 'N/A'
            WHEN genero_representante_legal = '' THEN 'N/A'
            WHEN genero_representante_legal = '3' THEN 'Otro'
            WHEN genero_representante_legal = 'No Definido' THEN 'N/A'
            ELSE genero_representante_legal
        END AS genero_representante_legal,
        url_contrato,
        origen,
        date(ultima_actualizacion) AS ultima_actualizacion,
        codigo_proveedor

        


        
    FROM
        contratos


),

temp2 AS (

    SELECT 
        *,
        duracion_dias + dias_adicionados_contrato AS duracion_dias_final,
        CASE
            WHEN dias_adicionados_contrato > 0
                THEN DATE_ADD('day', CAST(dias_adicionados_contrato AS INTEGER), fecha_fin_ejec_contrato)
            ELSE
                fecha_fin_ejec_contrato
        END AS fecha_fin_ejec_contrato_final,
        CASE 
            WHEN 
                valor_contrato_millones IS NOT NULL AND
                valor_contrato_millones > 0 AND
                duracion_meses IS NOT NULL AND
                duracion_meses > 0
                    THEN valor_contrato_millones / duracion_meses
            ELSE NULL 
        END AS pago_por_mes


    FROM temp1
),

temp3 AS (

    SELECT
        *,
        CASE
            WHEN fecha_fin_ejec_contrato_final < current_date
                THEN 0
            ELSE
                1
        END AS esta_en_ejecucion

    FROM temp2

)

SELECT * FROM temp3

)
