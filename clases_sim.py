



# ========================
#    Librerias
# ========================
from numpy.random import choice
import simpy
import pandas as pd
import numpy as np
import random
from scipy.stats import lognorm
import scipy.stats as stats
import matplotlib.pyplot as plt
import seaborn as sns
# from prettytable import PrettyTable


# =======================================
#    Parámetros básicos de operación
#       Se pueden modificar
# ========================================

TIEMPO_PUERTA_SALIDA = 8.16        # (minutos)
TIEMPO_PUERTA_ENTRADA = 2       # (minutos)
TIEMPO_CARGAR_EN_CHUTE = 7.28     # (minutos)
TIEMPO_ATRAQUE = 462  # (minutos)
TIEMPO_LLEGADA_CAMIONES = 440
# (factor de ajuste de la tasa de llegada de buques)
TASA_LLEGADA_FACTOR = 1.08

TIEMPO_A_BODEGA = 3             # (minutos)
TIEMPO_DESCARGAR_EN_BODEGA = 6  # (minutos)
TIEMPO_CARGAR_EN_BODEGA = 6     # (minutos)

TIEMPO_ENTRADA_CAMION_DEDICADO = 2  # (minutos)
TIEMPO_SALIDA_DE_BODEGA = 2         # (minutos)
MAXIMO_RADA = 8




# =======================================
#    Datos Historicos Camiones y Buques
# ========================================

camiones = pd.read_csv('camiones1.csv')
camiones = camiones[camiones['año'] > 2022]
camiones = camiones[camiones['capacidad'] > 20]
tasa_llegada = 1/(camiones.groupby('turno')['min_entre_camiones'].mean())
tasas_llegada = tasa_llegada.to_dict()

buques = pd.read_excel('naves_epic.xlsx')
buques = buques[buques['tiempo_descarga'] < 140]
buques = buques[buques['tiempo_descarga'] > 30]
buques = buques[buques['tiempo_entre_arribos'] < 450]
buques['espera_sin_detenciones_externas'] = (
    buques['tiempo_de_espera']-buques['total_detenciones'])
buques['horas_delay'] = (buques['inicio_descarga'] -
                         buques['primera_espia']).dt.total_seconds()/3600
buques['minutos_delay'] = buques['horas_delay']*60
buques['dias_delay'] = buques['horas_delay']/24
# buques.loc[buques['espera_sin_detenciones_externas'] < 0, 'espera_sin_detenciones_externas'] = 0

buques = buques[-250:]
buques['horas_de_espera'] = buques['tiempo_de_espera'].copy()
buques['horas_de_descarga'] = buques['tiempo_descarga'].copy()
buques['horas_detencion'] = buques['total_detenciones'].copy()
buques['horas_entre_arribos'] = buques['tiempo_entre_arribos'].copy()
buques['horas_falta_equipos'] = buques['total_falta_equipos'].copy()
buques['Dias_de_espera_buque'] = buques['tiempo_de_espera']/24
buques['Dias_de_descarga_buque'] = buques['tiempo_descarga']/24
buques['Dias_detencion_buque'] = buques['total_detenciones']/24
buques['Dias_entre_arribos_buque'] = buques['tiempo_entre_arribos']/24
buques['Dias_falta_equipos_buque'] = buques['total_falta_equipos']/24
buques['Dias_espera_2'] = buques['espera_sin_detenciones_externas']/24
buques['tiempo_de_espera'] = buques['tiempo_de_espera']*60
buques['tiempo_descarga'] = buques['tiempo_descarga']*60
buques['total_detenciones'] = buques['total_detenciones']*60
buques['minutos_entre_arribos'] = buques['tiempo_entre_arribos']*60
buques['total_falta_equipos'] = buques['total_falta_equipos']*60

tasa_llegada_buques = 1/(buques['minutos_entre_arribos'].mean())

tasa_llegada_buques = tasa_llegada_buques*TASA_LLEGADA_FACTOR  # tasa


def determinar_turno(hora):
    if 8 <= hora < 16:
        return 1
    elif 16 <= hora < 24:
        return 2
    else:
        return 3



# =====================================
#   Clases
# =====================================

