from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from typing import List

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modelos basados en las fichas proporcionadas
class TiempoResolucion(BaseModel):
    codigo: str
    fecha_apertura: str
    fecha_cierre: str
    tiempo_cierre: float # En horas o minutos
    
class IncidenciasResueltas(BaseModel):
    dia: str
    incidencias_resueltas: int
    
class CumplimientosSLA(BaseModel):
    dia: str
    resueltas_sla: int
    total_incidencias: int
    
# Bases de datos en memoria para el ejemplo
db_tiempo = []
db_incidencias = []
db_sla = []

# Endpoint - Tiempo Promedio de Resolucion [cite: 1]
@app.post("/api/tiempo")
def add_tiempo(data: TiempoResolucion):
    db_tiempo.append(data)
    return {"message": "Registrado", "data": data}

@app.get("/api/tiempo", response_model=List[TiempoResolucion])
def get_tiempo():
    return db_tiempo

# Endpoints - Numero de Incidencias Resueltas [cite: 2]
@app.post("/api/incidencias")
def add_incidencias (data: IncidenciasResueltas):
    db_incidencias.append(data)
    return {"message": "Registrado", "data": data}

@app.get("/api/incidencias", response_model=List[IncidenciasResueltas])
def get_incidencias():
    return db_incidencias

# Endpoints - Cumplimiento SLA
@app.post("/api/sla")
def add_sla(data: CumplimientosSLA):
    db_sla.append(data)
    return {"message": "Registrado", "data": data}

@app.get("/api/sla")
def get_sla():
    # Calculamos el porcentaje antes de devolver[cite: 3]
    resultado = []
    for item in db_sla:
        porcentaje = (item.resueltas_sla / item.total_incidencias) * 100 if item.total_incidencias > 0 else 0
        resultado.append({
            "dia": item.dia,
            "resueltas_sla": item.resueltas_sla,
            "total_incidencias": item.total_incidencias,
            "porcentaje": round(porcentaje, 2)
        })
    return resultado