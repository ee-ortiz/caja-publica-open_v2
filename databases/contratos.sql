-- CREATE TABLE "secop"."contratos" WITH (table_type = 'ICEBERG', format='parquet', location='s3://raw-secop/contratos/', is_external=false) AS (
--     SELECT * FROM contratos_secop_ii
--     UNION ALL
--     SELECT * FROM contratos_secop_i
-- )

CREATE TABLE "secop"."contratos" WITH (format='parquet', external_location='s3://raw-secop/contratos/') AS (
    SELECT 

        id_unico, 
        nivel_entidad, 
        nombre_entidad, 
        nit_entidad, 
        departamento_entidad, 
        municipio_entidad, 
        estado_proceso, 
        modalidad_contratacion, 
        objeto_contratar, 
        tipo_contrato, 
        fecha_firma_contrato, 
        fecha_inicio_ejec_contrato, 
        fecha_fin_ejec_contrato, 
        id_contrato, 
        id_proceso, 
        valor_contrato, 
        dias_adicionados_contrato, 
        NULL AS monto_adicionado_contrato, 
        tipo_doc_proveedor, 
        doc_proveedor, 
        nombre_proveedor, 
        es_grupo, 
        es_pyme, 
        tipo_doc_representante_legal, 
        doc_representante_legal, 
        nombre_representante_legal, 
        genero_representante_legal, 
        url_contrato, 
        ultima_actualizacion, 
        codigo_proveedor,
        origen
    
    
    FROM contratos_secop_ii
    UNION ALL
    SELECT 

        id_unico, 
        nivel_entidad, 
        nombre_entidad, 
        nit_entidad, 
        departamento_entidad, 
        municipio_entidad, 
        estado_proceso, 
        modalidad_contratacion, 
        objeto_contratar, 
        tipo_contrato, 
        fecha_firma_contrato, 
        fecha_inicio_ejec_contrato, 
        fecha_fin_ejec_contrato, 
        id_contrato, 
        id_proceso, 
        valor_contrato, 
        dias_adicionados_contrato, 
        monto_adicionado_contrato, 
        tipo_doc_proveedor, 
        doc_proveedor, 
        nombre_proveedor, 
        NULL AS es_grupo, 
        NULL AS es_pyme, 
        tipo_doc_representante_legal, 
        doc_representante_legal, 
        nombre_representante_legal, 
        genero_representante_legal, 
        url_contrato, 
        ultima_actualizacion, 
        NULL AS codigo_proveedor,
        origen

     FROM contratos_secop_i
)