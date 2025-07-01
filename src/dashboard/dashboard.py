import dash
from dash import dcc, html, Output, Input, State, ctx, callback, no_update, MATCH, ALL
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
import plotly.express as px
from pathlib import Path
import time

from threading import Thread, Lock
from sensorcar import SensorCar
from util.json_loader import readjson, save_log_to_file
import pandas as pd

#**********************************************
# Global directories
#**********************************************
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent.parent
TEMPLATE_DIR = BASE_DIR / "templates"
LOG_DIR = PROJECT_ROOT  / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

#**********************************************
# Background animation
#**********************************************
retro_html = (TEMPLATE_DIR / "retrobackground.html").read_text()
index_template = (TEMPLATE_DIR / "index.html").read_text()
index_string = index_template.replace("{{retro_background}}", retro_html)

# Ersetze Platzhalter {{retro_background}} durch den eigentlichen Inhalt
index_string = index_template.replace("{{retro_background}}", retro_html)

#**********************************************
# Main App and objects
#**********************************************
car = SensorCar()
car_thread_running = False
car_lock = Lock()

# for statistics
start_time_driving = None
stop_time_driving = None

total_drive_time = None
total_route = None
velocity = []
steering_angle = []
direction = []
timestamps = []

# loaded log file
loaded_log_from_file = None

app = dash.Dash(__name__, 
                external_stylesheets=[dbc.themes.BOOTSTRAP],
                assets_folder="assets",
                index_string=index_string
            )
#**********************************************
# Functions
#**********************************************
def get_available_logfiles():
    """
    Create dropdown menu items for each JSON log file in the logs directory.

    Returns
    -------
    list of dbc.DropdownMenuItem
        A list of Dash Bootstrap Components DropdownMenuItem objects,
        one for each .json file found in the LOG_DIR, sorted by filename.
    """
    return [ 
    dbc.DropdownMenuItem(
        name,
        id={"type": "dropdown-item",
            "menu": "log_choose_menu",
            "index": idx})
    for idx, name in enumerate(sorted([f.name for f in Path(LOG_DIR).glob("*.json")]))
]

def reset_car() -> None:
    """
    Reset the SensorCar instance and stop any running drive thread.

    This function stops the current car thread by setting the global
    flag `car_thread_running` to False and reinitializes the global `car`
    variable to a new SensorCar instance.

    Returns
    -------
    None
    """
    global car
    global car_thread_running

    car_thread_running = False
    car = SensorCar()

def write_to_logfile(log_name: str) -> None:
    """
    Save the current car log to a file.

    Parameters
    ----------
    log_name : str
        The filename under which to save the car's log data in the LOG_DIR.

    Returns
    -------
    None
    """
    global car
    save_log_to_file(car.log, LOG_DIR / log_name) 
  
def reset_global_statistic_vars():
    """
    Reset all global variables used for live-drive statistics.

    This clears accumulated route length, drive time, velocity list,
    steering angles, directions, timestamps, and total route.

    Returns
    -------
    None
    """
    global total_drive_time
    global velocity 
    global steering_angle 
    global direction
    global timestamps 
    global total_route

    total_route = 0
    total_drive_time = 0
    velocity = []
    steering_angle = []
    direction = []
    timestamps = []
    total_route = []

