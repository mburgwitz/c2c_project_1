import dash
from dash import dcc, html, Output, Input, State, ctx, callback, no_update, MATCH, ALL
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
import plotly.express as px
from pathlib import Path
import time

from threading import Thread, Lock
from sensorcar import SensorCar
from util.json_loader import readjson
import pandas as pd
from test_modi import save_log_to_file
import os

#**********************************************
# Background animation
#**********************************************
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent.parent
TEMPLATE_DIR = BASE_DIR / "templates"
LOG_DIR = PROJECT_ROOT  / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)


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

def get_avaiable_logfiles():
    return [ 
    dbc.DropdownMenuItem(
        name,
        id={"type": "dropdown-item",
            "menu": "log_choose_menu",
            "index": idx})
    for idx, name in enumerate(sorted([f.name for f in Path(LOG_DIR).glob("*.json")]))
]

def write_to_logfile(log_name: str) -> None:
    global log_menu_options
    global log_choose_menu
    save_log_to_file(car.log, LOG_DIR / log_name)
    log_menu_options = get_avaiable_logfiles()
    log_choose_menu.children = log_menu_options

# DataFrame mit den Fahrdaten erstellen
def reset_global_statistic_vars():
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

# worker process during car drive thread
def car_process(menu_selection: str):
    global car_thread_running

    try:
        car_thread_running = True
        if menu_selection == "DriveMode 1":
            car.fahrmodus1(30,4.0)
        elif menu_selection == "DriveMode 2":
            car.fahrmodus2(30,45)
        elif menu_selection == "DriveMode 3":
            car.drive_until_obstacle()
        elif menu_selection == "DriveMode 4":
            car.explore()
        elif menu_selection == "DriveMode 4b":
            car.random_drive(False)
        else:
            car_thread_running = False
    except Exception as e:
        raise Exception(e)
    finally:
        car_thread_running = False

#**********************************************
# Layout components
#**********************************************

# title string
header = dcc.Markdown('Pi:Car - Dashboard', className = "retro-header", id="header")

# title für plot
header_plot = dcc.Markdown('Zeitliche Entwicklung der Fahrdaten', className = "plot-header", id="header_plot")

# title für fahrdaten logs
header_log_load = dcc.Markdown('Logfiles', className = "log-header",id="header_log_load")

# Dummy-Output
loaded_data_store = dcc.Store(id='loaded_data_store')
live_data_store = dcc.Store(id='live_data_store')

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

fig_1 = px.line(None)

fig_1.update_layout(paper_bgcolor='rgba(0,0,0,0.0)', 
                    plot_bgcolor='rgba(0,0,0,0.2)')
fig_1.update_traces(line_color="#FFFF00",line_width=4)

fig_1.update_xaxes(tickfont=dict(family='Rockwell', color="#0eecec", size=14))
fig_1.update_yaxes(tickfont=dict(family='Rockwell', color='#0eecec', size=14))

start_stop_button = dbc.Button("Start", id="start_stop_button")

car_poll_interval = dcc.Interval(id="car_poll_interval", interval=500, disabled=True)
car_status_interval = dcc.Interval(id="car_status_interval", interval=250, disabled=True)

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
drive_mode_menu = dbc.DropdownMenu(
                label="Modes",
                children=drive_menu_options,
                className='driveOptions',
                id = {"type": "dropdown-menu", "menu": "drive_mode_menu"},
                style={"position": "relative", "zIndex": 2000}
                )

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

graph_display_menu = dbc.DropdownMenu(
                label="Velocity",
                children=graph_menu_options,
                className='driveOptions',
                id = {"type": "dropdown-menu", "menu": "graph_display_menu"},
                style={"position": "relative", "zIndex": 2000})

log_menu_options = get_avaiable_logfiles()

log_choose_menu = dbc.DropdownMenu(
                label="Choose Log",
                children=log_menu_options,
                className='driveOptions',
                id={"type": "dropdown-menu", "menu": "log_choose_menu"},
                style={"position": "relative", "zIndex": 2000})

load_file_button = dbc.Button("Load", id="load_file_button", className="mb-5")
refresh_logs_button = dbc.Button("Refresh", id="refresh_logs_button", className="mb-5")
log_load_feedback = dcc.Markdown(' ', className = "log-load-feeback",id="log_load_feedback")

