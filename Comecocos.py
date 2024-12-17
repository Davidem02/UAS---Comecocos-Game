import geopy.distance
from shapely.geometry import Point
from shapely.geometry.polygon import Polygon
from datetime import datetime
import json
import math
import random
import threading
import tkinter as tk
import os
from tkinter import ttk
from tkinter import messagebox
from tkinter.simpledialog import askstring
import tkintermapview
from PIL import Image, ImageTk
import pyautogui
import win32gui
import glob
import paho.mqtt.client as mqtt
from dronLink.Dron import Dron
import geopy.distance
from geographiclib.geodesic import Geodesic
from ParameterManager import ParameterManager
from AutopilotControllerClass import AutopilotController
from tkinter import messagebox, Toplevel
import pygame
from pygame import mixer




def haversine(lat1, lon1, lat2, lon2):
    # Radio promedio de la Tierra en metros
    R = 6371000

    # Convertir grados a radianes
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

    # Diferencias
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    # Fórmula de Haversine
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    # Distancia en metros
    distance = R * c
    return distance

# procesado de los datos de telemetría
def processTelemetryInfo (id, telemetry_info):
    global dronIcons, colors, traces, lock
    global positions
    # recupero la posición en la que está el dron
    lat = telemetry_info['lat']
    lon = telemetry_info['lon']
    alt = telemetry_info['alt']
    modo = telemetry_info['flightMode']
    positions[id] = [lat, lon]

    # si es el primer paquete de este dron entonces ponemos en el mapa el icono de ese dron
    if not dronIcons[id]:
        dronIcons[id] = map_widget.set_marker(lat, lon,
                        icon=dronPictures[id],icon_anchor="center")
    # si no es el primer paquete entonces muevo el icono a la nueva posición
    else:
        dronIcons[id].set_position(lat,lon)
    # actrualizo la altitud
    altitudes[id]['text'] = str (round(alt,2))
    modos[id]['text'] = modo

    #Calcumalos la distancia al dron 1 (pacman)
    distanciaPacman = round(haversine(positions[0][0], positions[0][1], positions[id][0], positions[id][1]), 2)
    distances[id]['text'] = str(round(distanciaPacman, 2))

    if distanciaPacman != 0 and distanciaPacman <= 2:
        mixer.init()
        mixer.music.load('images/PacmanGameOverAudio.mp3')
        mixer.music.play()

        swarm[0].Land(blocking=False)
        swarm[id].setFlightMode('BRAKE')



    # dejo rastro si debo hacerlo y guardo el marcador en la lista correspondiente al dron,
    # para luego poder borrarlo si así lo pide el jugador. También necesitare la posición del marcador
    if drawingAction[id] == 'startDrawing':
        traces[id].append({'pos': (lat, lon), 'marker': None})
        drawingAction[id] = 'draw'
    elif drawingAction[id] == 'draw':
            last = len(traces[id]) -1
            if last >= 0:
                coords = traces[id][last]['pos']

                marker = map_widget.set_path([(lat, lon), coords], color=colors[id], width=6)
                traces[id].append({'pos': (lat,lon), 'marker': marker})
    elif drawingAction [id] == 'remove':
        for item in traces[id]:
            # elimino de la lista de trazas todas las que están a menos de un metro de la posición del dron
            center = item['pos']
            if haversine (center[0], center[1], lat, lon) < 1:
                traces[id].remove(item)
                # la primera traza no tiene marker, asi que no puedo borrar la linea
                if  item['marker'] != None:
                    item['marker'].delete()

########## Funciones para la creación de multi escenarios #################################

def createBtnClick ():
    global scenario
    scenario = []
    # limpiamos el mapa de los elementos que tenga
    clear()
    # quitamos los otros frames
    selectFrame.grid_forget()
    superviseFrame.grid_forget()
    # visualizamos el frame de creación
    createFrame.grid(row=1, column=0,  columnspan=3, padx=5, pady=5, sticky=tk.N +  tk.E + tk.W)

    createBtn['text'] = 'Creando...'
    createBtn['fg'] = 'white'
    createBtn['bg'] = 'green'

    selectBtn['text'] = 'Seleccionar'
    selectBtn['fg'] = 'black'
    selectBtn['bg'] = 'dark orange'

    superviseBtn['text'] = 'Supervisar'
    superviseBtn['fg'] = 'black'
    superviseBtn['bg'] = 'dark orange'

# iniciamos la creación de un fence tipo polígono
def definePoly(type):
    global fence, paths, polys
    global fenceType

    fenceType = type # 1 es inclusión y 2 es exclusión

    paths = []
    fence = {
        'type' : 'polygon',
        'waypoints': []
    }
    # informo del tema de los botones del mouse para que el usuario no se despiste
    messagebox.showinfo("showinfo",
                        "Con el boton izquierdo del ratón señala los waypoints\nCon el boton derecho cierra el polígono")

# iniciamos la creación de un fence tipo círculo
def defineCircle(type):
    global fence, paths, polys
    global fenceType, centerFixed

    fenceType = type  # 1 es inclusión y 2 es exclusión
    paths = []
    fence = {
        'type': 'circle'
    }
    centerFixed = False
    # informo del tema de los botones del mouse para que el usuario no se despiste
    messagebox.showinfo("showinfo",
                        "Con el boton izquierdo señala el centro\nCon el boton derecho marca el límite del círculo")

# capturamos el siguiente click del mouse
def getFenceWaypoint (coords):
    global marker, centerFixed
    # acabo de clicar con el botón izquierdo
    if fence:
        # hay un fence en marcha
        # veamos si el fence es un polígono o un círculo
        if fence['type'] == 'polygon':
            if len(fence['waypoints']) == 0:
                # es el primer waypoint del fence. Pongo un marcador
                if fenceType == 1:
                    # en el fence de inclusión (límites del escenario)
                    marker = map_widget.set_marker(coords[0], coords[1], icon=colorIcon, icon_anchor="center")
                else:
                    # es un obstáculo
                    marker = map_widget.set_marker(coords[0], coords[1], icon=black, icon_anchor="center")

            if len(fence['waypoints']) > 0:
                # trazo una línea desde el anterior a este
                lat = fence['waypoints'][-1]['lat']
                lon = fence['waypoints'][-1]['lon']
                # elijo el color según si es de inclusión o un obstáculo
                if fenceType == 1:
                    paths.append(map_widget.set_path([(lat,lon), coords], color=selectedColor, width=3))
                else:
                    paths.append(map_widget.set_path([(lat,lon), coords], color='black', width=3))
                # si es el segundo waypoint quito el marcador que señala la posición del primero
                if len(fence['waypoints']) == 1:
                    marker.delete()

            # guardo el nuevo waypoint
            fence['waypoints'].append ({'lat': coords[0], 'lon': coords[1]})
        else:
            # es un círculo. El click indica la posición de centro del circulo
            if centerFixed:
                messagebox.showinfo("Error",
                                    "Marca el límite con el botón derecho del mouse")

            else:
                # ponemos un marcador del color adecuado para indicar la posición del centro
                if fenceType == 1:
                    marker = map_widget.set_marker(coords[0], coords[1], icon=colorIcon, icon_anchor="center")
                else:
                    marker = map_widget.set_marker(coords[0], coords[1], icon=black, icon_anchor="center")
                # guardamos la posicion de centro
                fence['lat']= coords[0]
                fence['lon'] = coords[1]
                centerFixed = True
    else:
        messagebox.showinfo("error",
                            "No hay ningun fence en construccion\nIndica primero qué tipo de fence quieres")

# cerramos el fence
def closeFence(coords):
    global poly, polys, fence
    # estamos creando un fence y acabamos de darle al boton derecho del mouse para cerrar
    # el fence está listo
    if fence['type'] == 'polygon':
        scenario.append(fence)

        # substituyo los paths por un polígono
        for path in paths:
            path.delete()

        poly = []
        for point in  fence['waypoints']:
            poly.append((point['lat'], point['lon']))

        if fenceType == 1:
            # polígono del color correspondiente al jugador
            polys.append(map_widget.set_polygon(poly,
                                        outline_color=selectedColor,
                                        fill_color=selectedColor,
                                        border_width=3))
        else:
            # polígono de color negro (obstaculo)
            polys.append(map_widget.set_polygon(poly,
                                                fill_color='black',
                                                outline_color="black",
                                                border_width=3))
    else:
        # Es un circulo y acabamos de marcar el límite del circulo
        # borro el marcador del centro
        marker.delete()
        center= (fence['lat'], fence['lon'])
        limit = (coords[0], coords[1])
        radius = geopy.distance.geodesic(center, limit).m
        # el radio del círculo es la distancia entre el centro y el punto clicado
        fence['radius'] = radius
        # ya tengo completa la definición del fence
        scenario.append(fence)
        # como no se puede dibujar un circulo con la librería tkintermapview, creo un poligono que aproxime al círculo
        points = getCircle(fence['lat'], fence['lon'], radius)

        # Dibujo en el mapa el polígono que aproxima al círculo, usando el color apropiado según el tipo y el jugador
        if fenceType == 1:
            polys.append(map_widget.set_polygon(points,
                                                outline_color= selectedColor,
                                                fill_color=selectedColor,
                                                border_width=3))
        else:
            polys.append(map_widget.set_polygon(points,
                                                fill_color='black',
                                                outline_color="black",
                                                border_width=3))

    fence = None