def car_process(menu_selection: str,
                input_speed, input_stop_dist, input_angle, input_time ):
    """
    Worker function to run the car in the selected driving mode.

    Depending on the `menu_selection`, this function invokes the
    corresponding SensorCar method with the provided parameters.
    It sets the `car_thread_running` flag to True at start and
    ensures the car is stopped and the flag reset on completion or error.

    Parameters
    ----------
    menu_selection : str
        The driving mode selected (e.g., "DriveMode 1", "DriveMode 3", etc.).
    input_speed : float or int
        The speed value passed to the driving mode method.
    input_stop_dist : float or int
        The stopping distance parameter for obstacle-based modes.
    input_angle : float or int
        The steering angle parameter for angle-based modes.
    input_time : float or int
        The duration for time-limited driving modes.

    Returns
    -------
    None
    """
    global car_thread_running

    
    try:
        car_thread_running = True
        if menu_selection == "DriveMode 1":
            car.fahrmodus1(input_speed, input_time)
        elif menu_selection == "DriveMode 2":
            car.fahrmodus2(input_speed, input_angle)
        elif menu_selection == "DriveMode 3":
            car.drive_until_obstacle(input_speed, input_stop_dist)
        elif menu_selection == "DriveMode 4":
            car.explore(input_speed, input_stop_dist, input_time)
        elif menu_selection == "DriveMode 4b":
            car.random_drive(normal_speed=input_speed, 
                             drive_time=input_time,
                              stop_distance=input_stop_dist)
        elif menu_selection == "DriveMode 5-7":
            car.follow_line_digital(input_speed, input_stop_dist)
        else:
            car_thread_running = False
            car.hard_stop()
        
    except Exception as e:
        raise Exception(e)
    finally:
        car_thread_running = False
        car.hard_stop()

def create_card(title: str, text: str, className: str, image: str = None):
    config = []
    if image is not None:
         config.append(dbc.CardImg(src=image, top=True))
    
    config_body = []
    #config_body.append(html.H4(title, className=className+'Title'))
    config_body.append(dcc.Markdown(title, className=className+'Title'))
    config_body.append(html.P(text, className=className+'Text', id = className+'TextId'))

    config.append(dbc.CardBody(config_body))
    return dbc.Card(config, className=className)

#**********************************************
# Layout components
#**********************************************
# dummy
dummy_div = html.Div("", style={"display": "none"}, id="dummy_div")

# title string
header = dcc.Markdown('Pi:Car - Dashboard', className = "retro-header", id="header")

# title für plot
header_plot = dcc.Markdown('Zeitliche Entwicklung der Fahrdaten', className = "plot-header", id="header_plot")

# title für fahrdaten logs
header_log_load = dcc.Markdown('Logfiles', className = "log-header",id="header_log_load")

# data storages
loaded_data_store = dcc.Store(id='loaded_data_store')
live_data_store = dcc.Store(id='live_data_store')

# figure
fig_1 = px.line(None)

fig_1.update_layout(paper_bgcolor='rgba(0,0,0,0.0)', 
                    plot_bgcolor='rgba(0,0,0,0.2)')
fig_1.update_traces(line_color="#FFFF00",line_width=4)

fig_1.update_xaxes(tickfont=dict(family='Rockwell', color="#0eecec", size=14))
fig_1.update_yaxes(tickfont=dict(family='Rockwell', color='#0eecec', size=14))

# buttons
start_stop_button = dbc.Button("Start", id="start_stop_button")
reference_ground_button = dbc.Button("Reference", id="reference_ground_button")
set_init_values_button = dbc.Button("Set Initial Values", id="set_init_values_button")

# init values popup entries
init_value_input_speed = dbc.Input(type="number", 
                                   placeholder="Velocity", 
                                   min=-100, max=100, step=1, 
                                   id="input_speed",
                                   value = 50)
init_value_input_angle = dbc.Input(type="number", 
                                   placeholder="Angle",
                                   min=45, max=135, step=1, 
                                   id="input_angle",
                                   value=90)
init_value_input_time = dbc.Input(type="number", 
                                  placeholder="Duration",
                                  min=0, step=0.5, 
                                  id="input_time",
                                  value=20)
init_value_input_stop_dist = dbc.Input(type="number", 
                                       placeholder="Stop Distance",
                                       min=0, step=1, 
                                       id="input_stop_dist",
                                       value=20)

