import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, State
import plotly.express as px
import pandas as pd
import numpy as np

# --- 1. App initialisieren mit einem dunklen Bootstrap-Theme ---
# Theme als Basis setzen
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.CYBORG])
#app = dash.Dash(__name__, external_stylesheets=["code.css"])

# --- 2. Fahrdaten laden ---
def lade_fahrdaten():
    try:
        data_df = pd.read_json("fahrt_log.json", orient='records')
    except Exception as e:
        print(e)
        '''"Zeit": timestamps,
        "Geschwindigkeit (km/h)": speed,
        "Zurückgelegte Strecke (km)": distance,
        "Beschleunigung (m/s²)": acceleration'''
    return data_df

# --- 3. KPIs aus den Fahrdaten generieren ---
# Die Fahrdaten kommen aus den Sensoren(Fahrten von BaseCar und SonicCar z.B. in test_modi.py)
# Gespeicherten Fahrdaten in der Datei "fahrt_log.json"
# Andere Funktion für LIVE-Daten, implementieren.
def generate_kpis_data_from_logs():
    # Lade die Fahrdaten aus der JSON-Datei
    fahrdaten_df = lade_fahrdaten()
    # Berechne die Gesamtfahrstecke und Gesamtfahrzeit aus fahrdaten_df
    # Gesamtfahrstecke ergibt sich  aus dem Produkt von Geschwindigkeit und Gesamtfahrzeit
    timestamps = fahrdaten_df['timestamp']
    speed = fahrdaten_df['speed']  # Geschwindigkeit in km/h
    # Strecke und Beschleunigung daraus ableiten
    distance = np.cumsum(speed * (1/3600)) # Strecke in km
    acceleration = np.diff(speed, prepend=speed[0]) # Einfache Beschleunigung
    
    df = pd.DataFrame({
        "Zeit": timestamps,
        "Geschwindigkeit (km/h)": speed,
        "Zurückgelegte Strecke (km)": distance,
        "Beschleunigung (m/s²)": acceleration
    })
    return df

# DataFrame mit den Fahrdaten erstellen
fahrdaten_df = generate_kpis_data_from_logs()

'''    df = pd.DataFrame({
        "Zeit": timestamps,
        "Geschwindigkeit (km/h)": speed,
        "Zurückgelegte Strecke (km)": distance,
        "Beschleunigung (m/s²)": acceleration
    }'''
'''    {
        "timestamp": 1750685210.8056064,
        "speed": 30,
        "steering_angle": 90,
        "direction": 1,
        "distance_cm": 107
    }'''
# Daten aus dem DataFrame berechnen
fahrdaten_karten = {
    "maximale_geschwindigkeit": f"{fahrdaten_df['Geschwindigkeit (km/h)'].max():.2f} km/h",
    "minimale_geschwindigkeit": f"{fahrdaten_df['Geschwindigkeit (km/h)'].min():.2f} km/h",
    "durchschnittsgeschwindigkeit": f"{fahrdaten_df['Geschwindigkeit (km/h)'].mean():.2f} km/h",
    "gesamtfahrstrecke": f"{fahrdaten_df['Zurückgelegte Strecke (km)'].iloc[-1]:.2f} km",
    "gesamtfahrzeit": "1.00 Minute" # Da wir 60s simulieren
}

# --- 3. Hilfsfunktionen ---
def create_data_card(title, value):
    return dbc.Card(
        dbc.CardBody([
            html.H6(title, className="card-title-custom"),
            html.H2(value, className="card-value-custom"),
        ]),
        className="data-card text-center m-3",
    )

