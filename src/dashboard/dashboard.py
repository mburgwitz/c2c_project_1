import dash
from dash import dcc, html, Output, Input, State, ctx, callback, no_update
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
import plotly.express as px
from pathlib import Path
import time

from threading import Thread, Lock
from soniccar import SonicCar

#**********************************************
# Background animation
#**********************************************
BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = BASE_DIR / "templates"

retro_html = (TEMPLATE_DIR / "retrobackground.html").read_text()
index_template = (TEMPLATE_DIR / "index.html").read_text()
index_string = index_template.replace("{{retro_background}}", retro_html)

# Ersetze Platzhalter {{retro_background}} durch den eigentlichen Inhalt
index_string = index_template.replace("{{retro_background}}", retro_html)

#**********************************************
# Main App and objects
#**********************************************
car = SonicCar()
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


app = dash.Dash(__name__, 
                external_stylesheets=[dbc.themes.BOOTSTRAP],
                assets_folder="assets",
                index_string=index_string
            )
#**********************************************
# Functions
#**********************************************

def reset_global_statistic_vars():
    global total_drive_time
    global velocity 
    global steering_angle 
    global direction
    global timestamps 
    global total_route

    print("reset_global_statistic_vars")

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
    
    # ctr=0
    # while car_thread_running:
    #     time.sleep(0.25)
    #     ctr += 1
    #     print(ctr)
    # return

    try:
        car_thread_running = True
        if menu_selection == "DriveMode 1":
            car.drive_fixed_route("fahrmodus_1")
        elif menu_selection == "DriveMode 2":
            car.drive_fixed_route("fahrmodus_2")
        elif menu_selection == "DriveMode 3":
            car.random_drive(True)
        elif menu_selection == "DriveMode 4":
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

# Dummy-Output
hidden_div = html.Div(id="hidden-output", style={"display": "none"})

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
fig_2 = px.line(None)

fig_1.update_layout(paper_bgcolor='rgba(0,0,0,0.0)', plot_bgcolor='rgba(0,0,0,0.2)')
fig_1.update_xaxes(tickfont=dict(family='Rockwell', color="#0eecec", size=14))
fig_1.update_yaxes(tickfont=dict(family='Rockwell', color='#0eecec', size=14))

fig_2.update_layout(paper_bgcolor='rgba(0,0,0,0.0)', plot_bgcolor='rgba(0,0,0,0.2)')
fig_2.update_xaxes(tickfont=dict(family='Rockwell', color='#0eecec', size=14))
fig_2.update_yaxes(tickfont=dict(family='Rockwell', color='#0eecec', size=14))

start_stop_button = dbc.Button("Start", id="start_stop_button")
car_poll_interval = dcc.Interval(id="car_poll_interval", interval=500, disabled=True)
car_status_interval = dcc.Interval(id="car_status_interval", interval=250, disabled=True)

drive_menu_options = [
    dbc.DropdownMenuItem("DriveMode 1", id="drop1"),
    dbc.DropdownMenuItem("DriveMode 2", id="drop2"),
    dbc.DropdownMenuItem("DriveMode 3", id="drop3"),
    dbc.DropdownMenuItem("DriveMode 4", id="drop4")
]
drive_mode_menu = dbc.DropdownMenu(label="Modes",
                children=drive_menu_options,
                className='driveOptions',
                id = "drive_mode_menu",
                style={"position": "relative", "zIndex": 2000})
#**********************************************
# Layout
#**********************************************

app.layout = dbc.Container([
        car_poll_interval,
        car_status_interval,
        hidden_div,
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
        ], align="center", style={
                "position": "relative",
                "zIndex": 20,
                "overflow": "visible"
            }),

        dbc.Row([dbc.Col(create_card("**Vmax**", "Text 1", "clsC1"), id="col1"),
                    dbc.Col(create_card("**Vmin**", "Text 1", "clsC2")),
                    dbc.Col(create_card("**Ø V**", "Text 1", "clsC3")),
                    dbc.Col(create_card("**Gesamtstrecke**", "Text 1", "clsC4")),
                    dbc.Col(create_card("**Fahrzeit**", "Text 1", "clsC5"))                 
        ], 
        className="g-5", 
        justify="between",
        style={
                "position": "relative",
                "zIndex": 1,
        }),        

        dbc.Row([
            dbc.Col([
                    dcc.Graph(id='fig_1', figure=fig_1)
                ]),
            dbc.Col([
                dcc.Graph(id='fig_2', figure=fig_2)
            ])
        ],
        style={
                "position": "relative",
                "zIndex": 1,
        }),
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
    Output("drive_mode_menu", "label"),
    [Input(item.id, "n_clicks") for item in drive_menu_options], 
    prevent_initial_call=True 
)
def update_menu_label(*menu_items):
    
    # den ausgelösten Input identifizieren
    clicked_id = ctx.triggered_id

    item_title_clicked = ""
    for item in drive_menu_options:
        if item.id == clicked_id:
            item_title_clicked = item.children
    
    # Rückgabe des neuen Labels
    return item_title_clicked

# Start button
@app.callback(
    Output("start_stop_button", "children"), 
    Output("car_poll_interval", "disabled"),
    Output("car_status_interval", "disabled"),

    Input("start_stop_button", "n_clicks"),
    Input("car_poll_interval", "n_intervals"),

    State("start_stop_button", "children"),
    State("drive_mode_menu", "label"),
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
            print(f"car thread ende: {stop_time_driving}")
            
            return "Start", True, True
        
        elif trigger_id == "start_stop_button":
            if menu_selection == "Modes":
                return "Start", True, True # polling stays deactivated,
            
            if current_label == "Stop":
                car.hard_stop()
                car_thread_running = False
                stop_time_driving = time.time()
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
        return no_update, no_update, no_update, no_update, no_update
    
    print(" ... update status")
    print(f" ......len(vel): {len(velocity)}")
    # only calculate if we have at least 2 values and started the process already
    if len(velocity) < 2:
        return ["-"]*5

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

    print(f"v_max: {v_max}, v_min: {v_min}, v_avg: {v_avg}, total_route: {total_route}, total_drive_time: {total_drive_time}")
    return (
        f"{v_max:.2f}",
        f"{v_min:.2f}",
        f"{v_avg:.2f}",
        f"{total_route:.2f}",
        f"{total_drive_time:.2f}"
    )

if __name__ == "__main__":
    app.run_server(debug=True, host="0.0.0.0")