class Puerto:
    def __init__(self, env):
        self.env = env
        self.frente_atraque = simpy.Resource(env, capacity=1)
        self.puerta_entrada = simpy.Resource(env, capacity=1)
        self.puerta_salida = simpy.Resource(env, capacity=1)
        self.chutes = simpy.Resource(env, capacity=5)
        self.grano_muelle = simpy.Container(env, init=0)
        self.iniciar_llegada_camiones = env.event()
        self.inicio_descarga_evento = env.event()
        self.fin_descarga_evento = env.event()
        self.falta_camiones_event = env.event()
        self.buques_peridos = 0
        self.current_buque = None
        self.arribo_buque_evento = env.event()
        self.buques_atendidos = []
        self.datos_rada = []

    def monitor_cola_camiones(self, env: simpy.Environment):
        """
        Monitorea la cola de camiones en la puerta de entrada.
        Si no hay camiones, dispara un evento indicando falta de camiones.
        """
        while True:
            if len(self.puerta_entrada.users) == 0 and len(self.puerta_entrada.queue) == 0:
                self.falta_camiones_event.succeed()
                self.falta_camiones_event = env.event()
            yield env.timeout(0.5)


class Bodega:
    def __init__(self, env, grano_bodega_init):
        self.env = env
        self.grano_bodega = simpy.Container(env, init=grano_bodega_init)
        self.cargar_en_bodega = simpy.Resource(env, capacity=1)
        self.descargar_en_bodega = simpy.Resource(env, capacity=1)
        self.bodega_recargada = env.event()
        self.eventos_bodega = []
        if grano_bodega_init > 0:
            self.bodega_recargada.succeed()
            self.bodega_recargada = env.event()


class Buque:
    def __init__(self, env, puerto: Puerto, id_buque, tonelaje):
        self.env = env
        self.id_buque = id_buque
        self.tonelaje = tonelaje
        self.puerto = puerto
        self.num_camiones_normales = 0
        self.num_camiones_dedicados = 0
        self.largo_cola_al_arribar = len(puerto.frente_atraque.queue)

    def proceso_buque(self, env, puerto):
        """
        Proceso que maneja la llegada de un buque, el atraque,
        la espera y la descarga.
        """
        self.arribo = env.now
        with puerto.frente_atraque.request() as request_muelle:
            yield request_muelle

            yield env.timeout(TIEMPO_LLEGADA_CAMIONES)

            puerto.current_buque = self

            # Iniciar la llegada de camiones:
            puerto.iniciar_llegada_camiones.succeed()
            puerto.iniciar_llegada_camiones = env.event()

            yield env.timeout(TIEMPO_ATRAQUE-TIEMPO_LLEGADA_CAMIONES)
            # fin de atraque, comienza descarga

            self.primera_espia = env.now
            self.tiempo_espera = self.primera_espia - self.arribo

            yield env.timeout(choice(buques['minutos_delay'].values))

            # Cargar el grano en el muelle
            yield puerto.grano_muelle.put(self.tonelaje)

            puerto.inicio_descarga_evento.succeed()
            puerto.inicio_descarga_evento = env.event()
            self.inicio_descarga = env.now
            # Esperar a que se dispare el evento de fin de descarga
            yield puerto.fin_descarga_evento
            puerto.current_buque = None
            self.tiempo_descarga = env.now - self.inicio_descarga

            puerto.buques_atendidos.append(self)


