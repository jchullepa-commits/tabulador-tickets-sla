from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import pandas as pd
import io

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modelos de datos para las 3 fichas de registro
class TiempoResolucion(BaseModel):
    codigo: str
    fecha_apertura: str
    fecha_cierre: str
    tiempo_cierre: float # En horas o minutos
    
class IncidenciasResueltas(BaseModel):
    dia: str
    incidencias_resueltas: int
    
class CumplimientoSLA(BaseModel):
    dia: str
    resueltas_sla: int
    total_incidencias: int
    porcentaje: float
    
# Bases de datos en memoria para el ejemplo
db_tiempo = []
db_incidencias = []
db_sla = []

@app.get("/api/tiempo", response_model=List[TiempoResolucion])
def get_tiempo():
    return db_tiempo

@app.get("/api/incidencias", response_model=List[IncidenciasResueltas])
def get_incidencias():
    return db_incidencias

@app.get("/api/sla", response_model=List[CumplimientoSLA])
def get_sla():
    return db_sla

@app.post("/api/upload")
async def upload_excels(
    file: UploadFile = File(...),
    sla_file: UploadFile = File(...)
):

    #Leer archivos recibidos
    contents_tickets = await file.read()
    contents_sla = await sla_file.read()

    df_tickets = pd.read.excel(io.BytesIO(contents_tickets))
    df_sla = pd.read_excel=(io.BytesIO(contents_sla))

    #Limpiar registro previos
    db_tiempo.clear()
    db_incidencias.clear()
    db_sla.clear()

    #Limpiar y convertir fechas
    df_tickets = df_tickets.dropna(subset=['FechaHoraCierre', 'FechaHoraCreacion'])
    df_tickets['FechaHoraCreacion'] = pd.to_datetime(df_tickets['FechaHoraCreacion'])
    df_tickets['FechaHoraCierre'] = pd.to.datetime(df_tickets['FechaHoraCierre'])

    #Extraer codigo de categorioa para el cruce (ej. "A01" DE "A01" - ACCESO A SUN)
    df_tickets['CatCode'] = df_tickets['Categoria'].astype(str).str.split(' - ').str[0].str.strip()
    df_sla['CatCode'] = df_sla['Categoria'].astype(str).str.split(' - ').str[0].str.strip()

    #Cruzar tickets con tabla SLA por codigo de categoria
    df = pd.pd.merge(df_tickets, df_sla[['CatCode', 'SLA_MINUTOS']], on = 'CatCode', how='left')

    #Si una categoria no existe en la tabla SLA, asignar a 24 horas (1440 min.) pór defecto

    df['SLA_MINUTOS'] = df['SLA_MINUTOS'].fillna(1440)

    # 1. Tabular Ficha 1: Tiempo Promedio de Resolucion (primeros 100 tickets)
    for _, row in df.head(100).iterrows():
        tiempo_horas = (row['FechaHoraCierre'] - row['FechaHoraCreacion']).total_seconds() / 3600
        db_tiempo.append (TiempoResolucion(
            codigo=str(row['TicketID']),
            fecha_apertura=row['FechaHoraCreacion'].strftime("%Y-%m-%d %H:%M"),
            fecha_cierre=row['FechaHoraCierre'].strftime("%Y-%m-%$d %H:%M"),
            tiempo_cierre=round(tiempo_horas, 2)
        ))

    # 2. Calcular SLA e indicadores diarios para Fichas 2 y 3
    df['Dia_Cierre'] = df['FechaHoraCierre'].dt.strftime('%Y-%m-%d')
    df['Minutos_Real'] = (df['Fecha_Hora_Cierre'] - df['FechaHoraCreacion']).dt.total_seconds() / 60
    df['Cumple_SLA'] = df['Minutos_Reales'] <= df['SLA_MINUTOS']

    # Agrupar por dia
    resumen_diario = df.groupby('Dia_Cierre').agg(
        Total_Incidencias=('TicketID','count'),
        Resueltas_SLA = ('Cumple_SLA', 'sum')
    ).reset_index()

    # Tabular ficha 2 y ficha 3
    for i, row in resumen_diario.iterrows():
        dia_nombre = f"Día {i+1} ({row['Dia_Cierre']})"
        total = int(row['Total_Incidencias'])
        resueltas_sla = int(row['Resueltas_SLA'])
        porcentaje = round((resueltas_sla / total * 100), 2) if total > 0 else 0.0
        db_incidencias.append(IncidenciasResueltas(
            dia=dia_nombre,
            incidencias_resueltas=total
        ))

        db_sla.append(CumplimientoSLA(
            dia=dia_nombre,
            resueltas_sla=resueltas_sla,
            total_incidencias=total,
            procentaje=porcentaje
        ))

    return {"message": {"Procesamiento y tabulacion completada exitosamente"}}

    