# FormFloating kann nur ein Input und ein Label nutzen --> Pro Input ein FormFloating
init_value_input_speed_form = dbc.FormFloating([init_value_input_speed, dbc.Label("Velocity")])
init_value_input_angle_form = dbc.FormFloating([init_value_input_angle, dbc.Label("Angle")])
init_value_input_time_form = dbc.FormFloating([init_value_input_time, dbc.Label("Duration")])
init_value_input_stop_dist_form = dbc.FormFloating([init_value_input_stop_dist, dbc.Label("Stop Distance")])

# container für forms zum Einfügen in popover
init_values_form = html.Div([init_value_input_speed_form,
                             init_value_input_angle_form,
                             init_value_input_time_form,
                             init_value_input_stop_dist_form
                            ])

# eigentliches popover für klick auf set_init_values_button
inital_values_popover = dbc.Popover([dbc.PopoverHeader("Inital Values Drive Mode",className="popover_title"),
                                     init_values_form #dbc.PopoverBody("text",className="popover_body")
                                     ], 
                                     target="set_init_values_button",
                                     trigger="click",
                                     placement="bottom")

# timed intervall to watch car process thread and update status cards
car_poll_interval = dcc.Interval(id="car_poll_interval", interval=500, disabled=True)
car_status_interval = dcc.Interval(id="car_status_interval", interval=250, disabled=True)

# Auswahloptionen für Fahroptionen / Modi
drive_menu_options = [
    dbc.DropdownMenuItem("DriveMode 1", id={"type": "dropdown-item", 
                                            "menu": "drive_mode_menu",
                                            "index": 0}),
    dbc.DropdownMenuItem("DriveMode 2", id={"type": "dropdown-item", 
                                            "menu": "drive_mode_menu",
                                            "index": 1}),
    dbc.DropdownMenuItem("DriveMode 3", id={"type": "dropdown-item", 
                                            "menu": "drive_mode_menu",
                                            "index": 2}),
    dbc.DropdownMenuItem("DriveMode 4", id={"type": "dropdown-item", 
                                            "menu": "drive_mode_menu",
                                            "index": 3}),
    dbc.DropdownMenuItem("DriveMode 4b", id={"type": "dropdown-item", 
                                            "menu": "drive_mode_menu",
                                            "index": 4}),
    dbc.DropdownMenuItem("DriveMode 5-7", id={"type": "dropdown-item", 
                                            "menu": "drive_mode_menu",
                                            "index": 5}),
]

# eigentliches Auswahlmenü mit Auswahlmöglichkeiten aus drive_menu_options
drive_mode_menu = dbc.DropdownMenu(
                label="Modes",
                children=drive_menu_options,
                className='driveOptions',
                id = {"type": "dropdown-menu", "menu": "drive_mode_menu"},
                style={"position": "relative", "zIndex": 2000}
                )

# Menüoptionen zur Auswahl der Darstellung im Graph
graph_menu_options = [
    dbc.DropdownMenuItem("Velocity", id={"type": "dropdown-item", 
                                        "menu": "graph_display_menu",
                                        "index": 0}),
    dbc.DropdownMenuItem("Acceleration", id={"type": "dropdown-item", 
                                        "menu": "graph_display_menu",
                                        "index": 1}),
    dbc.DropdownMenuItem("Angle", id={"type": "dropdown-item", 
                                        "menu": "graph_display_menu",
                                        "index": 2}),
    dbc.DropdownMenuItem("Route", id={"type": "dropdown-item", 
                                        "menu": "graph_display_menu",
                                        "index": 3})                     
]

# Eigentliches Menü mit Optionen aus graph_menu_options
graph_display_menu = dbc.DropdownMenu(
                label="Velocity",
                children=graph_menu_options,
                className='driveOptions',
                id = {"type": "dropdown-menu", "menu": "graph_display_menu"},
                style={"position": "relative", "zIndex": 2000})

# Optionen aus LOG_DIR lesen
log_menu_options = get_available_logfiles()

