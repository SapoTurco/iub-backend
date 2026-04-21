from jose import jwt
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer
from datetime import datetime, timedelta

SECRET_KEY = "clave_secreta"
ALGORITHM = "HS256"

security = HTTPBearer()

def create_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=60)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verificar_token(token=Depends(security)):
    try:
        return jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
    except:
        raise HTTPException(status_code=401, detail="Token inválido")