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
import os

# PYTHONPATH=src python3 src/dashboard/dashboard.py

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

def get_available_logfiles():
    return [ 
    dbc.DropdownMenuItem(
        name,
        id={"type": "dropdown-item",
            "menu": "log_choose_menu",
            "index": idx})
    for idx, name in enumerate(sorted([f.name for f in Path(LOG_DIR).glob("*.json")]))
]

def reset_car() -> None:
    global car
    global car_thread_running

    car_thread_running = False
    car = SensorCar()

def write_to_logfile(log_name: str) -> None:
    global car
    save_log_to_file(car.log, LOG_DIR / log_name) 
  
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
def car_process(menu_selection: str,
                input_speed, input_stop_dist, input_angle, input_time ):
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

reference_ground_button = dbc.Button("Reference", id="reference_ground_button")

set_init_values_button = dbc.Button("Set Initial Values", id="set_init_values_button")


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

init_values_form = html.Div([init_value_input_speed_form,
                             init_value_input_angle_form,
                             init_value_input_time_form,
                             init_value_input_stop_dist_form
                            ])

inital_values_popover = dbc.Popover([dbc.PopoverHeader("Inital Values Drive Mode",className="popover_title"),
                                     init_values_form #dbc.PopoverBody("text",className="popover_body")
                                     ], 
                                     target="set_init_values_button",
                                     trigger="click",
                                     placement="bottom")



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

log_menu_options = get_available_logfiles()

log_choose_menu = dbc.DropdownMenu(
                label="Choose Log",
                children=log_menu_options,
                className='driveOptions',
                id={"type": "dropdown-menu", "menu": "log_choose_menu"},
                style={"position": "relative", "zIndex": 2000})

load_file_button = dbc.Button("Load Log", id="load_file_button", className="mb-5")
refresh_logs_button = dbc.Button("Refresh Logs", id="refresh_logs_button", className="mb-5")
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

# @app.callback(
#     Output(),
#     Input("set_init_values_button", "n_clickds"),
#     prevent_initial_call=True
# )
# def set_initial_values(n):


@app.callback(
    Output("dummy_div","children"),
    Input("reference_ground_button", "n_clicks"),
    prevent_initial_call=True 
)
def reference_ir_sensor(self):
    car.reference_ground()
    return no_update

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
    # Erstelle eine Liniengrafik mit Plotly Express

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