# Auswahlmenü für Logfiles zur Anzeige im Graph
log_choose_menu = dbc.DropdownMenu(
                label="Choose Log",
                children=log_menu_options,
                className='driveOptions',
                id={"type": "dropdown-menu", "menu": "log_choose_menu"},
                style={"position": "relative", "zIndex": 2000})

# Laden des im log_choose_menu ausgewählten Logfiles in den Graphen
load_file_button = dbc.Button("Load Log", id="load_file_button", className="mb-5")

# Updaten der Auswahloptionen im log_choose_menu
refresh_logs_button = dbc.Button("Refresh Logs", id="refresh_logs_button", className="mb-5")

# Status-String für das Laden der Logfiles
log_load_feedback = dcc.Markdown(' ', className = "log-load-feeback",id="log_load_feedback")

#**********************************************
# Layout
#**********************************************
app.layout = dbc.Container([
        dummy_div,
        car_poll_interval,
        car_status_interval,
        loaded_data_store,
        live_data_store,

        # --- HEADER AND MENU ---
        dbc.Row([
            dbc.Col(header, width=8),
            dbc.Col(dbc.Row([
            dbc.Col([set_init_values_button, inital_values_popover,
                    html.Br(),
                    reference_ground_button
                    ], 
                    width=2,
                    className="d-flex flex-column gap-2 align-items-start",
                    style={
                        "flex": "0 0 200px",      # kein Wachstum, keine Schrumpfung, feste Basis 200px
                        "maxWidth": "200px",      # maximal 200px
                        "minWidth": "200px",      # minimal 200px
                    }  
                    ),
            dbc.Col([
                    drive_mode_menu,
                    html.Br(),
                    start_stop_button
                    ], 
                    width=2,
                    className="d-flex flex-column gap-2 align-items-start", 
                    style={
                        "flex": "0 0 200px",      # kein Wachstum, keine Schrumpfung, feste Basis 200px
                        "maxWidth": "200px",      # maximal 200px
                        "minWidth": "200px",      # minimal 200px
                    } )
                    ])
            )
        ], 
        align="center", 
        style={
            "position": "relative",
            "zIndex": 20,
            "overflow": "visible"
        }),

        # --- KPI-Cards ---
        dbc.Row([dbc.Col(create_card("**Vmax**", "-", "clsC1"), id="col1"),
                    dbc.Col(create_card("**Vmin**", "-", "clsC2")),
                    dbc.Col(create_card("**Ø V**", "-", "clsC3")),
                    dbc.Col(create_card("**Gesamtstrecke**", "-", "clsC4")),
                    dbc.Col(create_card("**Fahrzeit**", "-", "clsC5"))                 
        ], 
        className="g-1", 
        justify="between",
        style={
                "position": "relative",
                "zIndex": 1,
        }),        
        
        dbc.Row(html.Div(), style={"height": "2rem"}),

        # --- GRAFIK-BEREICH ---
        dbc.Row([
            dbc.Col([header_plot,
                    dcc.Graph(id='fig_1', figure=fig_1)], 
                    width=10, 
                    style={
                        "maxWidth": "calc(100% - 200px)"
                    }),
            
            dbc.Col([
                    dbc.Col(graph_display_menu),
                    html.Div(header_log_load, style={'position':'relative','zIndex':1}),
                    html.Br(),
                    html.Div(log_choose_menu, style={'position':'relative','zIndex':2}),
                    html.Br(),
                    html.Div(load_file_button, style={'position':'relative','zIndex':1}),
                    html.Br(),
                    html.Div(refresh_logs_button, style={'position':'relative','zIndex':1}),
                    html.Br(),
                    html.Div(log_load_feedback, style={'position':'relative','zIndex':1}),
                    ], width=2, style={
                        "flex": "0 0 200px",      # kein Wachstum, keine Schrumpfung, feste Basis 200px
                        "maxWidth": "200px",      # maximal 200px
                        "minWidth": "200px",      # minimal 200px
                    }
            ),
        ], 
        align="right",
        className="g-2 align-items-start "),
        #dbc.Row(graph_display_menu)
    ], 
    style={
        "position": "relative",
        "overflow": "visible"
})
#**********************************************
# Callbacks
#**********************************************
@app.callback(
    Output("dummy_div","children"),
    Input("reference_ground_button", "n_clicks"),
    prevent_initial_call=True 
)
def reference_ir_sensor(self):
    """
    Calibrate the IR sensor by referencing it to the ground level.

    This callback is triggered by clicking the "Reference" button and
    calls the SensorCar.reference_ground() method.

    Parameters
    ----------
    self : int
        Number of clicks on the reference button (ignored).

    Returns
    -------
    dash.no_update
        Prevents any change to the output components.
    """
    car.reference_ground()
    return no_update

