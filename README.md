# Impulso Digital · Plataforma Digital y Portal del Cliente (Módulos 1 y 2)

- **Módulo 1:** Diagnóstico **gratuito** de madurez digital para Pymes (Puerto Boyacá) + CRM comercial interno.
- **Módulo 2:** Sistema de Gestión y Accesos (**SGA**) para el **Portal del Cliente** (Staging, aprobación de entregables, soporte posventa y capacitaciones).

```
impulso-digital/
├── backend/            FastAPI + SQLAlchemy 2 + PostgreSQL
│   ├── app/
│   │   ├── services/questionnaire.py   Banco de preguntas (versionado)
│   │   ├── services/maturity.py        Motor de madurez y recomendación de paquete
│   │   ├── routers/public.py           Diagnóstico público (sin login)
│   │   ├── routers/auth.py             Login JWT y usuarios (admin/comercial/cliente)
│   │   ├── routers/companies.py        CRM: empresas, pipeline, interacciones
│   │   ├── routers/dashboard.py        Métricas y export de dataset para ML
│   │   ├── routers/portal.py           Módulo 2: Portal del Cliente (SGA)
│   │   ├── models.py / schemas.py / security.py
│   │   └── seed.py                     Datos de demostración (Puerto Boyacá)
│   └── tests/                          38 pruebas automatizadas (pytest)
├── frontend/           React + Vite + TypeScript
└── docker-compose.yml  PostgreSQL 16 + API
```

## Accesos y Cuentas de Demostración

| Perfil | URL | Correo | Contraseña |
|---|---|---|---|
| 📝 **Pyme (Público)** | `http://localhost:5173/` | *Sin autenticación* | *Sin autenticación* |
| 🛡️ **Portal Cliente (SGA)** | `http://localhost:5173/portal/login` | `cliente@laespiga.co` | `Cliente123*` |
| 💼 **Asesor Comercial** | `http://localhost:5173/crm/login` | `asesor@impulsodigital.co` | `Asesor123*` |
| 👑 **Administrador** | `http://localhost:5173/crm/login` | `admin@impulsodigital.co` | `Admin123*` |

Sin `.env`, el sistema usa **SQLite** (`impulso_dev.db`) como respaldo para desarrollo.

### Con PostgreSQL (recomendado)
1. Instala [Docker Desktop](https://www.docker.com/products/docker-desktop/) **o** [PostgreSQL para Windows](https://www.postgresql.org/download/windows/).
2. Docker: `docker compose up -d db` (crea usuario/clave/base `impulso`).
3. En `.env`: `DATABASE_URL=postgresql+psycopg://impulso:impulso@localhost:5432/impulso`

## Ejecutar el frontend
Requiere [Node.js 20+](https://nodejs.org/).
```powershell
cd frontend
npm install
npm run dev        # http://localhost:5173  (proxy /api -> :8000)
```
- `/` → formulario público de diagnóstico
- `/crm` → CRM interno (login)

## Pruebas
```powershell
cd backend
.\.venv\Scripts\python -m pytest -q
```

## Lógica de evaluación
1. 12 preguntas en 6 dimensiones (0-4 puntos c/u) → puntaje por dimensión 0-100.
2. Puntaje total = promedio **ponderado por sector** (comercio prioriza e-commerce; manufactura, gestión).
3. Nivel: `<30` Inicial · `<55` En desarrollo · `<75` Intermedio · `≥75` Avanzado.
4. Paquete: Inicial → **Básico**, En desarrollo → **Integral**, Intermedio/Avanzado → **Premium**.
   Ajustes: ≥50 empleados nunca Básico; ≤5 empleados nunca Premium.
5. Top-3 recomendaciones según la brecha × importancia en el sector.

Todo es configurable en `services/maturity.py`. Los puntos **nunca** se envían al navegador.

## Seguridad y cumplimiento
- **Ley 1581 de 2012**: autorización obligatoria; se registra fecha, IP y versión de la política.
- Contraseñas con bcrypt; JWT con expiración; roles `admin` / `comercial`.
- Un comercial solo modifica empresas libres o asignadas a él; solo admin reasigna, crea usuarios y exporta datos.
- Export para ML **anonimizado** (sin nombres, correos, NIT).
- Historial de cambios auditable (interacciones tipo `sistema`).

## Preparado para Machine Learning
Cada diagnóstico guarda respuestas individuales, versión del cuestionario y la etiqueta
`converted` (se marca al pasar la empresa a **Ganado**). `GET /api/dashboard/export/ml-dataset.csv`
entrega el dataset listo para entrenar un modelo de predicción de conversión (meta: 24%).

## Próximos pasos sugeridos
- Migraciones con Alembic · rate-limiting en el endpoint público · notificación por email al asesor.
- Módulo 2: Portal del Cliente (SGA) · Módulo 3: SLA freelancers + QA.
