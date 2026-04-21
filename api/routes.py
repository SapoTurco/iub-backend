from fastapi import APIRouter, HTTPException, Depends
from db import get_db
from auth.auth import create_token, verificar_token
from models.models import Login, Usuario, Paciente, Movimiento, NuevaCama, AltaCama, NuevoReporte

router = APIRouter()

# ============================================================
# ROLES
#   ADMIN      → control total
#   ENFERMERIA → operativo: asignar, alta, crear pacientes, ver todo
#   MEDICO     → consultivo: solo lectura
# ============================================================

ROLES_VALIDOS = {"ADMIN", "ENFERMERIA", "MEDICO"}


class HospitalRouter:

    # ── 🔐 LOGIN ─────────────────────────────────────────────
    @staticmethod
    def login(data: Login):
        db     = get_db()
        cursor = db.cursor()
        try:
            cursor.execute(
                "SELECT id, clave, rol, nombre FROM usuario WHERE usuario=%s",
                (data.usuario,)
            )
            user = cursor.fetchone()
            if not user:
                raise HTTPException(status_code=400, detail="Usuario no existe")
            if data.clave != user[1]:
                raise HTTPException(status_code=400, detail="Clave incorrecta")

            token = create_token({"id": user[0], "rol": user[2]})
            return {"token": token, "rol": user[2], "nombre": user[3]}
        finally:
            cursor.close()
            db.close()

    # ── 👤 LISTAR USUARIOS (solo ADMIN) ──────────────────────
    @staticmethod
    def listar_usuarios(token=Depends(verificar_token)):
        if token["rol"] != "ADMIN":
            raise HTTPException(status_code=403, detail="Sin permisos")
        db     = get_db()
        cursor = db.cursor()
        try:
            cursor.execute("SELECT id, usuario, nombre, rol FROM usuario ORDER BY id DESC")
            rows = cursor.fetchall()
            return [{"id": r[0], "usuario": r[1], "nombre": r[2], "rol": r[3]} for r in rows]
        finally:
            cursor.close()
            db.close()

    # ── 👤 CREAR USUARIO (solo ADMIN) ────────────────────────
    @staticmethod
    def crear_usuario(user: Usuario, token=Depends(verificar_token)):
        if token["rol"] != "ADMIN":
            raise HTTPException(status_code=403, detail="Sin permisos")
        if user.rol not in ROLES_VALIDOS:
            raise HTTPException(status_code=400, detail="Rol invalido")
        db     = get_db()
        cursor = db.cursor()
        try:
            cursor.execute("SELECT id FROM usuario WHERE usuario=%s", (user.usuario,))
            if cursor.fetchone():
                raise HTTPException(status_code=400, detail="Usuario ya existe")
            cursor.execute(
                "INSERT INTO usuario (usuario, clave, nombre, rol) VALUES (%s, %s, %s, %s)",
                (user.usuario, user.clave, user.nombre, user.rol)
            )
            db.commit()
            return {"mensaje": "Usuario creado"}
        finally:
            cursor.close()
            db.close()

    # ── 👤 EDITAR USUARIO (solo ADMIN) ───────────────────────
    @staticmethod
    def editar_usuario(id: int, user: Usuario, token=Depends(verificar_token)):
        if token["rol"] != "ADMIN":
            raise HTTPException(status_code=403, detail="Sin permisos")
        if user.rol not in ROLES_VALIDOS:
            raise HTTPException(status_code=400, detail="Rol invalido")
        db     = get_db()
        cursor = db.cursor()
        try:
            cursor.execute("SELECT id FROM usuario WHERE id=%s", (id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Usuario no existe")
            cursor.execute(
                "UPDATE usuario SET nombre=%s, rol=%s, clave=%s WHERE id=%s",
                (user.nombre, user.rol, user.clave, id)
            )
            db.commit()
            return {"mensaje": "Usuario actualizado"}
        finally:
            cursor.close()
            db.close()

    # ── 👤 ELIMINAR USUARIO (solo ADMIN) ─────────────────────
    @staticmethod
    def eliminar_usuario(id: int, token=Depends(verificar_token)):
        if token["rol"] != "ADMIN":
            raise HTTPException(status_code=403, detail="Sin permisos")
        if id == token["id"]:
            raise HTTPException(status_code=400, detail="No puedes eliminarte a ti mismo")
        db     = get_db()
        cursor = db.cursor()
        try:
            cursor.execute("SELECT id FROM usuario WHERE id=%s", (id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Usuario no existe")
            cursor.execute("DELETE FROM usuario WHERE id=%s", (id,))
            db.commit()
            return {"mensaje": "Usuario eliminado"}
        finally:
            cursor.close()
            db.close()

    # ── 🛏️ OBTENER CAMAS (todos los roles) ───────────────────
    @staticmethod
    def obtener_camas(token=Depends(verificar_token)):
        db     = get_db()
        cursor = db.cursor()
        try:
            cursor.execute("SELECT * FROM cama")
            camas = cursor.fetchall()
            resultado = []
            for c in camas:
                cama_id = c[0]
                estado  = c[3]
                paciente_data = None
                paciente_id   = None
                if estado == "OCUPADO":
                    cursor.execute("""
                        SELECT m.paciente_id, p.nombre, p.apellido, p.documento, p.diagnostico
                        FROM movimiento m
                        JOIN paciente p ON m.paciente_id = p.id
                        WHERE m.cama_id = %s AND m.tipo = 'INGRESO'
                        ORDER BY m.id DESC LIMIT 1
                    """, (cama_id,))
                    pac = cursor.fetchone()
                    if pac:
                        paciente_id   = pac[0]
                        paciente_data = {"id": pac[0], "nombre": pac[1], "apellido": pac[2], "documento": pac[3], "diagnostico": pac[4]}
                resultado.append({"id": c[0], "codigo": c[1], "zona": c[2], "estado": c[3], "paciente_id": paciente_id, "paciente": paciente_data})
            return resultado
        finally:
            cursor.close()
            db.close()

    # ── 🛏️ CREAR CAMA (solo ADMIN) ───────────────────────────
    @staticmethod
    def crear_cama(c: NuevaCama, token=Depends(verificar_token)):
        if token["rol"] != "ADMIN":
            raise HTTPException(status_code=403, detail="Sin permisos")
        zonas_validas = ["GENERAL", "UCI", "AISLAMIENTO", "QUIROFANO"]
        if c.zona not in zonas_validas:
            raise HTTPException(status_code=400, detail="Zona invalida")
        db     = get_db()
        cursor = db.cursor()
        try:
            cursor.execute("SELECT id FROM cama WHERE codigo=%s", (c.codigo,))
            if cursor.fetchone():
                raise HTTPException(status_code=400, detail="Ya existe una cama con ese codigo")
            cursor.execute("INSERT INTO cama (codigo, zona, estado) VALUES (%s, %s, 'DISPONIBLE')", (c.codigo, c.zona))
            db.commit()
            return {"mensaje": "Cama creada"}
        finally:
            cursor.close()
            db.close()

    # ── 🛏️ CAMAS DISPONIBLES (todos los roles) ───────────────
    @staticmethod
    def camas_disponibles(token=Depends(verificar_token)):
        db     = get_db()
        cursor = db.cursor()
        try:
            cursor.execute("SELECT * FROM cama WHERE estado='DISPONIBLE'")
            result = cursor.fetchall()
            return [{"id": r[0], "codigo": r[1], "zona": r[2], "estado": r[3]} for r in result]
        finally:
            cursor.close()
            db.close()

    # ── 🔧 CAMBIAR ESTADO DE CAMA (solo ADMIN) ────────────────
    @staticmethod
    def cambiar_estado(id: int, estado: str, token=Depends(verificar_token)):
        if token["rol"] != "ADMIN":
            raise HTTPException(status_code=403, detail="Sin permisos")
        if estado not in ["DISPONIBLE", "OCUPADO", "MANTENIMIENTO"]:
            raise HTTPException(status_code=400, detail="Estado invalido")
        db     = get_db()
        cursor = db.cursor()
        try:
            cursor.execute("SELECT id FROM cama WHERE id=%s", (id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Cama no existe")
            cursor.execute("UPDATE cama SET estado=%s WHERE id=%s", (estado, id))
            db.commit()
            return {"mensaje": "Estado actualizado"}
        finally:
            cursor.close()
            db.close()

    # ── 🧍 CREAR PACIENTE (ADMIN + ENFERMERIA) ───────────────
    @staticmethod
    def crear_paciente(p: Paciente, token=Depends(verificar_token)):
        if token["rol"] not in ("ADMIN", "ENFERMERIA"):
            raise HTTPException(status_code=403, detail="Sin permisos para registrar pacientes")
        db     = get_db()
        cursor = db.cursor()
        try:
            cursor.execute("SELECT id FROM paciente WHERE documento=%s", (p.documento,))
            if cursor.fetchone():
                raise HTTPException(status_code=400, detail="Paciente ya existe")
            cursor.execute(
                "INSERT INTO paciente (nombre, apellido, documento, diagnostico) VALUES (%s, %s, %s, %s)",
                (p.nombre, p.apellido, p.documento, p.diagnostico)
            )
            db.commit()
            return {"mensaje": "Paciente creado"}
        finally:
            cursor.close()
            db.close()

    # ── 🧍 TODOS LOS PACIENTES (todos los roles) ─────────────
    @staticmethod
    def obtener_pacientes(token=Depends(verificar_token)):
        db     = get_db()
        cursor = db.cursor()
        try:
            cursor.execute("SELECT * FROM paciente")
            result = cursor.fetchall()
            return [{"id": r[0], "nombre": r[1], "apellido": r[2], "documento": r[3], "diagnostico": r[4]} for r in result]
        finally:
            cursor.close()
            db.close()

    # ── 🔍 PACIENTE POR ID (todos los roles) ─────────────────
    @staticmethod
    def obtener_paciente(id: int, token=Depends(verificar_token)):
        db     = get_db()
        cursor = db.cursor()
        try:
            cursor.execute("SELECT * FROM paciente WHERE id=%s", (id,))
            r = cursor.fetchone()
            if not r:
                raise HTTPException(status_code=404, detail="Paciente no existe")
            return {"id": r[0], "nombre": r[1], "apellido": r[2], "documento": r[3], "diagnostico": r[4]}
        finally:
            cursor.close()
            db.close()

    # ── 🧠 INGRESO / ASIGNAR CAMA (ADMIN + ENFERMERIA) ───────
    @staticmethod
    def asignar(m: Movimiento, token=Depends(verificar_token)):
        if token["rol"] not in ("ADMIN", "ENFERMERIA"):
            raise HTTPException(status_code=403, detail="Sin permisos para asignar camas")
        db     = get_db()
        cursor = db.cursor()
        try:
            cursor.execute("SELECT id FROM paciente WHERE id=%s", (m.paciente_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Paciente no existe")
            cursor.execute("SELECT estado FROM cama WHERE id=%s", (m.cama_id,))
            cama = cursor.fetchone()
            if not cama:
                raise HTTPException(status_code=404, detail="Cama no existe")
            if cama[0] != "DISPONIBLE":
                raise HTTPException(status_code=400, detail="La cama no esta disponible")
            cursor.execute(
                "INSERT INTO movimiento (tipo, fecha, paciente_id, cama_id) VALUES ('INGRESO', NOW(), %s, %s)",
                (m.paciente_id, m.cama_id)
            )
            cursor.execute("UPDATE cama SET estado='OCUPADO' WHERE id=%s", (m.cama_id,))
            db.commit()
            return {"mensaje": "Paciente asignado correctamente"}
        finally:
            cursor.close()
            db.close()

    # ── 🏥 ALTA (ADMIN + ENFERMERIA) ─────────────────────────
    @staticmethod
    def alta(data: AltaCama, token=Depends(verificar_token)):
        if token["rol"] not in ("ADMIN", "ENFERMERIA"):
            raise HTTPException(status_code=403, detail="Sin permisos para registrar altas")
        db     = get_db()
        cursor = db.cursor()
        try:
            cursor.execute("SELECT estado FROM cama WHERE id=%s", (data.cama_id,))
            cama = cursor.fetchone()
            if not cama:
                raise HTTPException(status_code=404, detail="Cama no existe")
            if cama[0] != "OCUPADO":
                raise HTTPException(status_code=400, detail="La cama no esta ocupada")
            cursor.execute("""
                SELECT paciente_id FROM movimiento
                WHERE cama_id = %s AND tipo = 'INGRESO'
                ORDER BY id DESC LIMIT 1
            """, (data.cama_id,))
            mov = cursor.fetchone()
            if not mov:
                raise HTTPException(status_code=404, detail="No se encontro el ingreso de esta cama")
            paciente_id = mov[0]
            cursor.execute(
                "INSERT INTO movimiento (tipo, fecha, paciente_id, cama_id) VALUES ('ALTA', NOW(), %s, %s)",
                (paciente_id, data.cama_id)
            )
            cursor.execute("UPDATE cama SET estado='DISPONIBLE' WHERE id=%s", (data.cama_id,))
            db.commit()
            return {"mensaje": "Alta registrada correctamente"}
        finally:
            cursor.close()
            db.close()

    # ── 🔄 MOVIMIENTOS (todos los roles) ─────────────────────
    @staticmethod
    def movimientos(token=Depends(verificar_token)):
        db     = get_db()
        cursor = db.cursor()
        try:
            cursor.execute("""
                SELECT m.tipo, p.nombre, c.codigo, m.fecha
                FROM movimiento m
                JOIN paciente p ON m.paciente_id = p.id
                JOIN cama c ON m.cama_id = c.id
                ORDER BY m.id DESC
            """)
            result = cursor.fetchall()
            return [{"tipo": r[0], "paciente": r[1], "cama": r[2], "fecha": str(r[3]) if r[3] else None} for r in result]
        finally:
            cursor.close()
            db.close()

    # ── 📊 REPORTE ESTADISTICO (todos los roles) ─────────────
    @staticmethod
    def reporte(token=Depends(verificar_token)):
        db     = get_db()
        cursor = db.cursor()
        try:
            cursor.execute("SELECT estado, COUNT(*) FROM cama GROUP BY estado")
            result = cursor.fetchall()
            return [{"estado": r[0], "cantidad": r[1]} for r in result]
        finally:
            cursor.close()
            db.close()

    # ── 📝 CREAR REPORTE CLINICO (ADMIN + MEDICO) ────────────
    @staticmethod
    def crear_reporte(r: NuevoReporte, token=Depends(verificar_token)):
        if token["rol"] not in ("ADMIN", "MEDICO"):
            raise HTTPException(status_code=403, detail="Sin permisos para crear reportes clinicos")
        tipos_validos = ["MEDICO", "OBSERVACION", "INGRESO", "ALTA"]
        if r.tipo not in tipos_validos:
            raise HTTPException(status_code=400, detail="Tipo de reporte invalido")
        db     = get_db()
        cursor = db.cursor()
        try:
            cursor.execute("SELECT id FROM paciente WHERE id=%s", (r.paciente_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Paciente no existe")
            cursor.execute(
                "INSERT INTO reporte (tipo, contenido, fecha, paciente_id, usuario_id) VALUES (%s, %s, NOW(), %s, %s)",
                (r.tipo, r.contenido, r.paciente_id, token["id"])
            )
            db.commit()
            return {"mensaje": "Reporte creado correctamente"}
        finally:
            cursor.close()
            db.close()

    # ── 📝 TODOS LOS REPORTES (todos los roles) ───────────────
    @staticmethod
    def obtener_reportes(token=Depends(verificar_token)):
        db     = get_db()
        cursor = db.cursor()
        try:
            cursor.execute("""
                SELECT r.id, r.tipo, r.contenido, r.fecha,
                       p.nombre, p.apellido, p.documento,
                       u.nombre AS autor, u.rol
                FROM reporte r
                JOIN paciente p ON r.paciente_id = p.id
                JOIN usuario  u ON r.usuario_id  = u.id
                ORDER BY r.id DESC
            """)
            rows = cursor.fetchall()
            return [{"id": row[0], "tipo": row[1], "contenido": row[2], "fecha": str(row[3]) if row[3] else None, "paciente": {"nombre": row[4], "apellido": row[5], "documento": row[6]}, "autor": row[7], "rol_autor": row[8]} for row in rows]
        finally:
            cursor.close()
            db.close()

    # ── 📝 REPORTES DE UN PACIENTE (todos los roles) ──────────
    @staticmethod
    def obtener_reportes_paciente(id: int, token=Depends(verificar_token)):
        db     = get_db()
        cursor = db.cursor()
        try:
            cursor.execute("SELECT id FROM paciente WHERE id=%s", (id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Paciente no existe")
            cursor.execute("""
                SELECT r.id, r.tipo, r.contenido, r.fecha,
                       p.nombre, p.apellido, p.documento,
                       u.nombre AS autor, u.rol
                FROM reporte r
                JOIN paciente p ON r.paciente_id = p.id
                JOIN usuario  u ON r.usuario_id  = u.id
                WHERE r.paciente_id = %s
                ORDER BY r.id DESC
            """, (id,))
            rows = cursor.fetchall()
            return [{"id": row[0], "tipo": row[1], "contenido": row[2], "fecha": str(row[3]) if row[3] else None, "paciente": {"nombre": row[4], "apellido": row[5], "documento": row[6]}, "autor": row[7], "rol_autor": row[8]} for row in rows]
        finally:
            cursor.close()
            db.close()


# ============================================================
# REGISTRO DE RUTAS
# ============================================================
h = HospitalRouter()

router.post("/login")                        (h.login)
router.get("/usuarios")                      (h.listar_usuarios)
router.post("/usuarios")                     (h.crear_usuario)
router.put("/usuarios/{id}")                 (h.editar_usuario)
router.delete("/usuarios/{id}")              (h.eliminar_usuario)
router.get("/camas")                         (h.obtener_camas)
router.post("/camas")                        (h.crear_cama)
router.get("/camas/disponibles")             (h.camas_disponibles)
router.put("/camas/{id}")                    (h.cambiar_estado)
router.post("/pacientes")                    (h.crear_paciente)
router.get("/pacientes")                     (h.obtener_pacientes)
router.get("/pacientes/{id}")                (h.obtener_paciente)
router.post("/asignar")                      (h.asignar)
router.post("/alta")                         (h.alta)
router.get("/movimientos")                   (h.movimientos)
router.get("/reporte")                       (h.reporte)
router.post("/reportes")                     (h.crear_reporte)
router.get("/reportes")                      (h.obtener_reportes)
router.get("/reportes/paciente/{id}")        (h.obtener_reportes_paciente)