class Camion:
    def __init__(self, env, id_camion, capacidad, puerto: Puerto):
        self.env = env
        self.id = id_camion
        self.capacidad = capacidad
        self.carga = 0
        self.puerto = puerto
        self.proceso = env.process(self.proceso_camion(env, puerto))

    def proceso_camion(self, env,  puerto: Puerto):
        """
        Proceso del camión normal que entra por la puerta,
        solicita chute y carga desde el muelle, luego sale por la puerta de salida.
        """
        req_puerta_entrada = puerto.puerta_entrada.request()
        yield req_puerta_entrada
        yield env.timeout(TIEMPO_PUERTA_ENTRADA/2)
        with puerto.chutes.request() as req_chute:
            yield req_chute
            yield env.timeout(TIEMPO_PUERTA_ENTRADA/2)

            puerto.puerta_entrada.release(req_puerta_entrada)

            # Verificación de pausa en caso de horario de colación (ejemplo simple)
            current_time = env.now % 1440
            if 780 <= current_time < 840:
                yield env.timeout(840 - current_time)
            elif 420 <= current_time < 480:
                yield env.timeout(480 - current_time)
            elif 900 <= current_time < 960:
                yield env.timeout(960 - current_time)
            elif 1380 <= current_time < 1440:
                yield env.timeout(1440 - current_time)

            # Esperar a que comience la descarga si no hay buque o no hay grano
            if puerto.grano_muelle.level == 0 or puerto.current_buque == None:
                yield puerto.inicio_descarga_evento

            # Carga mínima entre la capacidad del camión y lo disponible en muelle
            carga = min(self.capacidad,  puerto.grano_muelle.level)
            yield puerto.grano_muelle.get(carga)
            self.carga = carga
            puerto.current_buque.num_camiones_normales += 1

            # Si ya no queda grano y todavía está en curso la descarga del buque,
            # se dispara el evento fin de descarga
            if puerto.grano_muelle.level == 0 and not puerto.fin_descarga_evento.triggered:
                puerto.fin_descarga_evento.succeed()
                puerto.fin_descarga_evento = env.event()

            yield env.timeout(TIEMPO_CARGAR_EN_CHUTE)
        req_puerta_salida = puerto.puerta_salida.request()
        yield req_puerta_salida

        puerto.puerta_salida.release(req_puerta_salida)


class CamionDedicado:
    def __init__(self, env, id_camion, capacidad, puerto: Puerto, bodega: Bodega):
        self.env = env
        self.id = id_camion
        self.capacidad = capacidad
        self.puerto = puerto
        self.bodega = bodega
        self.carga = 0
        self.proceso = env.process(
            self.proceso_camion_dedicado(env, puerto, bodega))

    def proceso_camion_dedicado(self, env, puerto, bodega):
        """
        El camión dedicado viaja repetidamente entre el muelle y la bodega.
        Solo parte cuando no hay camiones normales disponibles y se requiere traslado.
        """
        while True:
            # Esperar hasta que se dispare el evento de falta de camiones
            esperar = True
            while esperar:
                yield puerto.falta_camiones_event
                yield env.timeout(2)  # Pequeña demora adicional
                if len(puerto.puerta_entrada.users) == 0 and len(puerto.puerta_entrada.queue) == 0:
                    esperar = False

            # Entra al muelle
            req_puerta = puerto.puerta_entrada.request()
            yield req_puerta

            yield env.timeout(TIEMPO_PUERTA_ENTRADA)

            with puerto.chutes.request() as req_chute:
                yield req_chute

                puerto.puerta_entrada.release(req_puerta)

                current_time = env.now % 1440
                if 780 <= current_time < 840:
                    yield env.timeout(840 - current_time)
                elif 420 <= current_time < 480:
                    yield env.timeout(480 - current_time)
                elif 900 <= current_time < 960:
                    yield env.timeout(960 - current_time)
                elif 1380 <= current_time < 1440:
                    yield env.timeout(1440 - current_time)

                # Si no hay grano o no hay buque, esperar el inicio de descarga
                if puerto.grano_muelle.level == 0 or puerto.current_buque == None:
                    yield puerto.inicio_descarga_evento

                carga = min(self.capacidad,  puerto.grano_muelle.level)
                yield puerto.grano_muelle.get(carga)
                self.carga = carga
                puerto.current_buque.num_camiones_dedicados += 1

                if puerto.grano_muelle.level == 0 and not puerto.fin_descarga_evento.triggered:
                    puerto.fin_descarga_evento.succeed()
                    puerto.fin_descarga_evento = env.event()

                yield env.timeout(TIEMPO_CARGAR_EN_CHUTE)

            # Traslado a la bodega
            yield env.timeout(TIEMPO_A_BODEGA)

            # Descarga en la bodega
            self.t_llegada_bodega = env.now
            with bodega.descargar_en_bodega.request() as req_bodega:
                yield req_bodega
                self.t_inicio_descarga_bodega = env.now

                yield env.timeout(TIEMPO_DESCARGAR_EN_BODEGA)
                yield bodega.grano_bodega.put(self.carga)
                if not bodega.bodega_recargada.triggered:
                    bodega.bodega_recargada.succeed()
                    bodega.bodega_recargada = env.event()

                self.carga_depositada = self.carga
                self.carga = 0
                self.fin_descarga = env.now

                self.tiempo_en_cola = self.t_inicio_descarga_bodega-self.t_llegada_bodega
                self.tiempo_descarga = self.fin_descarga-self.t_inicio_descarga_bodega

                bodega.eventos_bodega.append({
                    'id_camion': 'Dedicado'+str(self.id),
                    'horas en cola bodega': self.tiempo_en_cola/60,
                    'horas de descarga en bodega': self.tiempo_descarga/60,
                    'horas de carga en bodega': 0,
                    'actividad camion ': 'descargar en bodega',
                    'tons depositadas en bodega': self.carga_depositada,
                    'tons retiradas de bodega': 0,
                    'ton restante bodega': bodega.grano_bodega.level
                })

            yield env.timeout(TIEMPO_SALIDA_DE_BODEGA)


