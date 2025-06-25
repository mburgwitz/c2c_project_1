import dash
from dash import dcc, html, Output, Input, State, ctx, callback
import dash_bootstrap_components as dbc
import plotly.express as px
from pathlib import Path

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

app = dash.Dash(__name__, 
                external_stylesheets=[dbc.themes.BOOTSTRAP],
                assets_folder="assets",
                index_string=index_string
            )
#**********************************************
# Functions
#**********************************************
#def set_car_values(speed, angle, stop_distance):



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
    config_body.append(html.P(text, className=className+'Text'))

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
    Input("start_stop_button", "n_clicks"),
    State("start_stop_button", "children"),
    prevent_initial_call=True 
)
def start_stop_button_clicked(n_clicks, current_label):
    
    # Toggle anhand des tatsächlich angezeigten Labels
    return "Stop" if current_label == "Start" else "Start"
    

if __name__ == "__main__":
    app.run_server(debug=True, host="0.0.0.0")