# Sistema de Estimación de Épicas con ML

![CI](https://github.com/ABRAHAMCIMAT/PoC_Agente_Estimacion_Epicas/actions/workflows/ci.yml/badge.svg)
![CodeQL](https://github.com/ABRAHAMCIMAT/PoC_Agente_Estimacion_Epicas/actions/workflows/codeql.yml/badge.svg)

Sistema fullstack basado en Machine Learning para estimar automáticamente puntos de historia, duración, costo y esfuerzo de épicas/historias de usuario en proyectos Agile.

## 🎯 Características Principales

- **Agente multiagente local con Meta Llama servido por Ollama**:
  - Estimador ML, analista RAG, especialista de costos y revisor.
  - API OpenAI-compatible de Ollama; los datos permanecen en el equipo.
  - Servidor MCP para conversar y ejecutar acciones desde un cliente MCP como Jan.
- **RAG del template T-Shirt**: indexa todas las pestañas del Excel y conserva
  referencias de hoja/fila en las respuestas.
- **Roles editables**: altas y modificaciones de colaboradores y costo por hora.
- **Cuestionario y dashboard automáticos**: selecciona opciones del cuestionario,
  estima épicas y replica la estructura de la pestaña `Resultado`.
- **Exportación completa**: llena una copia del template conservando hojas,
  formato, fórmulas e imágenes.

- **Estimación Multi-objetivo**: Calcula 4 métricas simultáneamente:
  - Puntos de Historia (Story Points)
  - Duración estimada (días)
  - Costo (USD)
  - Esfuerzo (horas)

- **Modelos de Ensemble**: Utiliza combinación de:
  - Random Forest
  - Decision Tree
  - Promedio Ensemble (recomendado)

- **Métricas de Confiabilidad**: Muestra R² para indicar confianza en cada predicción
  - R² > 0.8: Alta confiabilidad (Verde)
  - R² 0.6-0.8: Confiabilidad media (Amarillo)
  - R² < 0.6: Baja confiabilidad (Rojo)

- **Interfaz en Español**: UI completamente localizada en español

- **Upload de Excel**: Sube archivos Excel con historias de usuario para procesamiento por lotes

- **Visualización Tabular**: Resultados en formato tabla con barras de progreso coloreadas

## 📋 Requisitos Previos

### Backend
- Python 3.12
- pip (gestor de paquetes Python)

### Frontend
- Node.js 16+ 
- npm o yarn

## 🚀 Instalación Rápida

### 1. Clonar Repositorio

```bash
git clone https://github.com/ABRAHAMCIMAT/PoC_Agente_Estimacion_Epicas.git
cd PoC_Agente_Estimacion_Epicas
```

### 2. Configurar Backend

```bash
cd backend

# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
# En Windows:
venv\Scripts\activate
# En macOS/Linux:
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar servidor
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

El backend estará disponible en `http://localhost:8000`

### 2.1 Configurar Ollama y Meta Llama

Instala Ollama, descarga el modelo y deja el servidor activo en el puerto `11434`:

```bash
ollama pull llama3.1:8b-instruct-q4_K_M
ollama serve
```

El backend lee las variables `LLM_API_URL`, `LLM_MODEL`, `LLM_API_KEY` y
`LLM_TIMEOUT` (ver `.env.example`; por defecto apuntan a Ollama local). El
backend no carga `.env` automáticamente: expórtalas en la terminal antes de
iniciar uvicorn. Las variables `JAN_*` anteriores se siguen aceptando.

Consulta [`jan/README.md`](jan/README.md) para usar las herramientas MCP desde
el chat de Jan.

### 3. Configurar Frontend

```bash
cd frontend

# Instalar dependencias
npm install

# Ejecutar servidor de desarrollo
npm run dev
```

El frontend estará disponible en `http://localhost:3000`

## 📁 Estructura del Proyecto

```
├── backend/
│   ├── app/
│   │   ├── main.py                 # Servidor FastAPI principal
│   │   └── dependencies.py         # Dependencias compartidas
│   ├── models/
│   │   └── epic_estimation_models.py # Modelos ML
│   ├── utils/
│   │   └── data_preprocessing.py   # Procesamiento de datos
│   ├── trained_models/
│   │   └── models.pkl              # Modelos entrenados
│   ├── training_data_improved.csv  # Dataset de entrenamiento
│   ├── requirements.txt            # Dependencias Python
│   └── retrain_models.py           # Script de reentrenamiento
│
├── frontend/
│   ├── pages/
│   │   └── index.jsx               # Página principal
│   ├── components/
│   │   ├── Header.jsx              # Encabezado
│   │   ├── ExcelUpload.jsx         # Carga de archivos
│   │   └── EstimationResults.jsx   # Resultados
│   ├── styles/
│   │   └── globals.css             # Estilos globales
│   ├── package.json
│   └── next.config.js
│
├── docs/
│   ├── ARQUITECTURA.md             # Descripción de arquitectura
│   ├── DEPLOYMENT.md               # Guía de despliegue
│   ├── API_DOCUMENTATION.md        # Documentación API REST
│   ├── CODIGO.md                   # Documentación de código
│   └── MEJORES_PRACTICAS.md        # Buenas prácticas
│
└── README.md
```

## 📚 Documentación Detallada

- **[ARQUITECTURA.md](docs/ARQUITECTURA.md)**: Descripción técnica de la arquitectura del sistema
- **[DEPLOYMENT.md](docs/DEPLOYMENT.md)**: Guía completa para desplegar en producción
- **[API_DOCUMENTATION.md](docs/API_DOCUMENTATION.md)**: Documentación de todos los endpoints REST
- **[CODIGO.md](docs/CODIGO.md)**: Documentación del código fuente
- **[MEJORES_PRACTICAS.md](docs/MEJORES_PRACTICAS.md)**: Guía de desarrollo y buenas prácticas
- **[CALIDAD_CODIGO.md](docs/CALIDAD_CODIGO.md)**: Dependabot, CodeQL, CI (lint/tests/coverage) y SonarQube local — cómo leer las métricas de madurez

## 🔧 Uso Básico

### Opción 1: Interfaz Web

1. Abrir http://localhost:3000
2. Cargar el template T-Shirt o usar el incluido.
3. Editar tarifas en **Roles y costos**.
4. Pulsar **Ejecutar multiagente**.
5. Revisar dashboard y respuestas del cuestionario.
6. Exportar el Excel completo o conversar desde un cliente MCP (por ejemplo, Jan).

### Opción 2: API REST

#### Entrenar Modelos
```bash
curl -X POST "http://localhost:8000/train" \
  -F "file=@backend/training_data_improved.csv"
```

#### Estimar Historia Individual
```bash
curl -X POST "http://localhost:8000/estimate/single" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Implementar login",
    "description": "Agregar autenticación con JWT",
    "acceptance_criteria": ["Sistema valida credenciales", "Token expira en 24h"],
    "priority": "high",
    "issue_type": "feature"
  }'
```

#### Obtener Estadísticas de Modelos
```bash
curl -X GET "http://localhost:8000/models/stats"
```

## 🧠 Características de ML

### Extracción de Features (10 características lingüísticas)

1. **Complejidad**: Palabras clave que indican complejidad
2. **Alcance**: Indicadores de alcance del proyecto
3. **Criterios**: Cantidad de criterios de aceptación
4. **Palabras técnicas**: Cantidad de términos técnicos
5. **Integración**: Indicadores de integración con otros sistemas
6. **Testing**: Requisitos de testing y QA
7. **Prioridad**: Codificación de nivel de prioridad
8. **Tipo**: Codificación de tipo de issue
9. **Números**: Cantidad de valores numéricos en descripción
10. **Variedad léxica**: Diversidad de vocabulario

### Modelos Entrenados

```
Dataset: 150 historias sintéticas diversas
Split: 80% entrenamiento, 20% validación

Resultados R²:
├── Story Points: 0.9876 (Excelente)
├── Esfuerzo: 0.9620 (Excelente)
├── Duración: 0.7537 (Bueno)
└── Costo: 0.7729 (Bueno)
```

## ⚙️ Configuración Avanzada

### Reentrenar Modelos

```bash
python retrain_models.py
```

### Variables de Entorno

Crear archivo `.env` en backend/:
```
FLASK_ENV=development
DEBUG=True
CORS_ORIGINS=http://localhost:3000,http://localhost:8000
```

## 🐛 Manejo de Errores

El sistema incluye manejo robusto de errores:

- **Validación de entrada**: Valida estructura de datos de entrada
- **Errores de predicción**: Captura y reporta errores en modelos
- **Archivos inválidos**: Maneja formatos Excel incorrectos
- **Timeout**: Procesa archivos grandes con timeout configurable
- **Logging**: Registra todos los errores para auditoría

Ver [MEJORES_PRACTICAS.md](docs/MEJORES_PRACTICAS.md#manejo-de-errores) para detalles.

## 📊 Ejemplo de Salida

```
Historia: "Implementar API de usuarios"

Estimaciones (Ensemble - Recomendado):
- Puntos de Historia: 8.5
- Duración: 4.2 días
- Costo: $1,450
- Esfuerzo: 145.3 horas

Confiabilidad R²:
- Puntos: 0.9876 (98.76%) [Verde - Alta]
- Duración: 0.7927 (79.27%) [Verde - Alta]
- Costo: 0.8089 (80.89%) [Verde - Alta]
- Esfuerzo: 0.9634 (96.34%) [Verde - Alta]
```

## 🔐 Seguridad

- Validación de entrada en todos los endpoints
- CORS configurado restrictivamente
- Sin almacenamiento de datos sensibles
- Conexión HTTPS recomendada en producción

## 📈 Performance

- Procesamiento batch de hasta 1000 historias
- Tiempo de respuesta < 100ms por historia
- Uso de caché para modelos entrenados
- Compresión de respuestas JSON

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor:

1. Fork el proyecto
2. Crea rama con tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a rama (`git push origin feature/AmazingFeature`)
5. Abre Pull Request

## 📄 Licencia

Este proyecto está bajo licencia MIT. Ver archivo `LICENSE` para detalles.

## 👥 Autores

- **Abraham** - Desarrollo inicial y dirección del proyecto

## 📞 Soporte

Para reportar bugs o sugerencias:
- Crear issue en GitHub
- Contactar al equipo de desarrollo

## 🙏 Agradecimientos

- Datos de entrenamiento basados en históricas de proyectos Agile reales
- Inspiración en metodologías de planificación Agile modernas
- Comunidad de Machine Learning open source

---

**Última actualización**: Agosto 2026
**Versión**: 1.0.0