# Update menu with selected label
@app.callback(
    Output({"type": "dropdown-menu", "menu": MATCH}, "label"),
    Input({"type": "dropdown-item", "menu": MATCH, "index": ALL}, "n_clicks"),
    prevent_initial_call=True 
)
def update_menu_label(n_clicks_list):
    """
    Update the label of a dropdown menu to reflect the selected item.

    Identifies which dropdown-item triggered the callback and sets the
    parent dropdown-menu's label to that item's text.

    Parameters
    ----------
    n_clicks_list : list of int
        Click counts for all items in the matching dropdown menu.

    Returns
    -------
    str
        The new label for the dropdown menu based on the clicked item.
    """
    # den ausgelösten Input identifizieren
    clicked_id = ctx.triggered_id

    if not any(n_clicks_list):
        raise PreventUpdate
    
    menu = clicked_id["menu"]
    idx  = clicked_id["index"]

    menu_iterate = []
    if menu == "drive_mode_menu":
        menu_iterate = drive_menu_options 
    elif menu == "graph_display_menu":
        menu_iterate = graph_menu_options
    elif menu == "log_choose_menu":
        menu_iterate = log_menu_options
    return menu_iterate[idx].children

@app.callback(
    Output({"type":"dropdown-menu","menu":"log_choose_menu"}, "children"),
    Input("refresh_logs_button", "n_clicks"),
    prevent_initial_call=True
)
def refresh_log_menu(n):
    """
    Refresh the log file dropdown menu items.

    Re-reads the LOG_DIR to generate an updated list of log files
    and returns new children for the log selection dropdown.

    Parameters
    ----------
    n : int
        Number of clicks on the "Refresh Logs" button.

    Returns
    -------
    list of dbc.DropdownMenuItem
        Updated list of log file menu items.
    """
    global log_menu_options
    log_menu_options = get_available_logfiles()
    return get_available_logfiles()

