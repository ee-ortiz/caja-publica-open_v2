CREATE EXTERNAL TABLE IF NOT EXISTS `secop`.`contratos_secop_i` ( 
`id_unico` string, 
`nivel_entidad` string, 
`nombre_entidad` string, 
`nit_entidad` string, 
`departamento_entidad` string, 
`municipio_entidad` string, 
`estado_proceso` string, 
`modalidad_contratacion` string, 
`objeto_contratar` string, 
`tipo_contrato` string, 
`fecha_firma_contrato` date, 
`fecha_inicio_ejec_contrato` date, 
`fecha_fin_ejec_contrato` date, 
`id_contrato` string, 
`id_proceso` string, 
`valor_contrato` decimal(20, 2), 
`dias_adicionados_contrato` int, 
`monto_adicionado_contrato` decimal(20, 2), 
`tipo_doc_proveedor` string, 
`doc_proveedor` string, 
`nombre_proveedor` string, 
`es_grupo` string, 
`es_pyme` string, 
`tipo_doc_representante_legal` string, 
`doc_representante_legal` string, 
`nombre_representante_legal` string, 
`genero_representante_legal` string, 
`url_contrato` string, 
`ultima_actualizacion` timestamp, 
`codigo_proveedor` string,
`origen` string
)


ROW FORMAT SERDE 'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe'
STORED AS INPUTFORMAT 'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat' OUTPUTFORMAT 'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat'
LOCATION 's3://raw-secop/contratos-secop-i/'
TBLPROPERTIES ('classification' = 'parquet')