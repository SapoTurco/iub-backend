from pydantic import BaseModel

class Login(BaseModel):
    usuario: str
    clave: str

class Usuario(BaseModel):
    usuario: str
    clave: str
    nombre: str
    rol: str

class Paciente(BaseModel):
    nombre: str
    apellido: str
    documento: str
    diagnostico: str

class Movimiento(BaseModel):
    paciente_id: int
    cama_id: int

class NuevaCama(BaseModel):
    codigo: str
    zona: str

class AltaCama(BaseModel):
    cama_id: int

class NuevoReporte(BaseModel):
    tipo:        str   # MEDICO | OBSERVACION | INGRESO | ALTA
    contenido:   str
    paciente_id: int