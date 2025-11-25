# main.py (versión corregida y funcional)

from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from docxtpl import DocxTemplate
import json
import io
import os

app = FastAPI(title="Catastro → DOCX", version="1.0")

# CONFIGURACIÓN CORS CORRECTA (esta es la que funciona con APEX)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://censoedomex.maxapex.net",   # Tu APEX real
        "https://censoedomex.maxapex.net/",  # con slash final también
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

# ELIMINA el @app.middleware("http") que tenías → está mal escrito y sobrescribe CORS

# === Tus modelos Pydantic (sin cambios) ===
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

# === Ruta principal ===
@app.post("/generar-docx")
async def generar_docx(file: UploadFile = File(...)):
    if not file.filename.endswith(".json"):
        raise HTTPException(400, "Solo se permiten archivos .json")

    try:
        content = await file.read()
        data = json.loads(content.decode("utf-8"))
        doc_data = DocumentoCatastral.model_validate(data)
    except Exception as e:
        raise HTTPException(422, f"Error en JSON o validación: {str(e)}")

    template_path = "templates/template.docx"
    if not os.path.exists(template_path):
        raise HTTPException(500, "Plantilla template.docx no encontrada")

    doc = DocxTemplate(template_path)
    doc.render(doc_data.model_dump())

    output = io.BytesIO()
    doc.save(output)
    output.seek(0)

    # Usar el nombre que viene en el JSON
    nombre_archivo = doc_data.archivo if doc_data.archivo.endswith(".docx") else f"{doc_data.archivo}.docx"

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{nombre_archivo}",
            "Access-Control-Expose-Headers": "Content-Disposition",
        }
    )

@app.get("/")
def root():
    return {"message": "API Catastro → DOCX activa"}
