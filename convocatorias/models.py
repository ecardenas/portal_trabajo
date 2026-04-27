# convocatorias/models.py
# Modelos de convocatorias y filtros

class Convocatoria:
    def __init__(self, id, carrera, ubicacion, estado, fecha_vencimiento):
        self.id = id
        self.carrera = carrera
        self.ubicacion = ubicacion
        self.estado = estado
        self.fecha_vencimiento = fecha_vencimiento