class CamionBodega:
    def __init__(self, env, id_camion_bodega, capacidad, bodega):
        self.env = env
        self.id = id_camion_bodega
        self.capacidad = capacidad
        self.carga = 0
        self.proceso = env.process(self.proceso_camion_bodega(env, bodega))

    def proceso_camion_bodega(self, env, bodega: Bodega):
        """
        Camión que se carga en la bodega y luego sale.
        """
        self.tiempo_llegada = env.now
        with bodega.cargar_en_bodega.request() as req_cargar_bodega:
            yield req_cargar_bodega
            self.inicio_carga = env.now

            # Espera si la bodega está vacía
            if bodega.grano_bodega.level == 0:
                yield bodega.bodega_recargada

            yield env.timeout(TIEMPO_CARGAR_EN_BODEGA)

            carga = min(self.capacidad,  bodega.grano_bodega.level)
            yield bodega.grano_bodega.get(carga)
            self.carga = carga
            self.fin_carga = env.now

            self.tiempo_en_cola = self.inicio_carga-self.tiempo_llegada
            self.tiempo_carga = self.fin_carga-self.inicio_carga

            bodega.eventos_bodega.append({
                'id_camion': 'Bodega'+str(self.id),
                'horas en cola bodega': self.tiempo_en_cola/60,
                'horas de descarga en bodega': 0,
                'horas de carga en bodega': self.tiempo_carga/60,
                'actividad camion ': 'cargar en bodega',
                'tons depositadas en bodega': 0,
                'tons retiradas de bodega': self.carga,
                'ton restante bodega': bodega.grano_bodega.level
            })

            yield env.timeout(TIEMPO_SALIDA_DE_BODEGA)

def generar_buques(env: simpy.Environment, puerto: Puerto):
    """
    Genera buques en el sistema basados en una tasa de llegada exponencial.
    """
    i_buques = 0
    while True:
        tiempo_entre_arribo = random.expovariate(tasa_llegada_buques)

        # tiempo_entre_arribo = stats.expon.rvs(loc=loc, scale=scale, size=1)[0]
        yield env.timeout(tiempo_entre_arribo)

        # Si la cola es muy larga, se asume que el buque se pierde
        if len(puerto.frente_atraque.queue) < MAXIMO_RADA:
            buque = Buque(env, puerto, i_buques, choice(buques['tonelaje']))
            env.process(buque.proceso_buque(env, puerto))
            i_buques += 1
        else:
            puerto.buques_peridos += 1


def generar_camiones_puerto(env, puerto, p):
    """
    Genera camiones normales que llegan al puerto para cargar. 
    La probabilidad `p` se utiliza para otras condiciones (ej: ir a bodega).
    """
    camion_puerto_id = 0
    while True:
        yield puerto.iniciar_llegada_camiones

        while puerto.current_buque is not None:
            hora = (env.now % 1440) // 60
            turno = determinar_turno(hora)
            if random.random() < 1-p:
                yield env.timeout(random.expovariate(tasa_llegada[turno]))

            # Ejemplo de uso de p (no se emplea aquí, pero se deja para posibles extensiones)
                Camion(env, camion_puerto_id, choice(
                    camiones['capacidad']), puerto)
                camion_puerto_id += 1