# La siguiente función crea una imagen capturando el contenido de una ventana
def screenshot(window_title=None):
    # capturo una imagen del multi escenario para guardarla más tarde
    if window_title:
        hwnd = win32gui.FindWindow(None, window_title)
        if hwnd:
            win32gui.SetForegroundWindow(hwnd)
            x, y, x1, y1 = win32gui.GetClientRect(hwnd)
            x, y = win32gui.ClientToScreen(hwnd, (x, y))
            x1, y1 = win32gui.ClientToScreen(hwnd, (x1 - x, y1 - y))
            # aquí le indico la zona de la ventana que me interesa, que es básicamente la zona del dronLab
            im = pyautogui.screenshot(region=(x+800, y+250, 730, 580))
            return im
        else:
            print('Window not found!')
    else:
        im = pyautogui.screenshot()
        return im

# guardamos los datos del escenario (imagen y fichero json)
def registerScenario ():
    global escenariosComecocos

    # voy a guardar el multi escenario en el fichero con el nombre indicado en el momento de la creación
    jsonFilename = 'escenariosComecocos/' + name.get() + "_"+str(numPlayers)+".json"

    with open(jsonFilename, 'w') as f:
        json.dump(escenariosComecocos, f)
    # aqui capturo el contenido de la ventana que muestra el Camp Nou (zona del cesped, que es dónde está el escenario)
    im = screenshot('Gestión de escenarios')
    imageFilename = 'escenariosComecocos/'+name.get()+ "_"+str(numPlayers)+".png"
    im.save(imageFilename)
    escenariosComecocos = []
    # limpio el mapa
    clear()

# genera el poligono que aproxima al círculo
def getCircle ( lat, lon, radius):
    # aquí creo el polígono que aproxima al círculo
    geod = Geodesic.WGS84
    points = []
    for angle in range(0, 360, 5):  # 5 grados de separación para suavidad
        # me da las coordenadas del punto que esta a una distancia radius del centro (lat, lon) con el ángulo indicado
        g = geod.Direct(lat, lon, angle, radius)
        lat2 = float(g["lat2"])
        lon2 = float(g["lon2"])
        points.append((lat2, lon2))
    return points

############################ Funciones para seleccionar multi escenario ##########################################
def selectBtnClick ():
    global scenarios, current, polys
    scenarios = []
    # limpio el mapa
    clear()
    # elimino los otros frames
    createFrame.grid_forget()
    superviseFrame.grid_forget()
    # muestro el frame de selección
    selectFrame.grid(row=1, column=0, columnspan=3, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)

    selectBtn['text'] = 'Seleccionando...'
    selectBtn['fg'] = 'white'
    selectBtn['bg'] = 'green'

    createBtn['text'] = 'Crear'
    createBtn['fg'] = 'black'
    createBtn['bg'] = 'dark orange'

    superviseBtn['text'] = 'Supervisar'
    superviseBtn['fg'] = 'black'
    superviseBtn['bg'] = 'dark orange'

# una vez elegido el numero de jugadores mostramos los multi escenarios que hay para ese número de jugadores
def selectScenarios (num):
    global scenarios, current, polys, drawingAction, traces
    global numPlayers
    global client, swarm

    numPlayers = num
    # cargamos en una lista las imágenes de todos los multi escenarios disponibles
    # para el número de jugadores indicado
    scenarios = []
    for file in glob.glob("escenariosComecocos/*_"+str(num)+".png"):
        scene = Image.open(file)
        scene = scene.resize((300, 200))
        scenePic = ImageTk.PhotoImage(scene)
        # en la lista guardamos el nombre que se le dió al escenario y la imagen
        scenarios.append({'name': file.split('.')[0], 'pic': scenePic})

    if len(scenarios) > 0:
        # mostramos ya en el canvas la imagen del primer multi escenario
        scenarioCanvas.create_image(0, 0, image=scenarios[0]['pic'], anchor=tk.NW)
        current = 0
        # no podemos seleccionar el anterior porque no hay anterior
        prevBtn['state'] = tk.DISABLED
        # y si solo hay 1 multi escenario tampoco hay siguiente
        if len(scenarios) == 1:
            nextBtn['state'] = tk.DISABLED
        else:
            nextBtn['state'] = tk.NORMAL

        sendBtn['state'] = tk.DISABLED
    else:
        messagebox.showinfo("showinfo",
                            "No hay escenarios para elegir")

    # aqui ya puedo poner en marcha el sevicio de autopiloto

    additionalEvents = [
        {'event': 'startDrawing', 'method':startDrawing},
        {'event': 'stopDrawing', 'method':stopDrawing},
        {'event': 'startRemovingDrawing', 'method':startRemovingDrawing},
        {'event': 'stopRemovingDrawing', 'method':stopRemovingDrawing},
        {'event': 'removeAll', 'method': removeAll}
    ]
    autopilotService = AutopilotController (numPlayers, numPlayers, additionalEvents)
    client, swarm = autopilotService.start()

# mostrar anterior
def showPrev ():
    global current
    current = current -1
    # mostramos el multi escenario anterior
    scenarioCanvas.create_image(0, 0, image=scenarios[current]['pic'], anchor=tk.NW)
    # deshabilitamos botones si no hay anterior o siguiente
    if current == 0:
        prevBtn['state'] = tk.DISABLED
    else:
        prevBtn['state'] = tk.NORMAL
    if current == len(scenarios) - 1:
        nextBtn['state'] = tk.DISABLED
    else:
        nextBtn['state'] = tk.NORMAL

# mostrar siguiente
def showNext ():
    global current
    current = current +1
    # muestro el siguiente
    scenarioCanvas.create_image(0, 0, image=scenarios[current]['pic'], anchor=tk.NW)
    # deshabilitamos botones si no hay anterior o siguiente
    if current == 0:
        prevBtn['state'] = tk.DISABLED
    else:
        prevBtn['state'] = tk.NORMAL
    if current == len(scenarios) - 1:
        nextBtn['state'] = tk.DISABLED
    else:
        nextBtn['state'] = tk.NORMAL

# Limpiamos el mapa
def clear ():
    global paths, fence, polys
    name.set ("")
    for path in paths:
        path.delete()
    for poly in polys:
        poly.delete()

    paths = []
    polys = []

# borramos el escenario que esta a la vista
def deleteScenario ():
    global current
    msg_box = messagebox.askquestion(
        "Atención",
        "¿Seguro que quieres eliminar este escenario?",
        icon="warning",
    )
    if msg_box == "yes":
        # borro los dos ficheros que representan el multi escenario seleccionado
        os.remove(scenarios[current]['name'] + '.png')
        os.remove(scenarios[current]['name'] + '.json')
        scenarios.remove (scenarios[current])
        # muestro el multi escenario anterior (o el siguiente si no hay anterior o ninguno si tampoco hay siguiente)
        if len (scenarios) != 0:
            if len (scenarios) == 1:
                # solo queda un escenario
                current = 0
                scenarioCanvas.create_image(0, 0, image=scenarios[current]['pic'], anchor=tk.NW)
                prevBtn['state'] = tk.DISABLED
                nextBtn['state'] = tk.DISABLED
            else:
                # quedan más multi escenarios
                if current == 0:
                    # hemos borrado el primer multi escenario de la lista. Mostramos el nuevo primero
                    scenarioCanvas.create_image(0, 0, image=scenarios[current]['pic'], anchor=tk.NW)
                    prevBtn['state'] = tk.DISABLED
                    if len (scenarios) > 1:
                        nextBtn['state'] = tk.NORMAL
                else:
                    # mostramos
                    scenarioCanvas.create_image(0, 0, image=scenarios[current]['pic'], anchor=tk.NW)
                    prevBtn['state'] = tk.NORMAL
                    if current == len (scenarios) -1:
                        nextBtn['state'] = tk.DISABLED
                    else:
                        nextBtn['state'] = tk.NORMAL
            clear()

# dibujamos en el mapa el multi escenario
def drawScenario (escenariosComecocos):
    global polys

    # borro los elementos que haya en el mapa
    for poly in polys:
        poly.delete()
    # vamos a recorrer la lista de escenarios
    scenarios = escenariosComecocos ['scenarios']
    for element in scenarios:
        color = element ['player']
        # cojo el escenario de este cugador
        scenario = element['scenario']
        # ahora dibujamos el escenario
        # el primer fence es el de inclusión
        inclusion = scenario[0]
        if inclusion['type'] == 'polygon':
            poly = []
            for point in inclusion['waypoints']:
                poly.append((point['lat'], point['lon']))
            polys.append(map_widget.set_polygon(poly,
                                                outline_color=color,
                                                fill_color=color,
                                                border_width=3))
        else:
            # el fence es un círculo. Como no puedo dibujar circulos en el mapa
            # creo el polígono que aproximará al círculo
            poly = getCircle(inclusion['lat'], inclusion['lon'], inclusion['radius'])
            polys.append(map_widget.set_polygon(poly,
                                                outline_color=color,
                                                fill_color=color,
                                                border_width=3))
        # ahora voy a dibujar los obstáculos
        for i in range(1, len(scenario)):
            fence = scenario[i]
            if fence['type'] == 'polygon':
                poly = []
                for point in fence['waypoints']:
                    poly.append((point['lat'], point['lon']))
                polys.append(map_widget.set_polygon(poly,
                                                    outline_color="black",
                                                    fill_color="black",
                                                    border_width=3))
            else:
                poly = getCircle(fence['lat'], fence['lon'], fence['radius'])
                polys.append(map_widget.set_polygon(poly,
                                                    outline_color="black",
                                                    fill_color="black",
                                                    border_width=3))

