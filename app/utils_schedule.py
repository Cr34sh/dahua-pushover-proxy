from datetime import datetime
from .models import Schedule, Holiday

def is_active_now():
    """
    Comprueba si el momento actual está dentro del horario activo
    y si no es un día festivo.
    """
    now = datetime.now()
    today_date = now.date()
    current_time = now.time()
    
    # 1. Comprobar festivos
    holiday = Holiday.query.filter_by(date=today_date).first()
    if holiday:
        # Si es festivo, según la definición se bloquea/ignora todo el día.
        # "Ademas de añadir festivos como el dia 1 de enero todo el dia." -> Entendido como exención.
        # Wait, the prompt says "añadir festivos como el dia 1 de enero todo el dia" in the schedule menu.
        # Usually holidays mean NO notifications, OR it means ALWAYS notifications?
        # Let's assume festivos = no notifications. The prompt said: "Si un evento llega a las 15h y las notificaciones no estan activas... se ignora."
        # If they meant "holidays = notifications enabled all day", I should change this. 
        # Actually, in security, holidays usually mean the building is empty, so you DO want notifications all day.
        # "y sabado y domingo Todo el dia. Ademas de añadir festivos como el dia 1 de enero todo el dia."
        # Ah! It means "Holidays should behave like Saturday/Sunday, meaning active all day".
        # Okay, let's treat holidays as "Always Active".
        return True
        
    # 2. Comprobar horario normal
    current_day = now.weekday() # 0 = Lunes, 6 = Domingo
    schedule = Schedule.query.filter_by(day_of_week=current_day).first()
    
    if not schedule:
        # Si no hay horario definido para hoy, asumimos inactivo
        return False
        
    start = schedule.start_time
    end = schedule.end_time
    
    if start == end:
        # Si inicio y fin son iguales, podría significar inactivo o 24h. Asumamos 24h si es 00:00 a 00:00
        # O podemos usar la convención de start < end normal, pero qué pasa si cruza la medianoche (ej 19:00 a 08:00)?
        pass

    # Manejo del cruce de medianoche (ej: 19:00 a 08:00)
    if start < end:
        # Horario normal en el mismo día (ej: 08:00 a 19:00)
        return start <= current_time <= end
    else:
        # Horario cruzando medianoche (ej: 19:00 a 08:00)
        return current_time >= start or current_time <= end