# --- 4. Das Layout der App definieren (erweitert) ---
app.layout = dbc.Container([
    # --- TITELBEREICH ---
    html.H1("PiCarStats Dashboard", className="text-center mt-5 mb-2 main-title"),
    html.P("Not gonna lie, the styles.css is completely generated lol", className="text-center text-muted mb-5"),

    # --- KARTEN-BEREICH ---
    dbc.Row([
        dbc.Col(create_data_card("MAXIMALE GESCHWINDIGKEIT", fahrdaten_karten["maximale_geschwindigkeit"]), lg=3, md=6),
        dbc.Col(create_data_card("MINIMALE GESCHWINDIGKEIT", fahrdaten_karten["minimale_geschwindigkeit"]), lg=3, md=6),
        dbc.Col(create_data_card("DURCHSCHNITTSGESCHWINDIGKEIT", fahrdaten_karten["durchschnittsgeschwindigkeit"]), lg=3, md=6),
        dbc.Col(create_data_card("GESAMTFAHRSTRECKE", fahrdaten_karten["gesamtfahrstrecke"]), lg=3, md=6),
    ], justify="center"),
    dbc.Row([
        dbc.Col(create_data_card("GESAMTFAHRZEIT", fahrdaten_karten["gesamtfahrzeit"]), lg=3, md=6),
    ], justify="center"),

    # --- STEUERUNGSBEREICH (Anforderung 1) ---
    html.Div([
        html.P("Wähle ein Fahrmodus zum Ausführen:", className="mt-5"),
        dbc.InputGroup([
            dcc.Dropdown(
                id='fahrmodus-dropdown',
                options=[
                    {'label': 'DriveMode 1', 'value': 'Normal'},
                    {'label': 'DriveMode 2', 'value': 'Sport'},
                    {'label': 'DriveMode 3', 'value': 'Eco'},
                    {'label': 'DriveMode 4', 'value': 'Comfort'},                    
                ],
                value='Normal', # Standardwert setzen
                placeholder="Fahrmodus auswählen",
                className="dropdown-custom flex-grow-1"
            ),
            dbc.Button("Fahrt starten", id="start-button", color="primary", n_clicks=0),
        ]),
        # Bereich für Benachrichtigungen (z.B. "Fahrt gestartet")
        dbc.Alert(id="start-notification", is_open=False, duration=4000, className="mt-3"),
    ], className="text-center mt-4", style={'maxWidth': '500px', 'margin': 'auto'}),
    
    # --- GRAFIK-BEREICH (Anforderung 2 & 3) ---
    html.Div([
        html.H3("Zeitliche Entwicklung der Fahrdaten", className="text-center mt-5 mb-4"),
        
        # Dropdown zur Auswahl der Daten für den Graphen
        dcc.Dropdown(
            id='graph-data-selector',
            options=[
                {'label': 'Geschwindigkeit', 'value': 'Geschwindigkeit (km/h)'},
                {'label': 'Zurückgelegte Strecke', 'value': 'Zurückgelegte Strecke (km)'},
                {'label': 'Beschleunigung', 'value': 'Beschleunigung (m/s²)'},
            ],
            value='Geschwindigkeit (km/h)', # Standard-Auswahl
            clearable=False,
            className="dropdown-custom mb-4"
        ),
        
        # Der Graph selbst
        dcc.Graph(id='time-series-graph'),
        
    ], style={'maxWidth': '900px', 'margin': 'auto', 'marginTop': '3rem'}),

], fluid=False)

# --- 5. Callbacks für die Interaktivität ---

# Callback für den Start-Button (Anforderung 1)
@app.callback(
    Output("start-notification", "is_open"),
    Output("start-notification", "children"),
    Input("start-button", "n_clicks"),
    State("fahrmodus-dropdown", "value"),
    prevent_initial_call=True # Verhindert Ausführung bei App-Start
)
def handle_start_button(n_clicks, selected_mode):
    if n_clicks > 0:
        message = f"Fahrt im '{selected_mode}' Modus gestartet. (Simulation)"
        # In einer echten App würde hier der Code zur Steuerung des Autos aufgerufen.
        print(message) 
        return True, message
    return False, ""

# Callback zur Aktualisierung des Graphen (Anforderung 2 & 3)
@app.callback(
    Output("time-series-graph", "figure"),
    Input("graph-data-selector", "value")
)
def update_graph(selected_metric):
    # Erstelle eine Liniengrafik mit Plotly Express
    fig = px.line(
        fahrdaten_df, 
        x="Zeit", 
        y=selected_metric, 
        title=f"Verlauf: {selected_metric}",
        template="plotly_dark" # Nutzt ein passendes dunkles Template
    )
    
    # Passe das Layout an unser "Glassmorphism"-Design an
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", # Transparenter Hintergrund des Papiers
        plot_bgcolor="rgba(43, 52, 79, 0.35)", # Passender Hintergrund für den Plotbereich
        font_color="#c8d6e5",
        title_font_size=20,
        xaxis=dict(gridcolor='rgba(255, 255, 255, 0.1)'),
        yaxis=dict(gridcolor='rgba(255, 255, 255, 0.1)'),
        margin=dict(l=20, r=20, t=40, b=20)
    )
    
    # Passe die Farbe der Linie an
    fig.update_traces(line=dict(color="#89cff0", width=2))
    
    return fig
if __name__ == '__main__':
    #app.run_server(debug=True)
    app.run_server(host = '0.0.0.0', port=8080, debug=True)
    