# seleccionar el multi escenario que está a la vista
def selectScenario():
    global polys, selectedescenariosComecocos, numPlayers
    # limpio el mapa
    for poly in polys:
        poly.delete()
    # cargamos el fichero json con el multi escenario seleccionado (el que está en la posición current de la lista9
    f = open(scenarios[current]['name'] +'.json')
    selectedescenariosComecocos = json.load (f)
    # dibujo el escenario
    drawScenario(selectedescenariosComecocos)
    # habilito el botón para enviar el escenario al enjambre
    sendBtn['state'] = tk.NORMAL

# envia los datos del multi escenario seleccionado al enjambre
def sendScenario ():
    # enviamos a cada dron del enjambre el escenario que le toca
    global swarm
    global connected, dron, dronIcons
    global altitudes, modos, distances

# tengo que prepara el escenario de cada dron en el formato establecido
    tmp=[
         {'type': 'polygon',
          'waypoints': [{'lat': 41.2764287, 'lon': 1.9882538}, {'lat': 41.2766081, 'lon': 1.9890015}, {'lat': 41.2763893, 'lon': 1.9891083}, {'lat': 41.2762034, 'lon': 1.9883497}]},
         {'type': 'polygon',
          'waypoints': [{'lat': 41.2764166, 'lon': 1.98829}, {'lat': 41.2763284, 'lon': 1.9883256}, {'lat': 41.276342, 'lon': 1.9883718}, {'lat': 41.27640249, 'lon': 1.98834501}, {'lat': 41.2764191, 'lon': 1.9884069}, {'lat': 41.2764441, 'lon': 1.988394}]},
         {'type': 'polygon',
          'waypoints': [{'lat': 41.27628356, 'lon': 1.98834434}, {'lat': 41.2762941, 'lon': 1.9883899}, {'lat': 41.2762483, 'lon': 1.9884101}, {'lat': 41.2762629, 'lon': 1.9884704}, {'lat': 41.2762357, 'lon': 1.9884831}, {'lat': 41.276211, 'lon': 1.9883789}]},
         {'type': 'polygon',
          'waypoints': [{'lat': 41.27638486, 'lon': 1.98839799}, {'lat': 41.27628608, 'lon': 1.98844157}, {'lat': 41.2762982, 'lon': 1.9884919}, {'lat': 41.2763975, 'lon': 1.9884443}]},
         {'type': 'polygon',
          'waypoints': [{'lat': 41.2764413, 'lon': 1.9885133}, {'lat': 41.2763672, 'lon': 1.9885468}, {'lat': 41.2763511, 'lon': 1.9886012}, {'lat': 41.2763874, 'lon': 1.9886173}, {'lat': 41.2764574, 'lon': 1.988575}]},
         {'type': 'polygon',
          'waypoints': [{'lat': 41.27646952, 'lon': 1.98864006}, {'lat': 41.27641157, 'lon': 1.98867895}, {'lat': 41.27642164, 'lon': 1.98871382}, {'lat': 41.27645843, 'lon': 1.98868699}, {'lat': 41.27647002, 'lon': 1.98872589}, {'lat': 41.27643298, 'lon': 1.98875271}, {'lat': 41.2764426, 'lon': 1.9887856}, {'lat': 41.2764993, 'lon': 1.9887507}]},
         {'type': 'polygon',
          'waypoints': [{'lat': 41.276537, 'lon': 1.9887668}, {'lat': 41.2764695, 'lon': 1.9888094}, {'lat': 41.2764798, 'lon': 1.9888446}, {'lat': 41.276525, 'lon': 1.9888124}, {'lat': 41.27654234, 'lon': 1.98887073}, {'lat': 41.27655972, 'lon': 1.98885765}]},
         {'type': 'polygon',
          'waypoints': [{'lat': 41.27651361, 'lon': 1.98885748}, {'lat': 41.27647128, 'lon': 1.98888481}, {'lat': 41.27645138, 'lon': 1.98882144}, {'lat': 41.27642668, 'lon': 1.9888372}, {'lat': 41.27645541, 'lon': 1.98892772}, {'lat': 41.27652142, 'lon': 1.98888548}]},
         {'type': 'polygon',
          'waypoints': [{'lat': 41.2763879, 'lon': 1.9888292}, {'lat': 41.2763627, 'lon': 1.9888406}, {'lat': 41.276406, 'lon': 1.9890129}, {'lat': 41.2764297, 'lon': 1.9889901}]},
         {'type': 'circle', 'radius': 2, 'lat': 41.2763123, 'lon': 1.9885468},
         {'type': 'circle', 'radius': 2, 'lat': 41.2763057, 'lon': 1.9886193},
         {'type': 'circle', 'radius': 2, 'lat': 41.2763581, 'lon': 1.9887232},
         {'type': 'circle', 'radius': 3.5, 'lat': 41.2765391, 'lon': 1.988972}
        ]
        # lo primero el fence de inclusión que es la zona correspondente

        # y ahora cada uno de los obstaculos que tengo en la lista obstacles



    for i in range (0,len(swarm)):
        swarm[i].setScenario(tmp)

    sendBtn['bg'] = 'green'

# carga el multi escenario que hay ahora en el enjambre
# NO ESTA OPERATIVO
def loadScenario ():
    # ESTO NO ESTA OPERATIVO
    # voy a mostrar el escenario que hay cargado en el dron
    global connected, dron
    if not connected:
        dron = Dron()
        connection_string = 'tcp:127.0.0.1:5763'
        baud = 115200
        dron.connect(connection_string, baud)
        connected = True
    scenario = dron.getScenario()
    if scenario:
        drawScenario(scenario)
    else:
        messagebox.showinfo("showinfo",
                        "No hay ningún escenario cargado en el dron")

# preparo los botones para crear el escenario de cada jugador
def createPlayer (color):
    # aqui vamos a crear el escenario para uno de los jugadores, el que tiene el color indicado como parámetro
    global colorIcon
    global selectedColor, scenario
    selectedColor = color
    # veamos en que caso estamos
    if color == 'yellow':
        # empezamos a crear el escenario de este jugador
        if 'Crea' in yellowPlayerBtn['text']:
            colorIcon = yellow
            yellowPlayerBtn['text'] = "Clica aquí cuando hayas acabado el escenario amarillo"
            scenario = []
        # damos por terminado el escenario de este jugador
        elif 'Clica' in yellowPlayerBtn['text']:
            yellowPlayerBtn['text'] = "Escenario amarillo listo"
            # lo añadimos a la estructura del multi escenario
            escenariosComecocos ['scenarios'].append ({
                'player': 'yellow',
                'scenario': scenario
            })

    # ahora lo mismo para el resto de jugadores
    elif color == 'blue':
        if 'Crea' in bluePlayerBtn['text']:
            colorIcon = blue
            bluePlayerBtn['text'] = "Clica aquí cuando hayas acabado el escenario azul"
            scenario = []
        elif 'Clica' in bluePlayerBtn['text']:
            bluePlayerBtn['text'] = "Escenario azul listo"
            escenariosComecocos['scenarios'].append({
                'player': 'blue',
                'scenario': scenario
            })

    elif color == 'red':
        if 'Crea' in redPlayerBtn['text']:
            colorIcon = red
            redPlayerBtn['text'] = "Clica aquí cuando hayas acabado el escenario rojo"
            scenario = []
        elif 'Clica' in redPlayerBtn['text']:
            redPlayerBtn['text'] = "Escenario rojo listo"
            escenariosComecocos['scenarios'].append({
                'player': 'red',
                'scenario': scenario
            })
    else:
        if 'Crea' in pinkPlayerBtn['text']:
            colorIcon = pink
            pinkPlayerBtn['text'] = "Clica aquí cuando hayas acabado el escenario rosa"
            scenario = []
        elif 'Clica' in pinkPlayerBtn['text']:
                redPlayerBtn['text'] = "Escenario rosa listo"
                escenariosComecocos['scenarios'].append({
                    'player': 'pink',
                    'scenario': scenario
                })