# Start button
@app.callback(
    Output("start_stop_button", "children"), 
    Output("car_poll_interval", "disabled"),
    Output("car_status_interval", "disabled"),

    Input("start_stop_button", "n_clicks"),
    Input("car_poll_interval", "n_intervals"),

    State("start_stop_button", "children"),
    State({"type": "dropdown-menu", "menu": "drive_mode_menu"}, "label"),
    State("input_speed", "value"),
    State("input_angle", "value"),
    State("input_time", "value"),
    State("input_stop_dist", "value"),
    prevent_initial_call=True 
)
def start_stop_button_clicked(n_clicks, n_intervals, current_label, menu_selection,
                              input_speed, input_angle, input_time, input_stop_dist):
    """
    Handle start/stop button logic and polling activation for driving.

    Toggles between starting and stopping the car thread, manages
    logging on stop, and enables or disables the polling intervals
    to update live statistics.

    Parameters
    ----------
    n_clicks : int
        Number of clicks on the start/stop button.
    n_intervals : int
        Number of intervals elapsed (polling trigger).
    current_label : str
        Current text of the start/stop button ("Start" or "Stop").
    menu_selection : str
        Label of the selected drive mode.
    input_speed : float or int
        Current speed input value.
    input_angle : float or int
        Current steering angle input value.
    input_time : float or int
        Current duration input value.
    input_stop_dist : float or int
        Current stop distance input value.

    Returns
    -------
    tuple
        - New button label ("Start" or "Stop")
        - Boolean to enable/disable car data polling
        - Boolean to enable/disable car status polling
    """
    global car_thread_running
    global start_time_driving

    trigger_id = ctx.triggered_id

    with car_lock:
        if trigger_id == "car_poll_interval":
            if car_thread_running:
                #print("car thread running")
                return no_update, no_update, no_update
            
            stop_time_driving = time.time()
            write_to_logfile("log_"
                                 +str(time.strftime("%y%m%d_%H%M",  time.localtime(stop_time_driving)))
                                 +".json")
            print(f"car thread ende: {stop_time_driving}")
            reset_car()
            return "Start", True, True
        
        elif trigger_id == "start_stop_button":
            if menu_selection == "Modes":
                return "Start", True, True # polling stays deactivated,
            
            if current_label == "Stop":
                car_thread_running = False
                stop_time_driving = time.time()
                write_to_logfile("log_"
                                 +str(time.strftime("%y%m%d_%H%M",  time.localtime(stop_time_driving)))
                                 +".json")
                car.hard_stop()
                reset_car()
                return "Start", True, True # deactivate polling
            else:
                Thread(target=car_process, args=(menu_selection,
                                                 input_speed,
                                                 input_stop_dist, 
                                                 input_angle, 
                                                 input_time), daemon=True).start()
                reset_global_statistic_vars()

                car_thread_running = True
                start_time_driving = time.time()
                print(f"car thread start: {start_time_driving}")
                return "Stop", False, False # activate polling
        else:
            return "Start", True, True

@app.callback(
    Output("clsC1TextId", "children"),
    Output("clsC2TextId", "children"),
    Output("clsC3TextId", "children"),
    Output("clsC4TextId", "children"),
    Output("clsC5TextId", "children"),
    Output('live_data_store', 'data'),
    Input("car_status_interval", "n_intervals"),
    Input("load_file_button", "n_clicks"),
    State("start_stop_button", "children"),
    State("loaded_data_store", "data"),
    prevent_initial_call=True 
)
def update_status_cards( n_intervals, n_clicks, current_label, loaded_data):
    """
    Update the KPI cards with either live data or loaded log data.

    Depending on whether live driving is in progress or a log file
    has been loaded, calculates vmax, vmin, average speed, total route,
    and drive time, and updates both the display cards and the
    live_data_store.

    Parameters
    ----------
    n_intervals : int
        Number of status intervals elapsed (live update trigger).
    n_clicks : int
        Number of clicks on the "Load Log" button.
    current_label : str
        Current text of the start/stop button.
    loaded_data : list or None
        Data loaded from a JSON log, if any.

    Returns
    -------
    tuple
        - vmax (str), vmin (str), avg speed (str), total route (str),
          total drive time (str), or dash.no_update for live_data_store.
    """
    global total_route
    global total_drive_time

    trigger_id = ctx.triggered_id

    # data_loaded ist [data, timestamp]
    if loaded_data is not None:
        loaded_data = loaded_data[0]

    # Nur updaten, wenn der Button gerade "Stop" anzeigt (also Drive läuft)
    # und keine log-daten geladen wurden
    if current_label != "Stop" and trigger_id != "load_file_button":
        raise PreventUpdate
    
    if trigger_id == "load_file_button":
        if loaded_data is None:
            print("no loaded data")
            raise PreventUpdate
        df = pd.DataFrame(loaded_data)
        
        df["cum_delta_t"] = df["timestamp"] - df["timestamp"].iloc[0]
        df["dt_s"] = df["timestamp"].diff().fillna(0) 
        df['Route'] = ((df["speed"] + df["speed"].shift(fill_value=0)) * df["dt_s"] / 2).cumsum()

        v_max = df["speed"].max()
        v_min = df["speed"].min()
        v_avg = df["speed"].mean()
        total_route = df['Route'].max()
        total_drive_time = df["timestamp"].iloc[-1] - df["timestamp"].iloc[0]

        return (
            f"{v_max:.2f}",
            f"{v_min:.2f}",
            f"{v_avg:.2f}",
            f"{total_route:.2f}",
            f"{total_drive_time:.2f}",
            no_update
        )

    else:     
        with car_lock:
            velocity.append(car.speed)
            steering_angle.append(car.steering_angle)
            direction.append(car.direction)
        timestamps.append(time.time())

        # just append values if we just started to drive
        if car_thread_running == False:
            return no_update, no_update, no_update, no_update, no_update, no_update

    # only calculate if we have at least 2 values and started the process already
    if len(velocity) < 2:
        return "-", "-", "-", "-", "-", no_update

    # Basiszeit rechnen
    elapsed = time.time() - start_time_driving

    total_drive_time = elapsed

    # avg velocity between now and last timestamp times delta_t
    delta_t     = timestamps[-1] - timestamps[-2]
    segment     = (abs(velocity[-1]) + abs(velocity[-2])) / 2 * delta_t
    total_route = (total_route or 0) + segment

    v_max = max(velocity)
    v_min = min(velocity)
    v_avg = sum(velocity) / len(velocity)

    data = [
        {
            "timestamp": timestamps[i],
            "speed": velocity[i],
            "steering_angle": steering_angle[i],
            "direction": direction[i]
        }
        for i in range(len(velocity))
    ]

    return (
        f"{v_max:.2f}",
        f"{v_min:.2f}",
        f"{v_avg:.2f}",
        f"{total_route:.2f}",
        f"{total_drive_time:.2f}",
        data
    )

