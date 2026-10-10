-- Recuperación del corte histórico seleccionado en PostgreSQL 15 de este equipo.
-- psql debe recibir expected_database y expected_oid, verificados antes del cambio.
-- Las variables omitidas provocan error con ON_ERROR_STOP; no contiene credenciales.
\set ON_ERROR_STOP on
SELECT set_config('codex.expected_database', :'expected_database', false),
       set_config('codex.expected_oid', :'expected_oid', false);

DO $guard$
BEGIN
    IF current_database() <> current_setting('codex.expected_database')
       OR inet_server_port() <> 5432
       OR current_user <> 'plataforma_operacion'
       OR (SELECT oid::text FROM pg_database WHERE datname=current_database())
          <> current_setting('codex.expected_oid')
       OR NOT COALESCE((SELECT version_num IN ('d2804c8b39a1','f4826b9d1c30') FROM alembic_version),false)
       OR EXISTS (SELECT 1 FROM pg_roles WHERE rolname=current_user
                  AND (rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication))
    THEN
        RAISE EXCEPTION 'La identidad, revisión o permisos del destino no coinciden';
    END IF;
END
$guard$;

DO $locale$
DECLARE
    desired_oid oid;
    db_locale record;
    declared_locale record;
    tbl record;
    column_count integer;
    changes text;
    heap_before oid;
    heap_after oid;
    altered integer := 0;
BEGIN
    SELECT pg_encoding_to_char(encoding) AS encoding,datlocprovider,datcollate,datctype
      INTO db_locale FROM pg_database WHERE datname=current_database();
    IF db_locale.encoding <> 'UTF8' OR db_locale.datlocprovider <> 'c' THEN
        RAISE EXCEPTION 'Este procedimiento requiere UTF8 y el proveedor libc del corte';
    END IF;
    IF db_locale.datcollate='Spanish_Argentina.1252'
       AND db_locale.datctype='Spanish_Argentina.1252' THEN
        RAISE NOTICE 'La base ya conserva el locale de origen; sin cambios';
        RETURN;
    END IF;
    SELECT count(*) INTO column_count
      FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid
      JOIN pg_namespace n ON n.oid=c.relnamespace
     WHERE n.nspname='public' AND c.relkind='r' AND a.attnum>0
       AND NOT a.attisdropped AND a.attcollation<>0;
    IF column_count <> 102 THEN
        RAISE EXCEPTION 'La estructura de texto difiere de las 102 columnas verificadas';
    END IF;
    SELECT co.oid INTO desired_oid FROM pg_collation co
      JOIN pg_namespace n ON n.oid=co.collnamespace
     WHERE n.nspname='public' AND co.collname='secop_source_locale';
    IF desired_oid IS NULL THEN
        CREATE COLLATION public.secop_source_locale
          (provider=libc,lc_collate='Spanish_Argentina.1252',lc_ctype='Spanish_Argentina.1252');
        SELECT 'public.secop_source_locale'::regcollation::oid INTO desired_oid;
    END IF;
    SELECT collprovider,collcollate,collctype INTO declared_locale
      FROM pg_collation WHERE oid=desired_oid;
    IF declared_locale.collprovider<>'c'
       OR declared_locale.collcollate<>'Spanish_Argentina.1252'
       OR declared_locale.collctype<>'Spanish_Argentina.1252' THEN
        RAISE EXCEPTION 'La colación existente no coincide con el origen';
    END IF;
    -- Cada tabla se altera una vez; las columnas ya reconciliadas se omiten.
    FOR tbl IN
        SELECT c.oid,c.relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
         WHERE n.nspname='public' AND c.relkind='r'
         ORDER BY CASE c.relname WHEN 'contratos_procesados' THEN 0
                      WHEN 'raw_secop' THEN 2 ELSE 1 END,c.relname
    LOOP
        SELECT string_agg(format('ALTER COLUMN %I TYPE %s COLLATE public.secop_source_locale',
                               a.attname,format_type(a.atttypid,a.atttypmod)),', ' ORDER BY a.attnum)
          INTO changes FROM pg_attribute a
         WHERE a.attrelid=tbl.oid AND a.attnum>0 AND NOT a.attisdropped
           AND a.attcollation<>0 AND a.attcollation<>desired_oid;
        IF changes IS NULL THEN CONTINUE; END IF;
        IF EXISTS (SELECT 1 FROM pg_attribute a WHERE a.attrelid=tbl.oid
                    AND a.attnum>0 AND NOT a.attisdropped AND a.attcollation<>0
                    AND format_type(a.atttypid,a.atttypmod)
                        !~ '^(text|character varying(\([0-9]+\))?|character(\([0-9]+\))?)$') THEN
            RAISE EXCEPTION 'Tipo de texto no ensayado en %',tbl.relname;
        END IF;
        SELECT relfilenode INTO heap_before FROM pg_class WHERE oid=tbl.oid;
        EXECUTE format('ALTER TABLE public.%I %s',tbl.relname,changes);
        SELECT relfilenode INTO heap_after FROM pg_class WHERE oid=tbl.oid;
        IF heap_after <> heap_before THEN
            RAISE EXCEPTION 'La operación intentó reescribir datos en %; se revierte',tbl.relname;
        END IF;
        altered := altered+1;
    END LOOP;
    IF EXISTS (SELECT 1 FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid
                JOIN pg_namespace n ON n.oid=c.relnamespace
               WHERE n.nspname='public' AND c.relkind='r' AND a.attnum>0
                 AND NOT a.attisdropped AND a.attcollation<>0
                 AND a.attcollation<>desired_oid) THEN
        RAISE EXCEPTION 'Quedan columnas sin reconciliar';
    END IF;
    RAISE NOTICE 'Locale de las 102 columnas verificado; tablas alteradas: %',altered;
END
$locale$;