# elijo el número de jugadores
def selectNumPlayers (num):
    global yellowPlayerBtn, bluePlayerBtn, redPlayerBtn, pinkPlayerBtn
    global escenariosComecocos
    global numPlayers
    numPlayers = num
    # empezamos a preparar la estructura de datos del multi escenario
    escenariosComecocos = {
        'numPlayers': num,  # numero de jugadores
        'scenarios': []     # un escenario para cada jugador
    }
    # colocamos los botones que permiten crear el escenario para cada uno de los jugadores
    if num == 1:
        yellowPlayerBtn = tk.Button(selectPlayersFrame, text="Crea el escenario para el jugador rojo", bg="yellow", fg = 'white',
                                 command=lambda: createPlayer('yellow'))
        yellowPlayerBtn.grid(row=2, column=0, columnspan = 4, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)
    if num == 2:
        yellowPlayerBtn = tk.Button(selectPlayersFrame, text="Crea el escenario para el jugador rojo", bg="yellow", fg='white',
                                command = lambda: createPlayer('yellow'))
        yellowPlayerBtn.grid(row=2, column=0, columnspan = 4, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)

        bluePlayerBtn = tk.Button(selectPlayersFrame, text="Crea el escenario para el jugador azul", bg="blue", fg='white',
                                command = lambda: createPlayer('blue'))
        bluePlayerBtn.grid(row=3, column=0,columnspan = 4,  padx=5, pady=5, sticky=tk.N + tk.E + tk.W)
    if num == 3:
        yellowPlayerBtn = tk.Button(selectPlayersFrame, text="Crea el escenario para el jugador rojo", bg="yellow",
                                 fg='white',
                                 command=lambda: createPlayer('yellow'))
        yellowPlayerBtn.grid(row=2, column=0,columnspan = 4,  padx=5, pady=5, sticky=tk.N + tk.E + tk.W)

        bluePlayerBtn = tk.Button(selectPlayersFrame, text="Crea el escenario para el jugador azul", bg="blue",
                                  fg='white',
                                  command=lambda: createPlayer('blue'))
        bluePlayerBtn.grid(row=3, column=0,columnspan = 4,  padx=5, pady=5, sticky=tk.N + tk.E + tk.W)
        redPlayerBtn = tk.Button(selectPlayersFrame, text="Crea el escenario para el jugador verde", bg="red", fg='white',
                                command = lambda: createPlayer('red'))
        redPlayerBtn.grid(row=4, column=0,columnspan = 4,  padx=5, pady=5, sticky=tk.N + tk.E + tk.W)

    if num == 4:
        yellowPlayerBtn = tk.Button(selectPlayersFrame, text="Crea el escenario para el jugador amarillo", bg="yellow",
                                 fg='white',
                                 command=lambda: createPlayer('yellow'))
        yellowPlayerBtn.grid(row=2, column=0,columnspan = 4,  padx=5, pady=5, sticky=tk.N + tk.E + tk.W)

        bluePlayerBtn = tk.Button(selectPlayersFrame, text="Crea el escenario para el jugador azul", bg="blue",
                                  fg='white',
                                  command=lambda: createPlayer('blue'))
        bluePlayerBtn.grid(row=3, column=0,columnspan = 4,  padx=5, pady=5, sticky=tk.N + tk.E + tk.W)
        redPlayerBtn = tk.Button(selectPlayersFrame, text="Crea el escenario para el jugador rojo", bg="red",
                                   fg='white',
                                   command=lambda: createPlayer('red'))
        redPlayerBtn.grid(row=4, column=0,columnspan = 4,  padx=5, pady=5, sticky=tk.N + tk.E + tk.W)

        pinkPlayerBtn = tk.Button(selectPlayersFrame, text="Crea el escenario para el jugador rosa", bg="pink", fg='black',
                                command = lambda: createPlayer('pink'))
        pinkPlayerBtn.grid(row=5, column=0,columnspan = 4,  padx=5, pady=5, sticky=tk.N + tk.E + tk.W)

# me contecto a los drones del enjambre
def connect ():
    global swarm
    global connected, dron, dronIcons
    global altitudes, modos, points, distances
    global telemetriaFrame, controlesFrame, pointsFrame

    if not connected:

        if connectOption.get () == 'Simulation':
            # nos conectaremos a los simuladores de los drones
            connectionStrings = []
            base = 5763
            for i in range(0, numPlayers):
                port = base + i * 10
                connectionStrings.append('tcp:127.0.0.1:' + str(port))
            baud = 115200
        else:
            # nos conectaremos a los drones reales a través de las radios de telemetría
            # los puertos ya los hemos indicado y estan en comPorts, separados por comas
            connectionStrings = comPorts.split(',')
            baud = 57600


        colors = ['yellow', 'blue', 'red', 'pink']
        altitudes = []
        modos = []
        distances = []


        dronIcons = [None, None, None, None]

        textColor = 'white'

        for i in range(0, numPlayers):
            # identificamos el dron
            dron = swarm[i]
            dron.changeNavSpeed(1) # que vuele a 1 m/s
            # nos conectamos
            print ('voy a onectar ', i, connectionStrings[i], baud)
            dron.connect(connectionStrings[i], baud)
            print ('conectado')
            if i == 3:
                textColor = 'black'
            # colocamos los botones para aterrizar y cambiar de modo, cada uno con el color que toca
            tk.Button(controlesFrame, bg=colors[i], fg=textColor, text='Aterrizar',
                      command=lambda d=swarm[i]: d.Land(blocking=False)) \
                .grid(row=0, column=i, padx=2, pady=2, sticky=tk.N + tk.E + tk.W)
            tk.Button(controlesFrame, bg=colors[i], fg=textColor, text='Modo guiado',
                      command=lambda d=swarm[i]: d.setFlightMode('GUIDED')) \
                .grid(row=1, column=i, padx=2, pady=2, sticky=tk.N + tk.E + tk.W)
            tk.Button(controlesFrame, bg=colors[i], fg=textColor, text='Modo break',
                      command=lambda d=swarm[i]: d.setFlightMode('BRAKE')) \
                .grid(row=2, column=i, padx=2, pady=2, sticky=tk.N + tk.E + tk.W)
            # colocamos las labels para mostrar las alturas de los drones
            altitudes.append(tk.Label(telemetriaFrame, text='', borderwidth=1, relief="solid"))
            altitudes[-1].grid(row=0, column=i, padx=2, pady=2, sticky=tk.N + tk.E + tk.W)
            modos.append(tk.Label(telemetriaFrame, text='', borderwidth=1, relief="solid"))
            modos[-1].grid(row=1, column=i, padx=2, pady=2, sticky=tk.N + tk.E + tk.W)
            distances.append(tk.Label(telemetriaFrame, text='', borderwidth=1, relief="solid"))
            distances[-1].grid(row=3, column=i, padx=2, pady=2, sticky=tk.N + tk.E + tk.W)



            # solicitamos datos de telemetria del dron
            dron.send_telemetry_info(processTelemetryInfo)

        connected = True
        connectBtn['bg'] = 'green'

# evantos que no trata el Autopilot Service y se tratan aqui:
def startDrawing (id ):
    global drawingAction
    print ('start drawing')
    drawingAction [id] = 'startDrawing'

def stopDrawing (id):
    global drawingAction
    drawingAction [id] = 'nothing'

def startRemovingDrawing (id):
    global drawingAction
    drawingAction[id] = 'remove'

def stopRemovingDrawing (id):
    global drawingAction
    drawingAction[id] = 'nothing'

def removeAll (id):
    global traces
    for item in traces[id]:
        if  item['marker'] != None:
                item['marker'].delete()
    traces[id] = []

################### Funciones para supervisar el multi escenario #########################

def superviseBtnClick ():

    # quitamos los otros dos frames
    selectFrame.grid_forget()
    createFrame.grid_forget()
    # visualizamos el frame de creación
    superviseFrame.grid(row=1, column=0, columnspan=3, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)

    createBtn['text'] = 'Crear'
    createBtn['fg'] = 'black'
    createBtn['bg'] = 'dark orange'

    selectBtn['text'] = 'Seleccionar'
    selectBtn['fg'] = 'black'
    selectBtn['bg'] = 'dark orange'

    superviseBtn['text'] = 'Supervisando...'
    superviseBtn['fg'] = 'white'
    superviseBtn['bg'] = 'green'

def adjustParameters():
    global swarm, colors

    # Crear la ventana para gestionar los parámetros de los drones
    parameterManagementWindow = tk.Toplevel()
    parameterManagementWindow.title("Gestión de parámetros")

    # Configuración de la ventana
    parameterManagementWindow.rowconfigure(0, weight=1)
    parameterManagementWindow.rowconfigure(1, weight=1)

    # Crear una sección para cada dron en un LabelFrame
    for i in range(len(swarm)):
        # Asignar un color cíclico utilizando el índice del dron
        color = colors[i % len(colors)]  # Usa el módulo para repetir los colores

        # Crear el LabelFrame para el dron con el color correspondiente
        dronFrame = tk.LabelFrame(parameterManagementWindow, text=f"Dron {i+1}", padx=10, pady=10, font=("Helvetica", 10, "bold"), bg=color)
        dronFrame.grid(row=0, column=i, padx=10, pady=10)

        # Entrada para altura
        altura_label = tk.Label(dronFrame, text="Altura en metros:", font=("Helvetica", 9))
        altura_label.grid(row=0, column=1, pady=5, sticky="n")

        altura_entry = tk.Entry(dronFrame, width=5, font=("Helvetica", 10))
        altura_entry.grid(row=0, column=2, pady=5)

        # Botón "Armar Dron"
        tk.Button(dronFrame, text="Armar", bg="dark orange", fg="white", font=("Helvetica", 10, "bold"),
                    command=lambda idx=i: swarm[idx].arm()).grid(row=0, column=0, pady=5)

        # Botón "Despegar"
        tk.Button(dronFrame, text="Despegar", bg="dark orange", fg="white", font=("Helvetica", 10, "bold"),
                    command=lambda idx=i: swarm[idx].takeOff(int(altura_entry.get()) if altura_entry.get().isdigit() else 3)).grid(row=0, column=3, pady=5)

        # Botón "Aterrizar Dron"
        tk.Button(dronFrame, text="Aterrizar Dron", bg="dark orange", fg="white", font=("Helvetica", 10, "bold"),
                    command=lambda idx=i: swarm[idx].Land()).grid(row=0, column=4, pady=5)

        # Crear la cuadrícula de controles direccionales (3x3)
        directions = [
            ("NW", "NorthWest"), ("N", "North"), ("NE", "NorthEast"),
            ("W", "West"), ("Stop", "Stop"), ("E", "East"),
            ("SW", "SouthWest"), ("S", "South"), ("SE", "SouthEast")
        ]

        for row in range(3):  # Filas
            for col in range(3):  # Columnas
                label, command = directions[row * 3 + col]
                tk.Button(dronFrame, text=label, bg="dark orange", fg="black", font=("Helvetica", 12, "bold"),
                            width=5, height=2, command=lambda idx=i, cmd=command: swarm[idx].go(cmd)) \
                    .grid(row=row + 1, column=col, padx=5, pady=5)

    # Botón para cerrar la ventana
    tk.Button(parameterManagementWindow, text="Cerrar", bg="dark orange", fg="white", font=("Helvetica", 10, "bold"),
                command=parameterManagementWindow.destroy).grid(row=1, column=0, columnspan=len(swarm), pady=10)