@app.callback(
    Output("loaded_data_store", "data"),
    Output("log_load_feedback", "children"),
    Input("load_file_button", "n_clicks"),
    Input({ "type": "dropdown-menu", "menu": "log_choose_menu" }, "label"),
    prevent_initial_call=True
)
def load_file(n_clicks, filename):
    """
    Load a selected JSON log file into the store and provide feedback.

    Reads the specified log file from LOG_DIR, stores its data along
    with a timestamp to force downstream updates, and returns a
    feedback message.

    Parameters
    ----------
    n_clicks : int
        Number of clicks on the "Load Log" button.
    filename : str
        Name of the selected log file.

    Returns
    -------
    list, str
        - A list containing [data, time.time()] for dcc.Store
        - Feedback message markdown string.
    """
    if not filename:
        # kein file ausgewählt, nichts machen
        raise PreventUpdate

    # Lade die JSON aus Deinem LOG_DIR
    try:
        data = readjson(LOG_DIR /filename)
    except Exception as e:
        # Fehler beim Laden
        return no_update, f"Error loading **{filename}**"

    # alles OK → ins Store schreiben, Feedback setzen
    feedback = f"Loaded file: **{filename}**"

    # data_loaded ist [data, timestamp]
    # data dcc.Store das feld 'modified_timestamp' nur setzt, 
    # wenn sich das Datum wirklich ändert, wird durch time.time()
    # eine Änderung erzwungen. 'modified_timestamp' wird in 
    # update_graph genutzt, um den aktuellsten Datensatz anzuzeigen
    return [data, time.time()], feedback

