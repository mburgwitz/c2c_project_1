import dash
from dash import dcc, html, Output, Input, State
import dash_bootstrap_components as dbc
import plotly.express as px
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = BASE_DIR / "templates"

retro_html = (TEMPLATE_DIR / "retrobackground.html").read_text()
index_template = (TEMPLATE_DIR / "index.html").read_text()
index_string = index_template.replace("{{retro_background}}", retro_html)

# Ersetze Platzhalter {{retro_background}} durch den eigentlichen Inhalt
index_string = index_template.replace("{{retro_background}}", retro_html)

app = dash.Dash(__name__, 
                external_stylesheets=[dbc.themes.BOOTSTRAP],
                assets_folder="assets",
                index_string=index_string
                
                )


header = dcc.Markdown('Pi:Car - Dashboard', className = "retro-header")

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

app.layout = dbc.Container([
        dbc.Row([dbc.Col(header, width = 10),
                 dbc.Col(dbc.DropdownMenu(
                    label="DriveModes",
                    children=[dbc.DropdownMenuItem("Item 1"),
                              dbc.DropdownMenuItem("Item 2"),
                              dbc.DropdownMenuItem("Item 3")],
                    className='driveOptions'
                ), width = 2) 
        ], justify="between", align="center"),

        dbc.Row([
                dbc.Col("Column 1", width=4, style={"backgroundColor": "lightblue"}),
                dbc.Col("Column 2", width=4, style={"backgroundColor": "lightblue"}),
        ],style={"backgroundColor": "gray"}),   

        dbc.Row([dbc.Col(create_card("**Vmax**", "Text 1", "clsC1"), id="col1"),
                 dbc.Col(create_card("**Vmin**", "Text 1", "clsC2")),
                 dbc.Col(create_card("**Ø V**", "Text 1", "clsC3")),
                 dbc.Col(create_card("**Gesamtstrecke**", "Text 1", "clsC4")),
                 dbc.Col(create_card("**Fahrzeit**", "Text 1", "clsC5"))                 
        ], className="g-5", justify="between"),

        

        dbc.Row([
            dbc.Col([
                    dcc.Graph(id='fig_1', figure=fig_1)
                ]),
            dbc.Col([
                dcc.Graph(id='fig_2', figure=fig_2)
            ])
        ]),

])


if __name__ == "__main__":
    app.run_server(debug=True)