def generar_camiones_bodega(env, bodega, p):
    """
    Genera camiones que se cargan en la bodega. 
    La probabilidad `p` indica la probabilidad de que se generen estos camiones.
    """
    camion_bodega_id = 0
    while True:
        # Espera hasta que la bodega tenga algo de grano
        yield bodega.bodega_recargada

        while bodega.grano_bodega.level > 0:
            hora = (env.now % 1440) // 60
            turno = determinar_turno(hora)
            if random.random() < p:
                yield env.timeout(random.expovariate(tasa_llegada[turno]))

                CamionBodega(env, camion_bodega_id, choice(
                    camiones['capacidad']), bodega)
                camion_bodega_id += 1


def monitor_cola_buques(env, puerto: Puerto):
    """
    Monitorea la cola de buques en el muelle y guarda datos en puerto.datos_rada.
    """
    while True:
        yield env.timeout(60*24)
        tiempo = env.now
        buques_en_cola = len(puerto.frente_atraque.queue) + \
            len(puerto.frente_atraque.users)
        puerto.datos_rada.append({
            'Dia': tiempo // 1440,
            'Largo cola rada': buques_en_cola,
            'total buques atendidos': len(puerto.buques_atendidos),
            'total buques perdidos': puerto.buques_peridos
        })


def simulacion(años, camiones_dedicados=0, grano=0, cap=0, prob=0, buques_inicio_cola=7, seed=None):
    """
    Ejecuta la simulación con los parámetros proporcionados:
    - tiempo: tiempo total de simulación (minutos)
    - n: número de camiones dedicados
    - grano: capacidad inicial de la bodega
    - cap: capacidad de camiones dedicados
    - prob: probabilidad asociada a la generación de camiones para la bodega
    - buques_inicio_cola: cuántos buques se inician en la cola (inicial)

    Retorna:
    - df_buques: DataFrame con info de buques atendidos
    - df_cola: DataFrame con el monitoreo de la cola de buques
    - df_bodega (opcional): DataFrame con eventos de la bodega si n>0
    """
    tiempo = (365 * 24 * 60) * años

    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)

    env = simpy.Environment()
    puerto = Puerto(env)

    env.process(generar_buques(env, puerto))
    env.process(generar_camiones_puerto(env, puerto, prob))
    env.process(monitor_cola_buques(env, puerto))

    for i in range(buques_inicio_cola):
        buque = Buque(env, puerto, i, choice(buques['tonelaje']))
        env.process(buque.proceso_buque(env, puerto))

    if camiones_dedicados > 0:
        bodega = Bodega(env, grano)
        env.process(generar_camiones_bodega(env, bodega, prob))
        env.process(puerto.monitor_cola_camiones(env))

        for i in range(camiones_dedicados):
            CamionDedicado(env, i, cap, puerto, bodega)

    env.run(until=tiempo)

    datos_buques = []
    for buque in puerto.buques_atendidos[buques_inicio_cola:]:
        datos_buques.append({
            'BuqueID': buque.id_buque,
            'Largo cola al arribo': buque.largo_cola_al_arribar,
            'Tonelaje buque': buque.tonelaje,
            'Arribo': buque.arribo,
            'Tiempo de espera (dias)': (buque.tiempo_espera)/(60*24),
            'Tiempo descarga (dias)': buque.tiempo_descarga/(60*24),
            'Camiones normales': buque.num_camiones_normales,
            'Camiones dedicados': buque.num_camiones_dedicados,
            'Tiempo de espera (horas)': buque.tiempo_espera/60,
            'Tiempo descarga (horas)': buque.tiempo_descarga/60

        })

    df_buques = pd.DataFrame(datos_buques)
    df_cola = pd.DataFrame(puerto.datos_rada)
    if camiones_dedicados > 0:
        df_bodega = pd.DataFrame(bodega.eventos_bodega)
        return df_buques, df_cola, df_bodega
    
    print('fin simulacion')

    return df_buques, df_cola



df_buques, df_cola = simulacion(
    años=3, camiones_dedicados=0, seed=42)

num_con_camiones = 20
capacidad_camion_dedicado = 30
probabilidad_bodega = 0.1
grano_inicial_bodega = 1000
años_simulacion = 3
buques_inicio_cola = 7

df_buques_sim, df_cola_rada, df_bodega_sim = simulacion(
    años=3,
    camiones_dedicados=num_con_camiones,
    grano=grano_inicial_bodega,
    cap=capacidad_camion_dedicado,
    prob=probabilidad_bodega,
    buques_inicio_cola=buques_inicio_cola,
    seed=33
)