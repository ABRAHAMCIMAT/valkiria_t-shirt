# Documentación de Despliegue

## 📋 Tabla de Contenidos

1. [Despliegue Local](#despliegue-local)
2. [Despliegue en Desarrollo](#despliegue-en-desarrollo)
3. [Despliegue en Producción](#despliegue-en-producción)
4. [Docker](#docker)
5. [Solución de Problemas](#solución-de-problemas)

## 🏠 Despliegue Local

### Requisitos Previos
- Python 3.12
- Node.js 16+
- Git
- pip y npm
- Visual Studio Code (opcional)

### Paso 1: Clonar Repositorio

```bash
git clone https://github.com/ABRAHAMCIMAT/PoC_Agente_Estimacion_Epicas.git
cd PoC_Agente_Estimacion_Epicas
cd PoC_Agente_Estimacion_Epicas.worktrees/integrar-frontend-backend-excel-upload
```

### Paso 2: Configurar Backend

#### Windows:
```bash
cd backend

# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Entrenar modelos (si es necesario)
python retrain_models.py

# Ejecutar servidor
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### macOS/Linux:
```bash
cd backend

# Crear entorno virtual
python3 -m venv venv

# Activar entorno virtual
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Entrenar modelos
python retrain_models.py

# Ejecutar servidor
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Verificar Backend:**
```bash
curl http://localhost:8000/models/stats
# Debe retornar JSON con estadísticas del modelo
```

### Paso 3: Configurar Frontend

En otra terminal:
```bash
cd frontend

# Instalar dependencias
npm install

# Ejecutar en desarrollo
npm run dev

# La aplicación estará en http://localhost:3000
```

**Verificar Frontend:**
- Abrir navegador en http://localhost:3000
- Debería mostrar interfaz en español

### Paso 4: Verificar Funcionamiento

1. Ir a http://localhost:3000
2. Hacer clic en "Seleccionar archivo Excel"
3. Usar archivo de prueba: `backend/HU_test.xlsx` o `backend/training_data_improved.csv`
4. Ver resultados en tabla con estimaciones

## 🔧 Despliegue en Desarrollo

### Configuración de Variables de Entorno

Crear archivo `backend/.env`:
```env
# Flask
FLASK_ENV=development
DEBUG=True

# API
API_HOST=0.0.0.0
API_PORT=8000

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:8000,http://127.0.0.1:3000

# Logging
LOG_LEVEL=DEBUG
```

### Instalación de Herramientas de Desarrollo

```bash
# Backend - Herramientas de desarrollo
pip install -r requirements-dev.txt

# Incluye:
# - pytest (pruebas)
# - black (formateador)
# - pylint (linter)
# - mypy (verificación de tipos)

# Frontend - Herramientas de desarrollo
npm install --save-dev eslint prettier
```

### Ejecutar Pruebas

**Backend:**
```bash
cd backend
pytest tests/ -v --cov=app
```

**Frontend:**
```bash
cd frontend
npm run test
```

### Linting y Formateado

**Backend:**
```bash
# Verificar código
pylint app/

# Formatear
black app/ models/ utils/

# Verificar tipos
mypy app/
```

**Frontend:**
```bash
# Verificar código
npx eslint pages/ components/ styles/

# Formatear
npx prettier --write pages/ components/ styles/
```

## 🚀 Despliegue en Producción

### Checklist Pre-Producción

- [ ] Reentrenar modelos con datos reales
- [ ] Cambiar CORS_ORIGINS a dominios permitidos
- [ ] Configurar HTTPS/SSL
- [ ] Establecer variables de entorno seguras
- [ ] Hacer copia de seguridad de modelos
- [ ] Realizar pruebas de carga
- [ ] Documentar procedimiento de rollback

### Opción 1: Servidor Linux/Ubuntu

#### Backend

```bash
# Instalar dependencias del sistema
sudo apt-get update
sudo apt-get install python3.9 python3-pip python3-venv

# Clonar repositorio
cd /opt
sudo git clone https://github.com/ABRAHAMCIMAT/PoC_Agente_Estimacion_Epicas.git
cd PoC_Agente_Estimacion_Epicas/backend

# Crear entorno virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Instalar Gunicorn (servidor WSGI)
pip install gunicorn uvicorn

# Crear archivo de servicio
sudo nano /etc/systemd/system/epic-estimation-api.service
```

Contenido de `/etc/systemd/system/epic-estimation-api.service`:
```ini
[Unit]
Description=Epic Estimation API
After=network.target

[Service]
Type=notify
User=www-data
WorkingDirectory=/opt/PoC_Agente_Estimacion_Epicas/backend
Environment="PATH=/opt/PoC_Agente_Estimacion_Epicas/backend/venv/bin"
ExecStart=/opt/PoC_Agente_Estimacion_Epicas/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Habilitar y iniciar servicio
sudo systemctl daemon-reload
sudo systemctl enable epic-estimation-api
sudo systemctl start epic-estimation-api
sudo systemctl status epic-estimation-api
```

#### Frontend

```bash
# Instalar Node.js
curl -sL https://deb.nodesource.com/setup_16.x | sudo -E bash -
sudo apt-get install nodejs

# Clonar y configurar
cd /opt/PoC_Agente_Estimacion_Epicas/frontend
npm install
npm run build

# Instalar PM2 para administrar proceso
sudo npm install -g pm2

# Iniciar aplicación
pm2 start "npm run start" --name epic-estimation-frontend
pm2 save
pm2 startup
```

#### Configurar Nginx como Proxy Inverso

```bash
sudo nano /etc/nginx/sites-available/epic-estimation
```

Contenido:
```nginx
upstream backend {
    server localhost:8000;
}

upstream frontend {
    server localhost:3000;
}

server {
    listen 80;
    server_name estimacion.tudominio.com;

    # Frontend
    location / {
        proxy_pass http://frontend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # API
    location /api {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# Habilitar sitio
sudo ln -s /etc/nginx/sites-available/epic-estimation /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

#### HTTPS con Let's Encrypt

```bash
# Instalar Certbot
sudo apt-get install certbot python3-certbot-nginx

# Obtener certificado
sudo certbot --nginx -d estimacion.tudominio.com

# Renovación automática
sudo systemctl enable certbot.timer
```

### Opción 2: Docker

Ver sección [Docker](#docker) abajo.

### Opción 3: Heroku

#### Preparar Aplicación

```bash
# Crear archivo Procfile en raíz del repositorio
echo "web: cd backend && uvicorn app.main:app --host 0.0.0.0 --port \$PORT" > backend/Procfile
```

#### Desplegar

```bash
# Instalar Heroku CLI
# Seguir instrucciones en https://devcenter.heroku.com/articles/heroku-cli

# Crear aplicación
heroku create estimacion-epicas

# Configurar variables de entorno
heroku config:set FLASK_ENV=production

# Desplegar
git push heroku main

# Ver logs
heroku logs --tail
```

## 🐳 Docker

### Dockerfile Backend

Crear `backend/Dockerfile`:
```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Dockerfile Frontend

Crear `frontend/Dockerfile`:
```dockerfile
FROM node:16-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM node:16-alpine

WORKDIR /app

COPY --from=builder /app/next.config.js ./
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package*.json ./

EXPOSE 3000

CMD ["npm", "start"]
```

### docker-compose.yml

Crear `docker-compose.yml` en raíz:
```yaml
version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - FLASK_ENV=production
      - CORS_ORIGINS=http://localhost:3000
    volumes:
      - ./backend/trained_models:/app/trained_models
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/models/stats"]
      interval: 30s
      timeout: 10s
      retries: 3

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
    depends_on:
      - backend

  nginx:
    image: nginx:latest
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - backend
      - frontend
```

### Ejecutar con Docker Compose

```bash
# Construir imágenes
docker-compose build

# Iniciar servicios
docker-compose up -d

# Ver logs
docker-compose logs -f

# Detener
docker-compose down
```

## 🔍 Solución de Problemas

### Puerto 8000 ya en uso

```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux/macOS
lsof -i :8000
kill -9 <PID>
```

### Errores de dependencias Python

```bash
# Actualizar pip
pip install --upgrade pip

# Instalar versión exacta
pip install -r requirements.txt --force-reinstall

# Verificar versiones instaladas
pip list
```

### CORS bloqueado

Si ves error: "Access to XMLHttpRequest has been blocked by CORS policy"

Solución en `backend/app/main.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Cambiar según necesidad
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Modelos no entrenados

```bash
# Reentrenar
cd backend
python retrain_models.py

# Verificar
curl http://localhost:8000/models/stats
```

### Archivo Excel no se procesa

Verificar que el archivo tenga estas columnas:
- `Titulo`
- `Historia de Usuario`
- `Criterios de Aceptación`

Y usar formato .xlsx

### Memoria insuficiente en servidor

Para procesar archivos grandes:
```python
# En backend/app/main.py
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
BATCH_SIZE = 100  # Procesar en lotes
```

## 📊 Monitoreo en Producción

### Logs

```bash
# Backend
sudo journalctl -u epic-estimation-api -f

# Frontend (PM2)
pm2 logs epic-estimation-frontend
```

### Métricas

Implementar Prometheus + Grafana:

```bash
# Backend con Prometheus
pip install prometheus-client

# Exponer métricas
from prometheus_client import Counter, Histogram

estimations = Counter('estimations_total', 'Total estimations')
estimation_time = Histogram('estimation_duration_seconds', 'Estimation duration')
```

### Alertas

Configurar alertas para:
- Tiempo de respuesta > 1 segundo
- Tasa de error > 5%
- Uso de CPU > 80%
- Uso de memoria > 80%

## 🔄 Procedimiento de Actualización

```bash
# 1. Hacer backup
sudo cp -r /opt/epic-estimation /opt/epic-estimation.backup

# 2. Descargar cambios
cd /opt/epic-estimation
sudo git pull origin main

# 3. Instalar nuevas dependencias
cd backend
source venv/bin/activate
pip install -r requirements.txt

# 4. Reentrenar si es necesario
python retrain_models.py

# 5. Reiniciar servicios
sudo systemctl restart epic-estimation-api
pm2 restart epic-estimation-frontend

# 6. Verificar
curl http://localhost:8000/models/stats
```

## 🔐 Seguridad en Producción

1. **Usar HTTPS siempre**
2. **Configurar firewall**
   ```bash
   sudo ufw allow 22/tcp
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   sudo ufw enable
   ```

3. **Cambiar valores por defecto**
   - Cambiar puertos
   - Cambiar nombres de usuario
   - Usar contraseñas fuertes

4. **Hacer backup regularmente**
   ```bash
   # Backup automático diario
   sudo crontab -e
   # Agregar: 0 2 * * * /backup-script.sh
   ```

5. **Monitorear seguridad**
   ```bash
   sudo apt-get install aide
   sudo aideinit
   sudo aide --check
   ```

---

**Versión**: 1.0
**Última actualización**: Agosto 2026
