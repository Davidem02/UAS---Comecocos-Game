import tkinter as tk
from tkinter import messagebox
class ParameterManager:
    # con esta clase gestionamos los parámetros de un dron
    def __init__(self, window, swarm, pos):
        self.window = window
        self.swarm = swarm
        self.pos = pos
        self.on_off = 0 # indica si el geofence está habilitado (1) o no (0)
        # preparo el color correspondiente al dron (identificado del 0 en adelante)
        color = ['yellow', 'blue', 'red', 'pink'][pos]


        self.managementFrame = tk.LabelFrame (window, text = 'Dron '+str(pos+1), fg=color)
        self.managementFrame.rowconfigure(0, weight=1)
        self.managementFrame.rowconfigure(1, weight=1)
        self.managementFrame.rowconfigure(2, weight=1)
        self.managementFrame.rowconfigure(3, weight=1)
        self.managementFrame.rowconfigure(4, weight=1)
        self.managementFrame.rowconfigure(5, weight=1)
        self.managementFrame.rowconfigure(6, weight=1)
        self.managementFrame.rowconfigure(7, weight=1)
        self.managementFrame.rowconfigure(8, weight=1)
        self.managementFrame.rowconfigure(9, weight=1)


        self.managementFrame.columnconfigure(0, weight=1)
        self.managementFrame.columnconfigure(1, weight=1)

        # muestro los diferentes parámetros que quiero poder modificar

        tk.Label(self.managementFrame, text='FENCE_ENABLE') \
            .grid(row=0, column=0, padx=2, pady=2, sticky=tk.N + tk.E + tk.W)
        self.on_offBtn = tk.Button(self.managementFrame, text = 'OFF', bg = 'red', fg = 'white', command = self.on_off_btnClick)
        self.on_offBtn.grid(row=0, column=1, padx=2, pady=2, sticky=tk.N + tk.E + tk.W)

        tk.Label(self.managementFrame, text='FENCE_ACTION') \
            .grid(row=1, column=0, padx=2, pady=2, sticky=tk.N + tk.E + tk.W)
        self.fence_action_options = ["Break", "Land", "RTL"]
        self.fence_action_option = tk.StringVar(self.managementFrame)
        self.fence_action_option.set("Break")
        self.fence_action_option_menu = tk.OptionMenu(self.managementFrame, self.fence_action_option, *self.fence_action_options)
        self.fence_action_option_menu.grid(row=1, column=1, padx=2, pady=2, sticky=tk.N + tk.E + tk.W)

        tk.Label(self.managementFrame, text='RTL_ALT') \
            .grid(row=2, column=0, padx=2, pady=2, sticky=tk.N + tk.E + tk.W)

        self.RTL_ALT_Sldr = tk.Scale(self.managementFrame, label="RTL_ALT", resolution=1, from_=0, to=10, tickinterval=2,
                            orient=tk.HORIZONTAL)
        self.RTL_ALT_Sldr.grid(row=2, column=0, columnspan = 2, padx=5, pady=3, sticky=tk.N + tk.S + tk.E + tk.W)

        self.FENCE_MARGIN_Sldr = tk.Scale(self.managementFrame, label="FENCE_MARGIN", resolution=1, from_=0, to=10, tickinterval=2,
                            orient=tk.HORIZONTAL)
        self.FENCE_MARGIN_Sldr.grid(row=3, column=0, columnspan = 2, padx=5, pady=3, sticky=tk.N + tk.S + tk.E + tk.W)

        self.PILOT_SPEED_UP_Sldr = tk.Scale(self.managementFrame, label="PILOT_SPEED_UP", resolution=50, from_=50, to=200,
                                          tickinterval=50,
                                          orient=tk.HORIZONTAL)
        self.PILOT_SPEED_UP_Sldr.grid(row=4, column=0, columnspan=2, padx=5, pady=3, sticky=tk.N + tk.S + tk.E + tk.W)

        self.FENCE_ALT_MAX_Sldr = tk.Scale(self.managementFrame, label="FENCE_ALT_MAX", resolution=1, from_=1,
                                            to=10,
                                            tickinterval=2,
                                            orient=tk.HORIZONTAL)
        self.FENCE_ALT_MAX_Sldr.grid(row=5, column=0, columnspan=2, padx=5, pady=3, sticky=tk.N + tk.S + tk.E + tk.W)
        # este parámetro es el que determina la acción que se realiza al colocar el swith de los modos de vuelo de la emisora
        # en la posición inferior
        tk.Label(self.managementFrame, text='FLTMODE6') \
            .grid(row=6, column=0, padx=2, pady=2, sticky=tk.N + tk.E + tk.W)
        self.switch_action_options = ["Land", "RTL"]
        self.switch_action_option = tk.StringVar(self.managementFrame)
        self.switch_action_option.set("Land")
        self.switch_action_option_menu = tk.OptionMenu(self.managementFrame, self.switch_action_option,
                                                      *self.switch_action_options)
        self.switch_action_option_menu.grid(row=6, column=1, padx=2, pady=2, sticky=tk.N + tk.E + tk.W)

        self.NAV_SPEED_Sldr = tk.Scale(self.managementFrame, label="NAV_SPEED", resolution=1, from_=1,
                                            to=10,
                                            tickinterval=1,
                                            orient=tk.HORIZONTAL)
        self.NAV_SPEED_Sldr.grid(row=7, column=0, columnspan=2, padx=5, pady=3, sticky=tk.N + tk.S + tk.E + tk.W)


        # acciones que quiero poder hacer con los parámetros
        # leer los valores que tiene el dron en ese momento
        tk.Button(self.managementFrame, text='Leer valores', bg="dark orange", command=self.read_params) \
            .grid(row=8, column=0, padx=2, pady=2, sticky=tk.N + tk.E + tk.W)
        # enviar al dron los valores que he seleccionado
        tk.Button(self.managementFrame, text='Enviar valores', bg="dark orange", command=self.write_params) \
            .grid(row=8, column=1, padx=2, pady=2, sticky=tk.N + tk.E + tk.W)
        # en el caso del primer dron quiero poder copiar sus valores en todos los demás
        if pos == 0:
            tk.Button(self.managementFrame, text='Copiar valores en todos los drones', bg="dark orange",
                      command=self.copy_params) \
                .grid(row=9, column=0, columnspan=2, padx=2, pady=2, sticky=tk.N + tk.E + tk.W)
        else:
            # en el respo de los casos simplemente pongo un botón invisible para que se vean todos los managers alineados
            b = tk.Button(self.managementFrame, state=tk.DISABLED, bd=0)
            b.grid(row=9, column=0, columnspan=2, padx=2, pady=2, sticky=tk.N + tk.E + tk.W)

    # Esto se activa si pulso el boton de activar/desactivar el geofence
    def on_off_btnClick (self):
        if self.on_off == 0:
            self.on_off = 1
            self.on_offBtn['text'] = 'ON'
            self.on_offBtn['bg'] = 'green'
        else:
            self.on_off = 0
            self.on_offBtn['text'] = 'OFF'
            self.on_offBtn['bg'] = 'red'



    def buildFrame (self):
        self.read_params()
        return self.managementFrame

    # me guardo la lista de managers porque tengo que poder enviar info de unos a otros
    def setManagers (self, managers):
        self.managers = managers

    # aqui voy a leer del dron los valores de los parámetros de interés
    def read_params (self):
        parameters = [
            "RTL_ALT",
            "PILOT_SPEED_UP",
            "FENCE_ACTION",
            "FENCE_ENABLE",
            "FENCE_MARGIN",
            "FENCE_ALT_MAX",
            "FLTMODE6"
        ]
        result = self.swarm[self.pos].getParams(parameters)
        # coloco cada valor en su sitio
        # RTL_ALT viene en cm
        self.RTL_ALT_Sldr.set (int(result [0]['RTL_ALT']/100))
        self.PILOT_SPEED_UP_Sldr.set (result[1]['PILOT_SPEED_UP'])
        self.FENCE_MARGIN_Sldr.set(result[4]['FENCE_MARGIN'])
        self.FENCE_ALT_MAX_Sldr.set(result[5]['FENCE_ALT_MAX'])
        self.fence_action_option.set([None,'RTL', 'Land', None, 'Break'][int(result[2]['FENCE_ACTION'])])
        if int(result[6]['FLTMODE6']) == 6:
            self.switch_action_option.set ('RTL')
        elif int(result[6]['FLTMODE6']) == 9:
            self.switch_action_option.set('Land')
        if result[3]['FENCE_ENABLE'] == 0:
            self.on_off = 0
            self.on_offBtn['text'] = 'OFF'
            self.on_offBtn['bg'] = 'red'
        else:
            self.on_off = 1
            self.on_offBtn['text'] = 'ON'
            self.on_offBtn['bg'] = 'green'
        self.NAV_SPEED_Sldr.set (self.swarm[self.pos].navSpeed)
    # escribo en el dron los valores seleccionados
    def write_params (self):
        if self.switch_action_option.get () == 'Land':
            switch_option = 9
        elif self.switch_action_option.get () == 'RTL':
            switch_option = 6
        parameters = [
            {'ID': "FENCE_ENABLE", 'Value': float(self.on_off)},
            {'ID': "FENCE_ACTION", 'Value': float([None,'RTL', 'Land', None, 'Break'].index(self.fence_action_option.get()))},
            {'ID': "PILOT_SPEED_UP", 'Value': float(self.PILOT_SPEED_UP_Sldr.get())},
            {'ID': "PILOT_SPEED_DN", 'Value': 0}, # Para que use el mismo valor que se ha fijado para UP
            {'ID': "RTL_ALT", 'Value': float(self.RTL_ALT_Sldr.get()*100)},
            {'ID': "FENCE_MARGIN", 'Value': float(self.FENCE_MARGIN_Sldr.get())},
            {'ID': "FENCE_ALT_MAX", 'Value': float(self.FENCE_ALT_MAX_Sldr.get())},
            {'ID': "FLTMODE6", 'Value': float(switch_option)}
        ]
        self.swarm[self.pos].setParams(parameters)
        self.swarm[self.pos].navSpeed = float(self.NAV_SPEED_Sldr.get())
        #self.swarm[self.pos].startBottomGeofence(5)
        messagebox.showinfo( "showinfo", "Parámetros enviados", parent=self.window)

    # copio los valores de los parámetros del dron primero en todos los demás
    def copy_params (self):

        for i in range (1,len(self.swarm)):
            dronManager = self.managers[i]

            dronManager.RTL_ALT_Sldr.set(self.RTL_ALT_Sldr.get())
            dronManager.PILOT_SPEED_UP_Sldr.set(self.PILOT_SPEED_UP_Sldr.get())
            dronManager.FENCE_MARGIN_Sldr.set(self.FENCE_MARGIN_Sldr.get())
            dronManager.FENCE_ALT_MAX_Sldr.set(self.FENCE_ALT_MAX_Sldr.get())
            dronManager.fence_action_option.set(self.fence_action_option.get())
            dronManager.switch_action_option.set(self.switch_action_option.get())
            dronManager.NAV_SPEED_Sldr.set(self.NAV_SPEED_Sldr.get())

            dronManager.on_off =  self.on_off
            dronManager.on_offBtn['text'] = self.on_offBtn['text']
            dronManager.on_offBtn['bg'] =  self.on_offBtn['bg']
