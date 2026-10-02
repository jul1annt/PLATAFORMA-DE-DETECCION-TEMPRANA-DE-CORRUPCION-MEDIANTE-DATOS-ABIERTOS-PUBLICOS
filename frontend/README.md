# 💻 Frontend - Panel de Control & Visualización

El frontend de la **Plataforma de Detección Temprana de Corrupción** es una interfaz web moderna, responsiva e interactiva estructurada con **React 19**, **TypeScript** y **Vite**. Ofrece tanto un portal público de auditoría ciudadana como un panel de administración seguro para supervisar la calidad de los datos abiertos y el procesamiento analítico de riesgos de contratación.

---

## 🎨 Características de Diseño y UI
*   **Visualización Dinámica:** Gráficos estadísticos e interactivos mediante **Recharts** para representar la distribución de presupuestos, calidad de los datos e incidencias.
*   **Estilos Limpios:** Implementación ágil y responsiva con **Tailwind CSS v4** y componentes intuitivos.
*   **Exportación Multiformato:** Reportes CSV, XLSX y PDF generados por el backend sobre el conjunto completo de resultados filtrados.
*   **Formularios Seguros:** Gestión ágil de entradas con validaciones tipadas robustas con **React Hook Form** y **Zod**.

---

## 📂 Mapa de Vistas y Páginas (`frontend/src/pages/`)

El frontend está estructurado en áreas públicas y de administración protegidas:

### 🌐 Vistas Públicas
*   **Inicio / Portada (`HomePage.tsx`):** Bienvenida a la plataforma y explicación general de los indicadores de corrupción.
*   **Dashboard Ciudadano (`PublicDashboard.tsx`):** Estadísticas generales, tendencias de contratación, y visualización global de riesgos y banderas rojas detectadas.
*   **Listado de Contratos Procesados (`PublicProcesados.tsx`):** Buscador de contratos públicos con filtros avanzados por entidad, contratista, rango de montos y nivel de riesgo.
*   **Ficha del Contrato (`PublicContratoDetalle.tsx`):** Detalle técnico de un contrato específico, historial de modificaciones y desglose gráfico de alertas e indicadores de riesgo.
*   **Tablero de Calidad (`DataQualityDashboard.tsx`):** Estadísticas del nivel de salud de la información ingerida (campos vacíos, anomalías de formato, etc.).

### 🔒 Vistas de Administración (Rutas Protegidas)
Ubicadas en `src/pages/admin/` y accesibles únicamente previo inicio de sesión (`AdminLogin.tsx`):
*   **Panel Administrativo (`AdminDashboard.tsx`):** Panel de control inicial con resumen de estado general de la plataforma.
*   **Administración Analítica (`AdminAnalitica.tsx`):** Parametrización y visualización avanzada de riesgos y umbrales para las banderas rojas.
*   **Control de Fuentes (`AdminFuentes.tsx` & `FuentesList.tsx`):** Alta de nuevas URLs/APIs de datos abiertos, edición de parámetros de conexión y pruebas de comunicación en tiempo real.
*   **Reprocesamiento Manual (`AdminReprocesamiento.tsx`):** Consola para gatillar de forma inmediata la extracción, transformación y recálculo analítico de datos de contratación.
*   **Registro de Sincronizaciones (`AdminSyncLogs.tsx`):** Historial técnico detallado del programador de tareas en segundo plano.

---

## 📋 Requisitos Previos

Antes de comenzar, asegúrate de tener instalado:
*   [Node.js](https://nodejs.org/) (Versión LTS recomendada, 18.x o superior).
*   Un gestor de paquetes como `npm` (incluido con Node.js), `yarn` o `pnpm`.

---

## ⚙️ Configuración de la API

El cliente HTTP usa `VITE_API_URL` como URL base del backend. Copia `.env.example` a `.env.local` y ajusta la URL para tu entorno:

```bash
cp .env.example .env.local
```

Por ejemplo, en desarrollo local puedes usar `http://localhost:8000`; en integración o producción, configura el origen HTTPS real de FastAPI. Vite incorpora esta variable en el bundle durante el build, por lo que debes compilar de nuevo al cambiar de entorno. No guardes secretos en variables `VITE_*`, ya que quedan visibles en el navegador.

## Contratos de API y tipos

`src/types/api.generated.ts` se deriva de `Backend/openapi.json`. Para regenerar el contrato y sus tipos desde la raíz del repositorio:

```bash
cd Backend
python scripts/export_openapi.py
cd ../tools/openapi-types
npm ci
npm run generate
```

`npm run check` en `tools/openapi-types` y CI comprueban que el esquema y los tipos generados estén sincronizados. Los DTOs consumidos por las páginas se enlazan a estos tipos, incluidos los montos decimales serializados como texto para preservar su precisión.

## 🚀 Guía de Instalación y Ejecución

Sigue estos pasos para levantar la interfaz localmente:

### 1. Navegar al directorio del Frontend
Abre tu terminal y colócate en la carpeta `frontend`:
```bash
cd frontend
```

### 2. Instalar Dependencias de Node
Instala todas las librerías necesarias del ecosistema React:
```bash
npm ci
```

### 3. Levantar el Servidor de Desarrollo
Inicia la aplicación en modo desarrollo local:
```bash
npm run dev
```
*   Por defecto, Vite iniciará la aplicación en la dirección: [http://localhost:5173](http://localhost:5173)
*   **Nota:** Asegúrate de que el Backend de FastAPI (puerto `8000`) esté encendido para que el frontend pueda consultar los datos correctamente.

### 4. Compilación para Producción (Build)
Para compilar la aplicación optimizada para entornos productivos:
```bash
npm run build
```
Los archivos optimizados resultantes se guardarán en la carpeta `frontend/dist/` listos para ser servidos por un servidor web (Nginx, Apache, Hosting Estático, etc.).
