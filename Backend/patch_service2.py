import re

with open("modules/transformacion/services/trasformacionservice.py", "r", encoding="utf-8") as f:
    content = f.read()

new_method = """    def process_raw_data(self, forzar_reproceso: bool = False) -> Dict[str, Any]:
        \"\"\"
        Lee registros de raw_secop, detecta anomalías, normaliza y guarda
        en contratos_procesados. Nunca modifica raw_secop.
        \"\"\"
        inicio = datetime.now(timezone.utc)
        
        # Create Log
        log_entry = ProcesamientoLog(
            fecha_hora_inicio=inicio,
            estado="EN_PROCESO",
            forzar_reproceso=forzar_reproceso
        )
        self.session.add(log_entry)
        self.session.commit()
        
        chunk_size = 1000
        last_id = 0
        
        total_evaluados = 0
        procesados = 0
        omitidos = 0
        anomalias_totales = 0
        
        try:
            while True:
                # Build chunk query
                q = self.session.query(RawSecop).filter(RawSecop.id > last_id)
                
                if not forzar_reproceso:
                    q = q.outerjoin(ContratoProcesado, RawSecop.id == ContratoProcesado.raw_secop_id)\\
                         .filter(ContratoProcesado.id == None)
                         
                q = q.order_by(RawSecop.id.asc()).limit(chunk_size)
                raw_records = q.all()
                
                if not raw_records:
                    break
                    
                nuevas_anomalias = []
                
                for raw in raw_records:
                    total_evaluados += 1
                    
                    if raw.id > last_id:
                        last_id = raw.id
                        
                    # Normalizar
                    normalized = self._normalizar(raw)
                    data_hash = generate_hash(normalized)

                    anomalias_registro = self._detectar_anomalias(raw)
                    
                    campos_faltantes = [
                        a.campo_afectado for a in anomalias_registro 
                        if a.tipo_anomalia == "CAMPO_FALTANTE"
                    ]
                    tiene_monto_negativo = any(
                        a.tipo_anomalia == "MONTO_NEGATIVO" for a in anomalias_registro
                    )
                    tiene_fecha_futura = any(
                        a.tipo_anomalia == "FECHA_FUTURA" for a in anomalias_registro
                    )
                    
                    cantidad_faltantes = len(campos_faltantes)
                    es_incompleto = cantidad_faltantes > 0 or tiene_monto_negativo
                    es_sospechoso = tiene_fecha_futura
                    
                    nivel_confianza = 100
                    if cantidad_faltantes > 0:
                        nivel_confianza -= (cantidad_faltantes * 20)
                    if tiene_monto_negativo:
                        nivel_confianza -= 20
                    if es_sospechoso:
                        nivel_confianza -= 40
                        
                    nivel_confianza = max(0, min(100, nivel_confianza))

                    normalized["normalized_hash"] = data_hash
                    normalized["es_incompleto"] = es_incompleto
                    normalized["es_sospechoso"] = es_sospechoso
                    normalized["cantidad_campos_faltantes"] = cantidad_faltantes
                    normalized["campos_faltantes"] = campos_faltantes
                    normalized["nivel_confianza"] = nivel_confianza
                    
                    existente = self.repo.find_by_raw_secop_id(raw.id)
                    if existente:
                        if not forzar_reproceso:
                            omitidos += 1
                            continue
                            
                        if existente.normalized_hash == data_hash and existente.nivel_confianza == nivel_confianza and existente.es_incompleto == es_incompleto and existente.es_sospechoso == es_sospechoso:
                            omitidos += 1
                            continue
                            
                        # Actualizar el registro existente
                        for key, value in normalized.items():
                            setattr(existente, key, value)
                            
                        self.session.add(existente)
                        procesados += 1
                    else:
                        contrato = ContratoProcesado(**normalized)
                        self.session.add(contrato)
                        self.session.flush() # Flush to get ID
                        procesados += 1
                        
                        for anomalia in anomalias_registro:
                            anomalia.id_contrato_procesado = contrato.id
                        
                        nuevas_anomalias.extend(anomalias_registro)

                # Batch insert anomalias for this chunk
                if nuevas_anomalias:
                    self.repo.save_all_anomalias(nuevas_anomalias)
                    anomalias_totales += len(nuevas_anomalias)
                    self._actualizar_estadisticas(nuevas_anomalias)

                # Commit per chunk and update logs
                log_entry.total_evaluados = total_evaluados
                log_entry.procesados = procesados
                log_entry.omitidos = omitidos
                log_entry.anomalias_registradas = anomalias_totales
                log_entry.duracion_segundos = int((datetime.now(timezone.utc) - inicio).total_seconds())
                self.session.add(log_entry)
                self.session.commit()
                
                # Cleanup identity map to prevent memory leak
                for raw in raw_records:
                    self.session.expunge(raw)
                
            # Done with all chunks
            self.repo.recalculate_porcentajes_estadisticas_campos()
            self.session.commit()
            
            # Update Log success
            fin = datetime.now(timezone.utc)
            duracion = int((fin - inicio).total_seconds())
            
            log_entry.estado = "EXITOSO"
            log_entry.fecha_hora_fin = fin
            log_entry.duracion_segundos = duracion
            log_entry.total_evaluados = total_evaluados
            log_entry.procesados = procesados
            log_entry.omitidos = omitidos
            log_entry.anomalias_registradas = anomalias_totales
            
            self.session.add(log_entry)
            self.session.commit()

        except Exception as e:
            self.session.rollback()
            logger.error(f"Error en reprocesamiento: {e}", exc_info=True)
            
            fin = datetime.now(timezone.utc)
            duracion = int((fin - inicio).total_seconds())
            
            log_entry.estado = "ERROR"
            log_entry.fecha_hora_fin = fin
            log_entry.duracion_segundos = duracion
            log_entry.mensaje_error = str(e)
            
            self.session.add(log_entry)
            self.session.commit()
            
            raise e

        return {
            "total_evaluados": total_evaluados,
            "procesados": procesados,
            "omitidos": omitidos,
            "anomalias_registradas": anomalias_totales,
            "fecha_hora_inicio": inicio,
            "fecha_hora_fin": fin,
            "duracion_segundos": duracion,
            "estado": "EXITOSO"
        }"""

pattern = r"    def process_raw_data\(self, forzar_reproceso: bool = False\) -> Dict\[str, Any\]:.*?(?=    # ──────────────────────────────────────────────────────────────\n    # Detección de anomalías)"
content = re.sub(pattern, new_method + "\n\n", content, flags=re.DOTALL)

with open("modules/transformacion/services/trasformacionservice.py", "w", encoding="utf-8") as f:
    f.write(content)