def selectScenario():
    global  selectedScenario, numPlayers
    # limpio el mapa
    clear()
    # cargamos el fichero json con el multi escenario seleccionado (el que está en la posición current de la lista9
    f = open(scenarios[current]['name'] +'.json')
    selectedScenario = json.load (f)
    # dibujo el escenario
    drawScenario(selectedScenario)
    # habilito el botón para enviar el escenario al enjambre
    sendBtn['state'] = tk.NORMAL

def genetateTargets ():
    global targets
    geod = Geodesic.WGS84
    targets = [[], [], [], []]

    zone = [[41.2764287, 1.9882538], [41.2766081, 1.9890015], [41.2763893, 1.9891083], [41.2762034, 1.9883497]]
    selectedScenario = {'numPlayers': 2,
                        'base': '2V',
                        'zones':
                            [
                                [[41.2764287, 1.9882538], [41.2766081, 1.9890015], [41.2763893, 1.9891083], [41.2762034, 1.9883497]],
                                [[41.2764287, 1.9882538], [41.2766081, 1.9890015], [41.2763893, 1.9891083], [41.2762034, 1.9883497]]],
                        'data':
                            [73.19422085567864, 35.03624543766917],
                        'obstacles':
                            [
                                [[41.2764166, 1.98829], [41.2763284, 1.9883256], [41.276342, 1.9883718], [41.27640249, 1.98834501], [41.2764191, 1.9884069], [41.2764441, 1.988394]],
                                [[41.27628356, 1.98834434], [41.2762941, 1.9883899], [41.2762483, 1.9884101], [41.2762629, 1.9884704], [41.2762357, 1.9884831], [41.276211, 1.9883789]],
                                [[41.27638486, 1.98839799], [41.27628608, 1.98844157], [41.2762982, 1.9884919], [41.2763975, 1.9884443]],
                                [[41.2764413, 1.9885133], [41.2763672, 1.9885468], [41.2763511, 1.9886012], [41.2763874, 1.9886173], [41.2764574, 1.988575]],
                                [[41.27646952, 1.98864006], [41.27641157, 1.98867895], [41.27642164, 1.98871382], [41.27645843, 1.98868699], [41.27647002, 1.98872589], [41.27643298, 1.98875271], [41.2764426, 1.9887856], [41.2764993, 1.9887507]],
                                [[41.276537, 1.9887668], [41.2764695, 1.9888094], [41.2764798, 1.9888446], [41.276525, 1.9888124], [41.27654234, 1.98887073], [41.27655972, 1.98885765]],
                                [[41.27651361, 1.98885748], [41.27647128, 1.98888481], [41.27645138, 1.98882144], [41.27642668, 1.9888372], [41.27645541, 1.98892772], [41.27652142, 1.98888548]],
                                [[41.2763879, 1.9888292], [41.2763627, 1.9888406], [41.276406, 1.9890129], [41.2764297, 1.9889901]],
                                [[41.2763123, 1.9885468], 2],
                                [[41.2763057, 1.9886193], 2],
                                [[41.2763581, 1.9887232], 2],
                                [[41.2765391, 1.988972], 3.5]
                            ]
                        }
    obstacles = \
        [
            [
                [[41.2764166, 1.98829], [41.2763284, 1.9883256], [41.276342, 1.9883718], [41.27640249, 1.98834501], [41.2764191, 1.9884069], [41.2764441, 1.988394]],
                [[41.27628356, 1.98834434], [41.2762941, 1.9883899], [41.2762483, 1.9884101], [41.2762629, 1.9884704], [41.2762357, 1.9884831], [41.276211, 1.9883789]],
                [[41.27638486, 1.98839799], [41.27628608, 1.98844157], [41.2762982, 1.9884919], [41.2763975, 1.9884443]],
                [[41.2764413, 1.9885133], [41.2763672, 1.9885468], [41.2763511, 1.9886012], [41.2763874, 1.9886173], [41.2764574, 1.988575]],
                [[41.27646952, 1.98864006], [41.27641157, 1.98867895], [41.27642164, 1.98871382], [41.27645843, 1.98868699], [41.27647002, 1.98872589], [41.27643298, 1.98875271], [41.2764426, 1.9887856], [41.2764993, 1.9887507]],
                [[41.276537, 1.9887668], [41.2764695, 1.9888094], [41.2764798, 1.9888446], [41.276525, 1.9888124], [41.27654234, 1.98887073], [41.27655972, 1.98885765]],
                [[41.27651361, 1.98885748], [41.27647128, 1.98888481], [41.27645138, 1.98882144], [41.27642668, 1.9888372], [41.27645541, 1.98892772], [41.27652142, 1.98888548]],
                [[41.2763879, 1.9888292], [41.2763627, 1.9888406], [41.276406, 1.9890129], [41.2764297, 1.9889901]],
                [[41.2763123, 1.9885468], 2],
                [[41.2763057, 1.9886193], 2],
                [[41.2763581, 1.9887232], 2],
                [[41.2765391, 1.988972], 3.5]
            ],
            [
                 [[41.27650781162112, 1.9886903201452626], [41.27641961162252, 1.9887259196063753], [41.27643321162232, 1.988772119689474], [41.27649370162136, 1.9887453300590565], [41.27651031162109, 1.9888072201605373], [41.27653531162068, 1.9887943203132816]],
                 [[41.27637477162324, 1.9887446593324132], [41.27638531162308, 1.9887902193968117], [41.27633951162382, 1.9888104191169844], [41.27635411162357, 1.9888707192061863], [41.276326911624004, 1.9888834190399987], [41.27630221162441, 1.988779218889086]],
                 [[41.276476071621644, 1.9887983099513344], [41.27637729162321, 1.9888418893478168], [41.27638941162302, 1.9888922194218617], [41.276488711621425, 1.9888446200285677]],
                 [[41.27653251162074, 1.988913620296179], [41.27645841162192, 1.9889471198434392], [41.27644231162217, 1.9890015197450697], [41.27647861162159, 1.9890176199668554], [41.27654861162048, 1.9889753203945457]],
                 [[41.276560731620286, 1.989040380468592], [41.276502781621204, 1.9890792701145315], [41.27651285162105, 1.9891141401760544], [41.276549641620456, 1.9890873104008313], [41.27656123162026, 1.9891262104716543], [41.276524191620865, 1.9891530302453437], [41.27653381162072, 1.989185920304119], [41.27659051161982, 1.9891510206505474]],
                 [[41.2766282116192, 1.9891671208808863], [41.276560711620284, 1.989209720468471], [41.27657101162012, 1.9892449205314062], [41.2766162116194, 1.9892127208075696], [41.27663355161912, 1.989271050913514], [41.27665093161886, 1.989257971019697]],
                 [[41.27660482161959, 1.989257800737981], [41.27656249162026, 1.9892851304793482], [41.276542591620576, 1.9892217603577624], [41.27651789162096, 1.9892375202068502], [41.27654662162051, 1.9893280403823854], [41.27661263161947, 1.989285800785694]],
                 [[41.276479111621576, 1.9892295199699137], [41.276453911621985, 1.989240919815944], [41.276497211621304, 1.9894132200805004], [41.27652091162091, 1.989390420225296]],
                 [[41.27640351162279, 1.9889471195080102], 2],
                 [[41.2763969116229, 1.9890196194676855], 2],
                 [[41.27644931162206, 1.9891235197878314], 2],
                 [[41.276630311619186, 1.9893723208937164], 3.5]
            ], [], []
        ]
    # los puntos que se generen aleatoriamente deben estar dentro
    # de la zona del dron 0

    polygon = Polygon([(zone[0][0], zone[0][1]),
                       (zone[1][0], zone[1][1]),
                       (zone[2][0], zone[2][1]),
                       (zone[3][0], zone[3][1])])

    lats = [zone[0][0], zone[1][0], zone[2][0], zone[3][0]]
    lons = [zone[0][1], zone[1][1], zone[2][1], zone[3][1]]

    # generaremos puntos aleatorios dentro de estos rangos
    minLat = min(lats)
    maxLat = max(lats)
    minLon = min(lons)
    maxLon = max(lons)
    random.seed(datetime.now().timestamp())
    for i in range (10):
        # generamos un punto aleatorio que este dentro de la zona y fuera de los obstaculos
        valid = False
        while not valid:

            targetLat = random.uniform(minLat, maxLat)
            targetLon = random.uniform(minLon, maxLon)
            point = Point(targetLat, targetLon)
            valid = True

            if not polygon.contains(point):
                valid = False
            else:
                j = 0
                while j < len (obstacles[0]) and valid:
                    if len(obstacles[0][j]) > 2:
                        polygon2 = Polygon(obstacles[0][j])
                        if polygon2.contains(point):
                            valid = False
                    else:
                        if haversine(targetLat, targetLon, obstacles[0][j][0][0], obstacles[0][j][0][1]) <= obstacles[0][j][1]:
                            valid = False
                    j = j+1
        print ('ya tengo otro ',targetLat, targetLon )
        targets[0].append((targetLat, targetLon))

        print('ya tengo otro ', targets[0])

