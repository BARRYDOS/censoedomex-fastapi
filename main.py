# main.py

from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Optional
from docxtpl import DocxTemplate
import json
import io
import os

app = FastAPI(title="Catastro → DOCX", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # ← tu APEX
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_cors_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "https://censoedomex.maxapex.net"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    return response


# === Modelos Pydantic (mismos que antes) ===
class Terreno(BaseModel):
    valor_terreno_propio: int = Field(..., ge=0)
    metros_terreno_propio: Optional[float] = None
    valor_terreno_comun: int = Field(..., ge=0)
    metros_terreno_comun: int = Field(..., ge=0)

class Construccion(BaseModel):
    valor_construccion_propia: int = Field(..., ge=0)
    metros_construccion_propia: int = Field(..., ge=0)
    valor_construccion_comun: int = Field(..., ge=0)
    metros_construccion_comun: int = Field(..., ge=0)

class Impuesto(BaseModel):
    recargo: Optional[float] = None
    multa: Optional[float] = None
    gastos: Optional[float] = None
    subsidios: Optional[float] = None
    suma: Optional[float] = None
    ultimo_periodo_pagado: Optional[str] = None
    impuesto_predial: Optional[float] = None
    cantidad_con_letra: Optional[str] = None

class Predio(BaseModel):
    clave_catastral: str = Field(..., pattern=r"^\d{3}-\d{2}-\d{3}-\d{2}-\d{2}-[A-Z0-9]+$")
    folio: int = Field(..., gt=0)
    direccion: str
    contribuyente: str
    terreno: Terreno
    construccion: Construccion
    impuesto: Impuesto

class DocumentoCatastral(BaseModel):
    archivo: str
    predio: List[Predio]


# === Ruta para generar DOCX ===
@app.post("/generar-docx")
async def generar_docx(file: UploadFile = File(...)):    
    if not file.filename.endswith(".json"):
        raise HTTPException(400, "Solo archivos .json")

    try:
        content = await file.read()
        data = json.loads(content)
        doc_data = DocumentoCatastral.model_validate(data)
        print(doc_data.archivo)
    except Exception as e:
        raise HTTPException(422, f"Error en validación: {str(e)}")

    # Cargar plantilla
    template_path = "templates/template.docx"
    if not os.path.exists(template_path):
        raise HTTPException(500, "Plantilla no encontrada")

    doc = DocxTemplate(template_path)

    # Renderizar
    doc.render(doc_data.model_dump())

    # Guardar en memoria
    output = io.BytesIO()
    doc.save(output)
    #doc.save(doc_data.archivo)
    output.seek(0)

    # Nombre del archivo de salida
    nombre_salida = doc_data.archivo.replace(".docx", "_generado.docx")

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename={doc_data.archivo}"},
    )


@app.get("/")
def root():
    return {"message": "API para generar DOCX desde JSON catastral. Usa POST /generar-docx"}