# Callback zur Aktualisierung des Graphen (Anforderung 2 & 3)
@app.callback(
    Output("fig_1", "figure"),
    Input("load_file_button", "n_clicks"),
    Input({"type": "dropdown-item", "menu": "graph_display_menu", "index": ALL}, "n_clicks"),
    Input("live_data_store", "data"),
    Input({"type": "dropdown-menu", "menu": "graph_display_menu"}, "label"),
    State("loaded_data_store", "data"),
    State("fig_1", "figure"),     
    State('loaded_data_store', 'modified_timestamp'),
    State('live_data_store', 'modified_timestamp') ,      
    prevent_initial_call=True
)
def update_graph(n1,n2, 
                 data_live, 
                 selected_metric, 
                 data_loaded, 
                 fig,
                 time_loaded_data_modified,
                 time_live_data_modified ):
    """
    Update the Plotly figure based on live or loaded data and selected metric.

    Determines which dataset to use (live vs. loaded), computes derived
    metrics (Route or Acceleration) if needed, and updates the existing
    figure's x and y data arrays along with the trace name.

    Parameters
    ----------
    n1 : int
        Number of clicks on the "Load Log" button.
    n2 : list of int
        Click counts for graph metric menu items.
    data_live : list or None
        Live data from the car.
    selected_metric : str
        Currently selected metric label for display.
    data_loaded : list or None
        Loaded log data from dcc.Store.
    fig : dict
        Current Plotly figure dictionary.
    time_loaded_data_modified : float
        Timestamp when data_loaded was last modified.
    time_live_data_modified : float
        Timestamp when data_live was last modified.

    Returns
    -------
    dict
        Updated Plotly figure dictionary with new data and trace name.
    """

    # data_loaded ist [data, timestamp]
    if data_loaded is not None:
        data_loaded = data_loaded[0]

    trigger_id = ctx.triggered_id
    
    if not data_loaded and not data_live:
        print("no data live or loaded")
        raise PreventUpdate

    if not data_loaded and (trigger_id == "loaded_data_store" or trigger_id == "load_file_button"):
         print("no data loaded")
         raise PreventUpdate
    
    if (trigger_id != "load_file_button" and trigger_id != "live_data_store" and trigger_id != "loaded_data_store" and not (
            isinstance(trigger_id, dict)
            and trigger_id.get("type") == "dropdown-item"
            and trigger_id.get("menu") == "graph_display_menu")):
        print("no valid trigger")
        raise PreventUpdate
    
    # wurde die live data zuletzt modifiziert, zeige nur live data an
    # ermöglicht umschalten der angezeigten Größen im Graph auf Basis 
    # des aktuellsten Datensatzes (live oder loaded)
    if data_loaded is not None and data_live is None:
        data = data_loaded
    elif data_live is not None and data_loaded is None:
        data = data_live
    elif trigger_id ==  "load_file_button":
        data = data_loaded
    elif time_live_data_modified > time_loaded_data_modified:
        data = data_live
    else:
        data = data_loaded

    df = pd.DataFrame(data)

    # Verstrichene Zeit seit ersten timestamp
    df["cum_delta_t"] = df["timestamp"] - df["timestamp"].iloc[0]

    # Zeitdifferenz zwischen i und i-1
    df["dt_s"] = df["timestamp"].diff().fillna(0)     
    
    y_axis = "speed" 
    if selected_metric == "Angle":
        y_axis = "steering_angle"

    elif selected_metric == "Route":
        # strecke = (v_i + v_{i-1}/2 * delta_ti)
        df['Route'] = ((df["speed"] + df["speed"].shift(fill_value=0)) * df["dt_s"] / 2).cumsum()
        y_axis = 'Route'

    elif selected_metric == "Acceleration":
        # acc = (v_i - v_{i-1}) / delta_ti
        df['Acceleration'] = (df['speed'].diff().fillna(0) / df['dt_s']).fillna(0)
        y_axis = 'Acceleration'
    
    fig["data"][0]["x"] = df['cum_delta_t'].tolist()
    fig["data"][0]["y"] = df[y_axis].tolist()
    fig["data"][0]["name"] = selected_metric

    return fig

if __name__ == "__main__":
    app.run_server(debug=True, host="0.0.0.0")