def startCompetition ():
    global targets, nextTarget, targetIcon
    mixer.init()
    mixer.music.load('images/PacmanStartAudio.mp3')
    mixer.music.play()

    genetateTargets()
    nextTarget = [0,0,0,0]
    targetIcon = [None, None, None, None]
    for i in range (selectedScenario['numPlayers']):
        point = targets[i][0]
        targetIcon[i] = map_widget.set_marker(point[0], point[1], icon=diana, icon_anchor="center")

def end_game():
    global increment_button, startCompetitionBtn, showQRBtn
    # Deshabilitar el botón para evitar más clics
    increment_button.config(state=tk.DISABLED)
    startCompetitionBtn.config(state=tk.DISABLED)
    #showQRBtn.config(state=tk.DISABLED)
    # Mostrar la ventana con la animación
    show_animation()

# Función para mostrar la animación
def show_animation():
    global ventana
    # Crear una ventana nueva
    anim_window = Toplevel(ventana)
    anim_window.title("Juego Terminado")
    anim_window.geometry("700x400")  # Tamaño de la ventana
    anim_window.resizable(False, False)
    mixer.init()
    mixer.music.load('images/PacmanEating.mp3')
    mixer.music.play()

    # Agregar texto
    label_text = tk.Label(anim_window, text="¡Has alcanzado 5 puntos! El juego ha terminado.", font=("Arial", 16))
    label_text.pack(pady=10)

    global gif_frames
    ## Cargar la animación GIF
    gif_path = os.path.join("images", "comecocos.gif")   # Ruta al GIF
    gif_frames = []

    try:
        # Abrir el GIF y cargar todos los frames
        gif = Image.open(gif_path)
        while True:
            gif_frames.append(ImageTk.PhotoImage(gif.copy()))
            gif.seek(len(gif_frames))  # Mover al siguiente frame
    except EOFError:
        pass  # Fin del GIF

    # Etiqueta para mostrar los frames
    anim_label = tk.Label(anim_window)
    anim_label.pack()

    # Función para actualizar los frames del GIF
    def update_frame(index):
        frame = gif_frames[index]
        anim_label.config(image=frame)
        anim_window.after(100, update_frame, (index + 1) % len(gif_frames))  # Ciclar los frames
    # Iniciar la animación
    update_frame(0)
    # Botón para cerrar la ventana
    close_button = tk.Button(anim_window, text="Cerrar", command=anim_window.destroy)
    close_button.pack(pady=10)

# Función para incrementar el contador
def increment_score():
    global global_score, score_label
    global targetIcon
    # Eliminar todos los puntos del mapa
    if targetIcon:  # Verificar que targetIcon no está vacío
        for icon in targetIcon:
            try:
                icon.delete()  # Intentar eliminar cada marcador del mapa
            except AttributeError:
                print("Error al borrar un icono, puede que no exista o ya esté eliminado.")

    # Vaciar la lista después de eliminar los puntos
    targetIcon.clear()

    global_score += 1  #Incrementar la puntuación
    score_label.config(text=str(global_score))  # Actualizar el texto del contador
    if global_score >= 5:  # Si la puntuación llega a 5, termina el juego
        end_game()

def check_drop (id):
    global targetIcon, nextTarget, map_widget, diana, white, black, green
    global points


    distanceForSuccess = 1
    target = targets[id][nextTarget[id]]
    if haversine(positions[id][0], positions[id][1], target[0], target[1]) < distanceForSuccess:
         targetIcon[id].delete()

         targetIcon[id]=map_widget.set_marker(target[0], target[1], icon=white, icon_anchor="center")
         nextTarget[id] = nextTarget[id] + 1
         target = targets[id][nextTarget[id]]
         targetIcon[id]=map_widget.set_marker(target[0], target[1], icon=diana, icon_anchor="center")
         p = int (points[id]['text'])
         points[id]['text'] = str(p+1)

    else:
         targetIcon[id].delete()
         targetIcon[id] = map_widget.set_marker(target[0], target[1], icon=black, icon_anchor="center")
         nextTarget[id] = nextTarget[id] + 1
         targeta = targets[id][nextTarget[id]]
         targetIcon[id]=map_widget.set_marker(targeta[0], targeta[1], icon=diana, icon_anchor="center")

def showQR():
    global QRimg
    QRWindow = tk.Toplevel()
    QRWindow.title("Código QR para mobile web app")
    QRWindow.rowconfigure(0, weight=1)
    QRWindow.rowconfigure(1, weight=1)
    QRWindow.columnconfigure(0, weight=1)

    QRimg = Image.open("images/QR.png")
    QRimg = ImageTk.PhotoImage(QRimg)
    label = tk.Label(QRWindow, image=QRimg)
    label.grid(row=0, column=0, padx=5, pady=5, sticky=tk.N + tk.E +tk.S+ tk.W)

    closeBtn = tk.Button(QRWindow, text="Cerrar", bg="dark orange", command = lambda: QRWindow.destroy())
    closeBtn.grid(row=1, column=0, padx=5, pady=5, sticky=tk.N + tk.E +tk.S+tk.W)

    QRWindow.mainloop()