#**********************************************
# Layout
#**********************************************
app.layout = dbc.Container([
        car_poll_interval,
        car_status_interval,
        loaded_data_store,
        live_data_store,

            # --- HEADER AND MENU ---
            dbc.Row([
                dbc.Col(header, width=10),
                dbc.Col([
                    drive_mode_menu,
                    html.Br(),
                    start_stop_button
                ], width=2, style={
                    "position": "relative",
                    "zIndex": 20,
                    "overflow": "visible"
                })
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
            className="g-5", 
            justify="between",
            style={
                    "position": "relative",
                    "zIndex": 1,
            }),        
            
            dbc.Row(html.Div(), style={"height": "2rem"}),

            # --- GRAFIK-BEREICH ---
            dbc.Row([
                dbc.Col([header_plot,
                        dcc.Graph(id='fig_1', figure=fig_1)], width=10),
                
            # ],align="center"),

            
                
                
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
                    "position": "absolut",
                    "zIndex": 20,
                    "overflow": "visible"
                }),
            ], 
            align="center",
            className="g-2"),
            #dbc.Row(graph_display_menu)
        ], 
        style={
            "position": "relative",
            "overflow": "visible"
    })
#**********************************************
# Callbacks
#**********************************************

# Update menu with selected label
@app.callback(
    Output({"type": "dropdown-menu", "menu": MATCH}, "label"),
    Input({"type": "dropdown-item", "menu": MATCH, "index": ALL}, "n_clicks"),
    prevent_initial_call=True 
)
def update_menu_label(n_clicks_list):
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
    return get_avaiable_logfiles()

# Start button
@app.callback(
    Output("start_stop_button", "children"), 
    Output("car_poll_interval", "disabled"),
    Output("car_status_interval", "disabled"),

    Input("start_stop_button", "n_clicks"),
    Input("car_poll_interval", "n_intervals"),

    State("start_stop_button", "children"),
    State({"type": "dropdown-menu", "menu": "drive_mode_menu"}, "label"),
    prevent_initial_call=True 
)
def start_stop_button_clicked(n_clicks, n_intervals, current_label, menu_selection):
    global car_thread_running
    global start_time_driving

    trigger_id = ctx.triggered_id

    with car_lock:
        if trigger_id == "car_poll_interval":
            if car_thread_running:
                print("car thread running")
                return no_update, no_update, no_update
            
            stop_time_driving = time.time()
            write_to_logfile("log_"
                                 +str(time.strftime("%y%m%d_%H%M",  time.localtime(stop_time_driving)))
                                 +".json")
            print(f"car thread ende: {stop_time_driving}")
            
            return "Start", True, True
        
        elif trigger_id == "start_stop_button":
            if menu_selection == "Modes":
                return "Start", True, True # polling stays deactivated,
            
            if current_label == "Stop":
                car.hard_stop()
                car_thread_running = False
                stop_time_driving = time.time()
                write_to_logfile("log_"
                                 +str(time.strftime("%y%m%d_%H%M",  time.localtime(stop_time_driving)))
                                 +".json")
                return "Start", True, True # deactivate polling
            else:
                Thread(target=car_process, args=(menu_selection,), daemon=True).start()
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
    State("start_stop_button", "children"),
    prevent_initial_call=True 
)
def update_status_cards( n_intervals,current_label):
    global total_route
    global total_drive_time
    
    # Nur updaten, wenn der Button gerade "Stop" anzeigt (also Drive läuft)
    if current_label != "Stop":
        raise PreventUpdate
    
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
    segment     = (velocity[-1] + velocity[-2]) / 2 * delta_t
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
    return data, feedback

# Callback zur Aktualisierung des Graphen (Anforderung 2 & 3)
@app.callback(
    Output("fig_1", "figure"),
    Input("load_file_button", "n_clicks"),
    Input("live_data_store", "data"),
    Input({"type": "dropdown-menu", "menu": "graph_display_menu"}, "label"),
    State("loaded_data_store", "data"),
    State("fig_1", "figure"),            
    prevent_initial_call=True
)
def update_graph(n_click, data_live, selected_metric, data_loaded, fig ):
    # Erstelle eine Liniengrafik mit Plotly Express

    trigger_id = ctx.triggered_id
    
    if not data_loaded and (trigger_id == "loaded_data_store" or trigger_id == "load_file_button"):
         raise PreventUpdate
    
    if trigger_id not in ("load_file_button", "live_data_store"):
        raise PreventUpdate
    
    data = data_loaded if (trigger_id == "loaded_data_store" or trigger_id == "load_file_button") else data_live
    
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
        df['Acceleration'] = df['speed'].diff().fillna(0) / df['dt_s']
        y_axis = 'Acceleration'
    
    fig["data"][0]["x"] = df['cum_delta_t'].tolist()
    fig["data"][0]["y"] = df[y_axis].tolist()
    fig["data"][0]["name"] = selected_metric
    
    return fig

if __name__ == "__main__":
    app.run_server(debug=True, host="0.0.0.0")