def crear_ventana():

    global map_widget
    global createBtn,selectBtn, superviseBtn, createFrame, name, selectFrame, scene, scenePic,scenarios, current
    global superviseFrame
    global prevBtn, nextBtn, sendBtn, connectBtn
    global scenarioCanvas
    global i_wp, e_wp
    global paths, fence, polys
    global connected
    global selectPlayersFrame
    global yellow, blue, red, pink, black, dronPictures
    global connectOption
    global playersCount
    global client
    global drawingAction, traces, dronLittlePictures
    global QRimg
    global colors
    global lock
    global target, positions, diana, green
    global pointsFrame, telemetriaFrame, controlesFrame
    global global_score, score_label
    global increment_button, startCompetitionBtn, showQRBtn

    playersCount = 0

    # Variable global para almacenar el puntaje
    global_score = 0  # Inicializar la puntuación global

    positions = [None, None, None, None]
    target = None

    connected = False
    # aqui indicare, para cada dron, si estamos pintando o no
    drawingAction = ['nothing']*4 # nothing, draw o remove
    # y aqui ire guardando los rastros
    traces = [[], [], [], []]

    # para guardar datos y luego poder borrarlos
    paths = []
    fence = []
    polys = []


    ventana = tk.Tk()
    ventana.title("Gestión de escenarios")
    ventana.geometry ('1900x1000')

    # El panel principal tiene una fila y dos columnas
    ventana.rowconfigure(0, weight=1)
    ventana.columnconfigure(0, weight=1)
    ventana.columnconfigure(1, weight=1)

    controlFrame = tk.LabelFrame(ventana, text = 'Control')
    controlFrame.grid(row=0, column=0, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)
    # El frame de control aparece en la primera columna
    controlFrame.rowconfigure(0, weight=1)
    controlFrame.rowconfigure(1, weight=1)
    controlFrame.columnconfigure(0, weight=1)
    controlFrame.columnconfigure(1, weight=1)
    controlFrame.columnconfigure(2, weight=1)


    # botones para crear/seleccionar/supervisar
    createBtn = tk.Button(controlFrame, text="Crear", bg="dark orange", command = createBtnClick)
    createBtn.grid(row=0, column=0, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)
    selectBtn = tk.Button(controlFrame, text="Seleccionar", bg="dark orange", command = selectBtnClick)
    selectBtn.grid(row=0, column=1,  padx=5, pady=5, sticky=tk.N + tk.E + tk.W)
    superviseBtn = tk.Button(controlFrame, text="Supervisar", bg="dark orange", command=superviseBtnClick)
    superviseBtn.grid(row=0, column=2,  padx=5, pady=5, sticky=tk.N + tk.E + tk.W)

    ################################# frame para crear escenario  ###################################################
    createFrame = tk.LabelFrame(controlFrame, text='Crear escenario')
    # la visualización del frame se hace cuando se clica el botón de crear
    #createFrame.grid(row=1, column=0,  columnspan=3, padx=5, pady=5, sticky=tk.N + tk.S + tk.E + tk.W)
    createFrame.rowconfigure(0, weight=1)
    createFrame.rowconfigure(1, weight=1)
    createFrame.rowconfigure(2, weight=1)
    createFrame.rowconfigure(3, weight=1)
    createFrame.rowconfigure(4, weight=1)
    createFrame.rowconfigure(5, weight=1)
    createFrame.rowconfigure(6, weight=1)
    createFrame.rowconfigure(7, weight=1)
    createFrame.rowconfigure(8, weight=1)
    createFrame.rowconfigure(9, weight=1)
    createFrame.columnconfigure(0, weight=1)

    tk.Label (createFrame, text='Escribe el nombre aquí')\
        .grid(row=0, column=0, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)
    # el nombre se usará para poner nombre al fichero con la imagen y al fichero json con el escenario
    name = tk.StringVar()
    tk.Entry(createFrame, textvariable=name)\
        .grid(row=1, column=0, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)

    selectPlayersFrame = tk.LabelFrame(createFrame, text='Jugadores')
    selectPlayersFrame.grid(row=2, column=0, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)
    selectPlayersFrame.rowconfigure(0, weight=1)
    selectPlayersFrame.rowconfigure(1, weight=1)
    selectPlayersFrame.rowconfigure(2, weight=1)
    selectPlayersFrame.rowconfigure(3, weight=1)
    selectPlayersFrame.rowconfigure(4, weight=1)
    selectPlayersFrame.rowconfigure(5, weight=1)
    selectPlayersFrame.rowconfigure(6, weight=1)

    selectPlayersFrame.columnconfigure(0, weight=1)
    selectPlayersFrame.columnconfigure(1, weight=1)
    selectPlayersFrame.columnconfigure(2, weight=1)
    selectPlayersFrame.columnconfigure(3, weight=1)
    tk.Label (selectPlayersFrame, text = 'Selecciona el número de jugadores').\
        grid(row=0, column=0, columnspan=4, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)
    tk.Button(selectPlayersFrame, text="1", bg="dark orange", command = lambda:  selectNumPlayers (1))\
        .grid(row=1, column=0, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)
    tk.Button(selectPlayersFrame, text="2", bg="dark orange", command=lambda: selectNumPlayers(2)) \
        .grid(row=1, column=1, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)
    tk.Button(selectPlayersFrame, text="3", bg="dark orange", command=lambda: selectNumPlayers(3)) \
        .grid(row=1, column=2, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)
    tk.Button(selectPlayersFrame, text="4", bg="dark orange", command=lambda: selectNumPlayers(4)) \
        .grid(row=1, column=3, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)

    inclusionFenceFrame = tk.LabelFrame (createFrame, text ='Definición de los límites del escenario')
    inclusionFenceFrame.grid(row=3, column=0, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)
    inclusionFenceFrame.rowconfigure(0, weight=1)
    inclusionFenceFrame.columnconfigure(0, weight=1)
    inclusionFenceFrame.columnconfigure(1, weight=1)
    # el fence de inclusión puede ser un poligono o un círculo
    # el parámetro 1 en el command indica que es fence de inclusion
    polyInclusionFenceBtn = tk.Button(inclusionFenceFrame, text="Polígono", bg="dark orange", command = lambda:  definePoly (1))
    polyInclusionFenceBtn.grid(row=0, column=0, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)
    circleInclusionFenceBtn = tk.Button(inclusionFenceFrame, text="Círculo", bg="dark orange", command = lambda:  defineCircle (1))
    circleInclusionFenceBtn.grid(row=0, column=1, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)

    # los obstacilos son fences de exclusión y pueden ser también polígonos o círculos
    # el parámetro 2 en el command indica que son fences de exclusión
    obstacleFrame = tk.LabelFrame(createFrame, text='Definición de los obstaculos del escenario')
    obstacleFrame.grid(row=4, column=0, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)
    obstacleFrame.rowconfigure(0, weight=1)
    obstacleFrame.columnconfigure(0, weight=1)
    obstacleFrame.columnconfigure(1, weight=1)

    polyObstacleBtn = tk.Button(obstacleFrame, text="Polígono", bg="dark orange", command = lambda: definePoly (2))
    polyObstacleBtn.grid(row=0, column=0, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)
    circleObstacleBtn = tk.Button(obstacleFrame, text="Círculo", bg="dark orange", command=lambda: defineCircle(2))
    circleObstacleBtn.grid(row=0, column=1, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)

    registerBtn = tk.Button(createFrame, text="Registra escenario", bg="dark orange", command = registerScenario)
    registerBtn.grid(row=5, column=0, padx=5, pady=5, sticky=tk.N +tk.E + tk.W)

    clearBtn = tk.Button(createFrame, text="Limpiar", bg="dark orange", command=clear)
    clearBtn.grid(row=6, column=0, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)

    ################################ frame para seleccionar escenarios ############################################
    selectFrame = tk.LabelFrame(controlFrame, text='Selecciona escenario')
    # la visualización del frame se hace cuando se clica el botón de seleccionar
    #selectFrame.grid(row=1, column=0,  columnspan=2, padx=5, pady=5, sticky=tk.N + tk.S + tk.E + tk.W)

    selectFrame.rowconfigure(0, weight=1)
    selectFrame.rowconfigure(1, weight=1)
    selectFrame.rowconfigure(2, weight=1)
    selectFrame.rowconfigure(3, weight=1)
    selectFrame.rowconfigure(4, weight=1)
    selectFrame.rowconfigure(5, weight=1)
    selectFrame.rowconfigure(6, weight=1)
    selectFrame.rowconfigure(7, weight=1)
    selectFrame.columnconfigure(0, weight=1)
    selectFrame.columnconfigure(1, weight=1)
    selectFrame.columnconfigure(2, weight=1)
    selectFrame.columnconfigure(3, weight=1)


    tk.Label (selectFrame, text = 'Selecciona el número de jugadores').\
        grid(row=0, column=0, columnspan=4, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)
    tk.Button(selectFrame, text="1", bg="dark orange", command = lambda:  selectScenarios (1))\
        .grid(row=1, column=0, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)
    tk.Button(selectFrame, text="2", bg="dark orange", command=lambda: selectScenarios(2)) \
        .grid(row=1, column=1, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)
    tk.Button(selectFrame, text="3", bg="dark orange", command=lambda: selectScenarios(3)) \
        .grid(row=1, column=2, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)
    tk.Button(selectFrame, text="4", bg="dark orange", command=lambda: selectScenarios(4)) \
        .grid(row=1, column=3, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)

    # en este canvas se mostrarán las imágenes de los escenarios disponibles
    scenarioCanvas = tk.Canvas(selectFrame, width=300, height=200, bg='grey')
    scenarioCanvas.grid(row = 2, column=0, columnspan=4, padx=5, pady=5)

    prevBtn = tk.Button(selectFrame, text="<<", bg="dark orange", command = showPrev)
    prevBtn.grid(row=3, column=0, padx=5, pady=5, sticky=tk.N +  tk.E + tk.W)
    selectScenarioBtn = tk.Button(selectFrame, text="Seleccionar", bg="dark orange", command = selectScenario)
    selectScenarioBtn.grid(row=3, column=1, columnspan = 2, padx=5, pady=5, sticky=tk.N + tk.S + tk.E + tk.W)
    nextBtn = tk.Button(selectFrame, text=">>", bg="dark orange", command = showNext)
    nextBtn.grid(row=3, column=3, padx=5, pady=5, sticky=tk.N +  tk.E + tk.W)

    # La función de cargar el multi escenario que hay en ese momento en los drones no está operativa aún
    loadBtn = tk.Button(selectFrame, text="Cargar el escenario que hay en el dron", bg="dark orange", state = tk.DISABLED, command=loadScenario)
    loadBtn.grid(row=4, column=0,columnspan = 4, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)

    # pequeño frame para configurar la conexión
    connectFrame = tk.Frame(selectFrame)
    connectFrame.grid(row=5, column=0, columnspan=4, padx=5, pady=3, sticky=tk.N  + tk.E + tk.W)
    connectFrame.rowconfigure(0, weight=1)
    connectFrame.rowconfigure(1, weight=1)
    connectFrame.rowconfigure(2, weight=1)
    connectFrame.columnconfigure(0, weight=1)
    connectFrame.columnconfigure(1, weight=1)

    connectBtn = tk.Button(connectFrame, text="Conectar", bg="dark orange", command = connect)
    connectBtn.grid(row=0, column=0, rowspan=2, padx=5, pady=3, sticky=tk.N + tk.S + tk.E + tk.W)

    # se puede elegir entre conectarse al simulador o conectarse al dron real
    # en el segundo caso hay que especificar en qué puertos están conectadas las radios de telemetría
    connectOption = tk.StringVar()
    connectOption.set('Simulation')  # por defecto se trabaja en simulación
    option1 = tk.Radiobutton(connectFrame, text="Simulación", variable=connectOption, value="Simulation")
    option1.grid(row=0, column=1, padx=5, pady=3, sticky=tk.N + tk.S + tk.W)

    # se activa cuando elegimos la conexión en modo producción. Aquí especificamos los puertos en los que están
    # conectadas las radios de telemetría
    def ask_Ports():
        global comPorts
        comPorts = askstring('Puertos', "Indica los puertos COM separados por comas (por ejemplo: 'COM3,COM21,COM7')")

    option2 = tk.Radiobutton(connectFrame, text="Producción", variable=connectOption, value="Production",command=ask_Ports)
    option2.grid(row=1, column=1, padx=5, pady=3, sticky=tk.N + tk.S + tk.W)

    sendBtn = tk.Button(selectFrame, text="Enviar escenario", bg="dark orange", command=sendScenario)
    sendBtn.grid(row=6, column=0,columnspan = 4, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)

    deleteBtn = tk.Button(selectFrame, text="Eliminar escenario", bg="red", fg = 'white', command = deleteScenario)
    deleteBtn.grid(row=7, column=0, columnspan = 4, padx=5, pady=5, sticky=tk.N +  tk.E + tk.W)

    ########################## frame para supervisar ####################################################
    superviseFrame = tk.LabelFrame(controlFrame, text='Supervisar vuelos')
    # la visualización del frame se hace cuando se clica el botón de supervisar
    # superviseFrame.grid(row=1, column=0,  columnspan=3, padx=5, pady=5, sticky=tk.N + tk.S + tk.E + tk.W)

    superviseFrame.rowconfigure(0, weight=1)
    superviseFrame.rowconfigure(1, weight=1)
    superviseFrame.rowconfigure(2, weight=1)
    superviseFrame.rowconfigure(3, weight=1)
    superviseFrame.rowconfigure(4, weight=1)

    superviseFrame.columnconfigure(0, weight=1)
    superviseFrame.columnconfigure(1, weight=1)
    superviseFrame.columnconfigure(2, weight=1)
    superviseFrame.columnconfigure(3, weight=1)

    parametersBtn = tk.Button(superviseFrame, text="Control Drones", bg="dark orange", command=adjustParameters)
    parametersBtn.grid(row=0, column=0, columnspan=4, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)
    # debajo de este label colocaremos botones para aterrizar los drones.
    # los colocaremos cuando sepamos cuántos drones tenemos en el enjambre

    controlesFrame = tk.LabelFrame(superviseFrame, text='Controles')
    controlesFrame.grid(row=1, column=0, columnspan=4, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)
    controlesFrame.rowconfigure(0, weight=1)
    controlesFrame.rowconfigure(1, weight=1)
    controlesFrame.rowconfigure(3, weight=1)
    controlesFrame.columnconfigure(0, weight=1)
    controlesFrame.columnconfigure(1, weight=1)
    controlesFrame.columnconfigure(2, weight=1)
    controlesFrame.columnconfigure(3, weight=1)

    # debajo de este label colocaremos las alturas en las que están los drones
    # las colocaremos cuando sepamos cuántos drones tenemos en el enjambre
    telemetriaFrame = tk.LabelFrame(superviseFrame, text='Telemetría (altitud y modo de vuelo)')
    telemetriaFrame.grid(row=2, column=0, columnspan=4, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)
    telemetriaFrame.rowconfigure(0, weight=1)
    telemetriaFrame.rowconfigure(1, weight=1)
    telemetriaFrame.rowconfigure(2, weight=1)
    telemetriaFrame.rowconfigure(3, weight=1)
    telemetriaFrame.columnconfigure(0, weight=1)
    telemetriaFrame.columnconfigure(1, weight=1)
    telemetriaFrame.columnconfigure(2, weight=1)
    telemetriaFrame.columnconfigure(3, weight=1)

    tk.Label(telemetriaFrame, text='Distancia al Pacman') \
        .grid(row=2, column=0, columnspan=4, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)



    #showQRBtn = tk.Button(superviseFrame, text="Mostrar código QR de mobile web APP", bg="dark orange", command=showQR)
    #showQRBtn.grid(row=3, column=0, columnspan=4, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)

    startCompetitionBtn = tk.Button(superviseFrame, text="Crear Punto Aleatorio", bg="dark orange", command=startCompetition)
    startCompetitionBtn.grid(row=4, column=0, columnspan=4, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)

    imglogo = Image.open('images/logo.png')
    logo_resized = imglogo.resize((400, 250))
    logo = ImageTk.PhotoImage(logo_resized)
    logo_label = tk.Label(superviseFrame, image=logo)
    logo_label.image = logo
    logo_label.grid(row=6, column=0, padx=4, pady=4, sticky=tk.N + tk.E + tk.W)

    pointsFrame = tk.LabelFrame(superviseFrame, text='Puntuación')
    pointsFrame.grid(row=5, column=0, columnspan=4, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)
    pointsFrame.rowconfigure(0, weight=1)
    pointsFrame.rowconfigure(1, weight=1)
    pointsFrame.rowconfigure(2, weight=1)
    pointsFrame.columnconfigure(0, weight=1)


    # Crear la etiqueta para mostrar el puntaje inicial
    score_label = tk.Label(pointsFrame, text=str(global_score), font=("Arial", 25), fg="black", borderwidth=1,relief="solid")
    score_label.grid(row=0, column=0, padx=4, pady=4, sticky=tk.N + tk.E + tk.W)

    # Crear el botón para incrementar el puntaje
    increment_button = tk.Button(pointsFrame, text="Sumar Punto", bg="dark orange", command=increment_score)
    increment_button.grid(row=1, column=0, padx=4, pady=4, sticky=tk.N + tk.E + tk.W)

    #tambien ponemos el logo del comecocos





    #################### Frame para el mapa, en la columna de la derecha #####################
    mapaFrame = tk.LabelFrame(ventana, text='Mapa')
    mapaFrame.grid(row=0, column=1, padx=5, pady=5, sticky=tk.N + tk.S + tk.E + tk.W)
    mapaFrame.rowconfigure(0, weight=1)
    mapaFrame.rowconfigure(1, weight=1)
    mapaFrame.columnconfigure(0, weight=1)

    # creamos el widget para el mapa
    map_widget = tkintermapview.TkinterMapView(mapaFrame, width=1400, height=1000, corner_radius=0)
    map_widget.grid(row=1, column=0, padx=5, pady=5)
    map_widget.set_tile_server("https://mt0.google.com/vt/lyrs=s&hl=en&x={x}&y={y}&z={z}&s=Ga", max_zoom=22)
    map_widget.set_position(41.2764478, 1.9886568)  # Coordenadas del dronLab
    map_widget.set_zoom(20)


    # indicamos que capture los eventos de click sobre el mouse
    map_widget.add_right_click_menu_command(label="Cierra el fence", command=closeFence, pass_coords=True)
    map_widget.add_left_click_map_command(getFenceWaypoint)

    # ahora cargamos las imagenes de los iconos que vamos a usar

    # iconos para representar cada dron (circulo de color) y para marcar su rastro (círculo más pequeño del mismo color)
    im = Image.open("images/pacman.png")
    im_resized = im.resize((20, 20), Image.LANCZOS)
    yellow = ImageTk.PhotoImage(im_resized)
    im_resized_plus = im.resize((10, 10), Image.LANCZOS)
    littleYellow = ImageTk.PhotoImage(im_resized_plus)

    im = Image.open("images/blueghost.png")
    im_resized = im.resize((20, 20), Image.LANCZOS)
    blue = ImageTk.PhotoImage(im_resized)
    im_resized_plus = im.resize((10, 10), Image.LANCZOS)
    littleBlue = ImageTk.PhotoImage(im_resized_plus)

    im = Image.open("images/redghost.png")
    im_resized = im.resize((20, 20), Image.LANCZOS)
    red = ImageTk.PhotoImage(im_resized)
    im_resized_plus = im.resize((10, 10), Image.LANCZOS)
    littleRed = ImageTk.PhotoImage(im_resized_plus)


    im = Image.open("images/pinkghost.png")
    im_resized = im.resize((20, 20), Image.LANCZOS)
    pink = ImageTk.PhotoImage(im_resized)
    im_resized_plus = im.resize((10, 10), Image.LANCZOS)
    littlePink = ImageTk.PhotoImage(im_resized_plus)


    im = Image.open("images/black.png")
    im_resized = im.resize((20, 20), Image.LANCZOS)
    black = ImageTk.PhotoImage(im_resized)

    im = Image.open("images/targetIcon.png")
    im_resized = im.resize((30, 30), Image.LANCZOS)
    diana = ImageTk.PhotoImage(im_resized)

    dronPictures = [yellow, blue, red, pink]
    colors =['yellow', 'blue', 'red', 'pink']
    # para dibujar los rastros
    dronLittlePictures = [littleYellow, littleBlue, littleRed, littlePink]

    '''# nos conectamos al broker para recibir las ordenes de los que vuelan con la web app
    clientName = "multiPlayerDash" + str(random.randint(1000, 9000))
    client = mqtt.Client(clientName,transport="websockets")


    broker_address = "dronseetac.upc.edu"
    broker_port = 8000

    client.username_pw_set(
        'dronsEETAC', 'mimara1456.'
    )
    print('me voy a conectar')
    client.connect(broker_address, broker_port )
    print('Connected to dronseetac.upc.edu:8000')

    client.on_message = on_message
    client.on_connect = on_connect
    client.connect(broker_address, broker_port)

    # me subscribo a cualquier mensaje  que venga del autopilot service
    client.subscribe('mobileApp/multiPlayerDash/#')
    client.loop_start()
    # para garantizar acceso excluyente a las estructuras para pintar el rastro
    lock = threading.Lock()'''

    return ventana


if __name__ == "__main__":
    ventana = crear_ventana()
    ventana.mainloop()
