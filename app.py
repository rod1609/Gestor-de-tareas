import json
import os
import smtplib
from email.message import EmailMessage

from flask import Flask, request, redirect, url_for, render_template_string

app = Flask(__name__)

# Rutas de archivo
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TAREAS_FILE = os.path.join(BASE_DIR, "tareas.json")
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

# Configuración de correo
EMAIL_FROM = os.environ.get("TASKS_EMAIL_FROM", "romartelo08@gmail.com")
EMAIL_PASSWORD = os.environ.get("TASKS_EMAIL_PASSWORD", "qahadfbtsxlvuqhy")
email_destino = os.environ.get("TASKS_EMAIL_TO", EMAIL_FROM)

# Datos en memoria
# Cada tarea es un diccionario: {"id": int, "texto": str, "hecho": bool}
tareas = []
proximo_id = 1


def cargar_config():
  global email_destino
  if not os.path.exists(CONFIG_FILE):
    return
  try:
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
      data = json.load(f)
  except (json.JSONDecodeError, OSError):
    return

  if isinstance(data, dict) and "email_destino" in data:
    email_destino = data["email_destino"]


def guardar_config():
  data = {"email_destino": email_destino}
  try:
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
      json.dump(data, f, ensure_ascii=False, indent=2)
  except OSError:
    pass


def cargar_tareas():
  """Carga las tareas desde el archivo JSON (si existe)."""
  global tareas, proximo_id
  if os.path.exists(TAREAS_FILE):
    try:
      with open(TAREAS_FILE, "r", encoding="utf-8") as f:
        tareas_cargadas = json.load(f)
      if isinstance(tareas_cargadas, list):
        tareas[:] = tareas_cargadas
      else:
        tareas[:] = []
    except (json.JSONDecodeError, OSError):
      tareas[:] = []
  else:
    tareas[:] = []

  if tareas:
    proximo_id = max(t["id"] for t in tareas) + 1
  else:
    proximo_id = 1


def guardar_tareas():
  """Guarda la lista de tareas actual en el archivo JSON."""
  try:
    with open(TAREAS_FILE, "w", encoding="utf-8") as f:
      json.dump(tareas, f, ensure_ascii=False, indent=2)
  except OSError:
    pass


def enviar_recordatorio_por_email(tarea):
  """Envía un correo de recordatorio para una tarea."""
  if not EMAIL_FROM or not EMAIL_PASSWORD or not email_destino:
    return

  asunto = f"Recordatorio de tarea #{tarea['id']}"
  cuerpo = f"""Has creado una nueva tarea:

ID: {tarea['id']}
Texto: {tarea['texto']}
Estado: {'Completada' if tarea.get('hecho') else 'Pendiente'}

Este es un recordatorio automático de tu gestor de tareas en Flask.
"""

  msg = EmailMessage()
  msg["Subject"] = asunto
  msg["From"] = EMAIL_FROM
  msg["To"] = email_destino
  msg.set_content(cuerpo)

  try:
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
      server.starttls()
      server.login(EMAIL_FROM, EMAIL_PASSWORD)
      server.send_message(msg)
  except Exception:
    # No romper la app si falla el envío
    pass


# Cargar config y tareas al arrancar
cargar_config()
cargar_tareas()


PLANTILLA_INDEX = """
<!doctype html>
<html lang="es">
  <head>
    <meta charset="utf-8">
    <title>Gestor de tareas</title>
    <style>
      body {
        font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        margin: 0;
        padding: 0;
        background: #f3f4f6;
      }
      .container {
        max-width: 800px;
        margin: 40px auto;
        background: #ffffff;
        border-radius: 12px;
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.05);
        padding: 24px 28px 32px;
      }
      h1 {
        margin-top: 0;
        font-size: 1.8rem;
      }
      form {
        display: flex;
        gap: 8px;
        margin-bottom: 20px;
      }
      input[type="text"],
      input[type="email"] {
        flex: 1;
        padding: 8px 10px;
        border-radius: 6px;
        border: 1px solid #d1d5db;
        font-size: 0.95rem;
      }
      button {
        padding: 8px 14px;
        border-radius: 6px;
        border: none;
        background: #2563eb;
        color: #ffffff;
        cursor: pointer;
        font-size: 0.95rem;
      }
      button:hover {
        background: #1d4ed8;
      }
      ul {
        list-style: none;
        padding: 0;
        margin: 0;
      }
      li {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 8px 0;
        border-bottom: 1px solid #e5e7eb;
      }
      li:last-child {
        border-bottom: none;
      }
      .tarea-texto.hecha {
        text-decoration: line-through;
        color: #6b7280;
      }
      .badge {
        font-size: 0.75rem;
        padding: 2px 6px;
        border-radius: 999px;
        background: #e5e7eb;
        color: #374151;
        margin-left: 6px;
      }
      .acciones {
        display: flex;
        gap: 8px;
        align-items: center;
      }
      .link-accion {
        font-size: 0.85rem;
        text-decoration: none;
      }
      .link-accion:hover {
        text-decoration: underline;
      }
      .link-completar {
        color: #059669;
      }
      .link-editar {
        color: #2563eb;
      }
      .link-eliminar {
        color: #dc2626;
      }
      .empty {
        color: #9ca3af;
        font-size: 0.95rem;
        padding: 4px 0;
      }
      .config-email {
        margin-bottom: 24px;
        padding: 12px 14px;
        border-radius: 8px;
        background: #eff6ff;
        border: 1px solid #dbeafe;
      }
      .config-email h2 {
        margin: 0 0 8px;
        font-size: 1rem;
      }
      .config-email small {
        display: block;
        margin-top: 4px;
        color: #6b7280;
      }
    </style>
  </head>
  <body>
    <div class="container">
      <h1>Gestor de tareas</h1>

      <section class="config-email">
        <h2>Correo para recordatorios</h2>
        <form action="{{ url_for('config_correo') }}" method="post">
          <input
            type="email"
            name="email"
            placeholder="tu_correo@gmail.com"
            value="{{ email_destino or '' }}"
            required
          >
          <button type="submit">Guardar correo</button>
        </form>
        <small>
          Se enviará un correo cada vez que crees una nueva tarea.
        </small>
      </section>

      <form action="{{ url_for('agregar') }}" method="post">
        <input
          type="text"
          name="texto"
          placeholder="Escribe una nueva tarea..."
          required
        >
        <button type="submit">Agregar tarea</button>
      </form>

      {% if tareas %}
      <ul>
        {% for tarea in tareas %}
        <li>
          <span class="tarea-texto {% if tarea.hecho %}hecha{% endif %}">
            {{ tarea.texto }}
            {% if tarea.hecho %}
              <span class="badge">Completada</span>
            {% endif %}
          </span>
          <div class="acciones">
            {% if not tarea.hecho %}
            <a
              class="link-accion link-completar"
              href="{{ url_for('completar', id=tarea.id) }}"
            >
              Completar
            </a>
            {% else %}
            <span style="font-size: 0.8rem; color: #9ca3af;">✔</span>
            {% endif %}
            <a
              class="link-accion link-editar"
              href="{{ url_for('editar', id=tarea.id) }}"
            >
              Editar
            </a>
            <a
              class="link-accion link-eliminar"
              href="{{ url_for('eliminar', id=tarea.id) }}"
            >
              Eliminar
            </a>
          </div>
        </li>
        {% endfor %}
      </ul>
      {% else %}
        <p class="empty">No hay tareas todavía. Agrega la primera.</p>
      {% endif %}
    </div>
  </body>
</html>
"""


PLANTILLA_EDITAR = """
<!doctype html>
<html lang="es">
  <head>
    <meta charset="utf-8">
    <title>Editar tarea</title>
    <style>
      body {
        font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        margin: 0;
        padding: 0;
        background: #f3f4f6;
      }
      .container {
        max-width: 600px;
        margin: 40px auto;
        background: #ffffff;
        border-radius: 12px;
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.05);
        padding: 24px 28px 32px;
      }
      h1 {
        margin-top: 0;
        font-size: 1.6rem;
      }
      form {
        display: flex;
        gap: 8px;
        margin-bottom: 16px;
      }
      input[type="text"] {
        flex: 1;
        padding: 8px 10px;
        border-radius: 6px;
        border: 1px solid #d1d5db;
        font-size: 0.95rem;
      }
      button {
        padding: 8px 14px;
        border-radius: 6px;
        border: none;
        background: #2563eb;
        color: #ffffff;
        cursor: pointer;
        font-size: 0.95rem;
      }
      button:hover {
        background: #1d4ed8;
      }
      a {
        font-size: 0.9rem;
        color: #6b7280;
        text-decoration: none;
      }
      a:hover {
        text-decoration: underline;
      }
    </style>
  </head>
  <body>
    <div class="container">
      <h1>Editar tarea</h1>
      <form method="post">
        <input
          type="text"
          name="texto"
          value="{{ tarea.texto }}"
          required
        >
        <button type="submit">Guardar</button>
      </form>
      <a href="{{ url_for('index') }}">Volver a la lista</a>
    </div>
  </body>
</html>
"""


@app.route("/")
def index():
  return render_template_string(PLANTILLA_INDEX, tareas=tareas, email_destino=email_destino)


@app.route("/config-correo", methods=["POST"])
def config_correo():
  global email_destino
  email = request.form.get("email", "").strip()
  if email:
    email_destino = email
    guardar_config()
  return redirect(url_for("index"))


@app.route("/agregar", methods=["POST"])
def agregar():
  global proximo_id
  texto = request.form.get("texto", "").strip()
  if texto:
    tarea = {"id": proximo_id, "texto": texto, "hecho": False}
    tareas.append(tarea)
    proximo_id += 1
    guardar_tareas()
    enviar_recordatorio_por_email(tarea)
  return redirect(url_for("index"))


@app.route("/completar/<int:id>")
def completar(id):
  for tarea in tareas:
    if tarea["id"] == id:
      tarea["hecho"] = True
      break
  guardar_tareas()
  return redirect(url_for("index"))


@app.route("/eliminar/<int:id>")
def eliminar(id):
  global tareas
  tareas = [t for t in tareas if t["id"] != id]
  guardar_tareas()
  return redirect(url_for("index"))


@app.route("/editar/<int:id>", methods=["GET", "POST"])
def editar(id):
  tarea = next((t for t in tareas if t["id"] == id), None)
  if not tarea:
    return redirect(url_for("index"))

  if request.method == "POST":
    texto = request.form.get("texto", "").strip()
    if texto:
      tarea["texto"] = texto
      guardar_tareas()
    return redirect(url_for("index"))

  return render_template_string(PLANTILLA_EDITAR, tarea=tarea)


if __name__ == "__main__":
  app.run(debug=True)

import json
import os
import smtplib
from email.message import EmailMessage

from flask import Flask, request, redirect, url_for, render_template_string

app = Flask(__name__)

# Archivo donde se guardan las tareas (JSON)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TAREAS_FILE = os.path.join(BASE_DIR, "tareas.json")

# Configuración básica de correo (rellena estos valores)
EMAIL_FROM = os.environ.get("TASKS_EMAIL_FROM", "romartelo08@gmail.com")
EMAIL_PASSWORD = os.environ.get("TASKS_EMAIL_PASSWORD", "qahadfbtsxlvuqhy")
EMAIL_TO = os.environ.get("TASKS_EMAIL_TO", EMAIL_FROM)

# Lista en memoria para las tareas
# Cada tarea es un diccionario: {"id": int, "texto": str, "hecho": bool}
tareas = []
proximo_id = 1


def cargar_tareas():
  """Carga las tareas desde el archivo JSON (si existe)."""
  global tareas, proximo_id
  if os.path.exists(TAREAS_FILE):
    try:
      with open(TAREAS_FILE, "r", encoding="utf-8") as f:
        tareas_cargadas = json.load(f)
      if isinstance(tareas_cargadas, list):
        tareas[:] = tareas_cargadas
      else:
        tareas[:] = []
    except (json.JSONDecodeError, OSError):
      tareas[:] = []
  else:
    tareas[:] = []

  if tareas:
    proximo_id = max(t["id"] for t in tareas) + 1
  else:
    proximo_id = 1


def guardar_tareas():
  """Guarda la lista de tareas actual en el archivo JSON."""
  try:
    with open(TAREAS_FILE, "w", encoding="utf-8") as f:
      json.dump(tareas, f, ensure_ascii=False, indent=2)
  except OSError:
    # En un proyecto real, aquí se podría registrar el error
    pass


def enviar_recordatorio_por_email(tarea):
  """Envía un correo de recordatorio a Gmail para una tarea."""
  if not EMAIL_FROM or not EMAIL_PASSWORD or not EMAIL_TO:
    return

  asunto = f"Recordatorio de tarea #{tarea['id']}"
  cuerpo = f"""Has creado una nueva tarea:

ID: {tarea['id']}
Texto: {tarea['texto']}
Estado: {'Completada' if tarea.get('hecho') else 'Pendiente'}

Este es un recordatorio automático de tu gestor de tareas en Flask.
"""

  msg = EmailMessage()
  msg["Subject"] = asunto
  msg["From"] = EMAIL_FROM
  msg["To"] = EMAIL_TO
  msg.set_content(cuerpo)

  try:
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
      server.starttls()
      server.login(EMAIL_FROM, EMAIL_PASSWORD)
      server.send_message(msg)
  except Exception as e:
    print("Error al enviar correo:", e)

# Cargar tareas al iniciar la aplicación
cargar_tareas()


PLANTILLA_INDEX = """
<!doctype html>
<html lang="es">
  <head>
    <meta charset="utf-8">
    <title>Gestor de tareas</title>
    <style>
      body {
        font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        margin: 0;
        padding: 0;
        background: #f3f4f6;
      }
      .container {
        max-width: 800px;
        margin: 40px auto;
        background: #ffffff;
        border-radius: 12px;
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.05);
        padding: 24px 28px 32px;
      }
      h1 {
        margin-top: 0;
        font-size: 1.8rem;
      }
      form {
        display: flex;
        gap: 8px;
        margin-bottom: 20px;
      }
      input[type="text"] {
        flex: 1;
        padding: 8px 10px;
        border-radius: 6px;
        border: 1px solid #d1d5db;
        font-size: 0.95rem;
      }
      button {
        padding: 8px 14px;
        border-radius: 6px;
        border: none;
        background: #2563eb;
        color: #ffffff;
        cursor: pointer;
        font-size: 0.95rem;
      }
      button:hover {
        background: #1d4ed8;
      }
      ul {
        list-style: none;
        padding: 0;
        margin: 0;
      }
      li {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 8px 0;
        border-bottom: 1px solid #e5e7eb;
      }
      li:last-child {
        border-bottom: none;
      }
      .tarea-texto.hecha {
        text-decoration: line-through;
        color: #6b7280;
      }
      .badge {
        font-size: 0.75rem;
        padding: 2px 6px;
        border-radius: 999px;
        background: #e5e7eb;
        color: #374151;
        margin-left: 6px;
      }
      .acciones {
        display: flex;
        gap: 8px;
        align-items: center;
      }
      .link-accion {
        font-size: 0.85rem;
        text-decoration: none;
      }
      .link-accion:hover {
        text-decoration: underline;
      }
      .link-completar {
        color: #059669;
      }
      .link-editar {
        color: #2563eb;
      }
      .link-eliminar {
        color: #dc2626;
      }
      .empty {
        color: #9ca3af;
        font-size: 0.95rem;
        padding: 4px 0;
      }
    </style>
  </head>
  <body>
    <div class="container">
      <h1>Gestor de tareas</h1>

      <form action="{{ url_for('agregar') }}" method="post">
        <input
          type="text"
          name="texto"
          placeholder="Escribe una nueva tarea..."
          required
        >
        <button type="submit">Agregar</button>
      </form>

      {% if tareas %}
      <ul>
        {% for tarea in tareas %}
        <li>
          <span class="tarea-texto {% if tarea.hecho %}hecha{% endif %}">
            {{ tarea.texto }}
            {% if tarea.hecho %}
              <span class="badge">Completada</span>
            {% endif %}
          </span>
          <div class="acciones">
            {% if not tarea.hecho %}
            <a
              class="link-accion link-completar"
              href="{{ url_for('completar', id=tarea.id) }}"
            >
              Completar
            </a>
            {% else %}
            <span style="font-size: 0.8rem; color: #9ca3af;">✔</span>
            {% endif %}
            <a
              class="link-accion link-editar"
              href="{{ url_for('editar', id=tarea.id) }}"
            >
              Editar
            </a>
            <a
              class="link-accion link-eliminar"
              href="{{ url_for('eliminar', id=tarea.id) }}"
            >
              Eliminar
            </a>
          </div>
        </li>
        {% endfor %}
      </ul>
      {% else %}
        <p class="empty">No hay tareas todavía. Agrega la primera.</p>
      {% endif %}
    </div>
  </body>
</html>
"""


PLANTILLA_EDITAR = """
<!doctype html>
<html lang="es">
  <head>
    <meta charset="utf-8">
    <title>Editar tarea</title>
    <style>
      body {
        font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        margin: 0;
        padding: 0;
        background: #f3f4f6;
      }
      .container {
        max-width: 600px;
        margin: 40px auto;
        background: #ffffff;
        border-radius: 12px;
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.05);
        padding: 24px 28px 32px;
      }
      h1 {
        margin-top: 0;
        font-size: 1.6rem;
      }
      form {
        display: flex;
        gap: 8px;
        margin-bottom: 16px;
      }
      input[type="text"] {
        flex: 1;
        padding: 8px 10px;
        border-radius: 6px;
        border: 1px solid #d1d5db;
        font-size: 0.95rem;
      }
      button {
        padding: 8px 14px;
        border-radius: 6px;
        border: none;
        background: #2563eb;
        color: #ffffff;
        cursor: pointer;
        font-size: 0.95rem;
      }
      button:hover {
        background: #1d4ed8;
      }
      a {
        font-size: 0.9rem;
        color: #6b7280;
        text-decoration: none;
      }
      a:hover {
        text-decoration: underline;
      }
    </style>
  </head>
  <body>
    <div class="container">
      <h1>Editar tarea</h1>
      <form method="post">
        <input
          type="text"
          name="texto"
          value="{{ tarea.texto }}"
          required
        >
        <button type="submit">Guardar</button>
      </form>
      <a href="{{ url_for('index') }}">Volver a la lista</a>
    </div>
  </body>
</html>
"""


@app.route("/")
def index():
  return render_template_string(PLANTILLA_INDEX, tareas=tareas)


@app.route("/agregar", methods=["POST"])
def agregar():
  global proximo_id
  texto = request.form.get("texto", "").strip()
  if texto:
    tarea = {"id": proximo_id, "texto": texto, "hecho": False}
    tareas.append(tarea)
    proximo_id += 1
    guardar_tareas()
    enviar_recordatorio_por_email(tarea)
  return redirect(url_for("index"))


@app.route("/completar/<int:id>")
def completar(id):
  for tarea in tareas:
    if tarea["id"] == id:
      tarea["hecho"] = True
      break
  guardar_tareas()
  return redirect(url_for("index"))


@app.route("/eliminar/<int:id>")
def eliminar(id):
  global tareas
  tareas = [t for t in tareas if t["id"] != id]
  guardar_tareas()
  return redirect(url_for("index"))


@app.route("/editar/<int:id>", methods=["GET", "POST"])
def editar(id):
  tarea = next((t for t in tareas if t["id"] == id), None)
  if not tarea:
    return redirect(url_for("index"))

  if request.method == "POST":
    texto = request.form.get("texto", "").strip()
    if texto:
      tarea["texto"] = texto
      guardar_tareas()
    return redirect(url_for("index"))

  return render_template_string(PLANTILLA_EDITAR, tarea=tarea)


if __name__ == "__main__":
  app.run(debug=True)

import json
import os
from flask import Flask, request, redirect, url_for, render_template_string

app = Flask(__name__)

# Archivo donde se guardan las tareas (JSON)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TAREAS_FILE = os.path.join(BASE_DIR, "tareas.json")

# Lista en memoria para las tareas
# Cada tarea es un diccionario: {"id": int, "texto": str, "hecho": bool}
tareas = []
proximo_id = 1


def cargar_tareas():
  """Carga las tareas desde el archivo JSON (si existe)."""
  global tareas, proximo_id
  if os.path.exists(TAREAS_FILE):
    try:
      with open(TAREAS_FILE, "r", encoding="utf-8") as f:
        tareas_cargadas = json.load(f)
      if isinstance(tareas_cargadas, list):
        tareas[:] = tareas_cargadas
      else:
        tareas[:] = []
    except (json.JSONDecodeError, OSError):
      tareas[:] = []
  else:
    tareas[:] = []

  if tareas:
    proximo_id = max(t["id"] for t in tareas) + 1
  else:
    proximo_id = 1


def guardar_tareas():
  """Guarda la lista de tareas actual en el archivo JSON."""
  try:
    with open(TAREAS_FILE, "w", encoding="utf-8") as f:
      json.dump(tareas, f, ensure_ascii=False, indent=2)
  except OSError:
    # En un proyecto real, aquí se podría registrar el error
    pass


# Cargar tareas al iniciar la aplicación
cargar_tareas()


PLANTILLA_INDEX = """
<!doctype html>
<html lang="es">
  <head>
    <meta charset="utf-8">
    <title>Gestor de tareas</title>
    <style>
      body {
        font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        margin: 0;
        padding: 0;
        background: #f3f4f6;
      }
      .container {
        max-width: 800px;
        margin: 40px auto;
        background: #ffffff;
        border-radius: 12px;
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.05);
        padding: 24px 28px 32px;
      }
      h1 {
        margin-top: 0;
        font-size: 1.8rem;
      }
      form {
        display: flex;
        gap: 8px;
        margin-bottom: 20px;
      }
      input[type="text"] {
        flex: 1;
        padding: 8px 10px;
        border-radius: 6px;
        border: 1px solid #d1d5db;
        font-size: 0.95rem;
      }
      button {
        padding: 8px 14px;
        border-radius: 6px;
        border: none;
        background: #2563eb;
        color: #ffffff;
        cursor: pointer;
        font-size: 0.95rem;
      }
      button:hover {
        background: #1d4ed8;
      }
      ul {
        list-style: none;
        padding: 0;
        margin: 0;
      }
      li {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 8px 0;
        border-bottom: 1px solid #e5e7eb;
      }
      li:last-child {
        border-bottom: none;
      }
      .tarea-texto.hecha {
        text-decoration: line-through;
        color: #6b7280;
      }
      .badge {
        font-size: 0.75rem;
        padding: 2px 6px;
        border-radius: 999px;
        background: #e5e7eb;
        color: #374151;
        margin-left: 6px;
      }
      .acciones {
        display: flex;
        gap: 8px;
        align-items: center;
      }
      .link-accion {
        font-size: 0.85rem;
        text-decoration: none;
      }
      .link-accion:hover {
        text-decoration: underline;
      }
      .link-completar {
        color: #059669;
      }
      .link-editar {
        color: #2563eb;
      }
      .link-eliminar {
        color: #dc2626;
      }
      .empty {
        color: #9ca3af;
        font-size: 0.95rem;
        padding: 4px 0;
      }
    </style>
  </head>
  <body>
    <div class="container">
      <h1>Gestor de tareas</h1>

      <form action="{{ url_for('agregar') }}" method="post">
        <input
          type="text"
          name="texto"
          placeholder="Escribe una nueva tarea..."
          required
        >
        <button type="submit">Agregar</button>
      </form>

      {% if tareas %}
      <ul>
        {% for tarea in tareas %}
        <li>
          <span class="tarea-texto {% if tarea.hecho %}hecha{% endif %}">
            {{ tarea.texto }}
            {% if tarea.hecho %}
              <span class="badge">Completada</span>
            {% endif %}
          </span>
          <div class="acciones">
            {% if not tarea.hecho %}
            <a
              class="link-accion link-completar"
              href="{{ url_for('completar', id=tarea.id) }}"
            >
              Completar
            </a>
            {% else %}
            <span style="font-size: 0.8rem; color: #9ca3af;">✔</span>
            {% endif %}
            <a
              class="link-accion link-editar"
              href="{{ url_for('editar', id=tarea.id) }}"
            >
              Editar
            </a>
            <a
              class="link-accion link-eliminar"
              href="{{ url_for('eliminar', id=tarea.id) }}"
            >
              Eliminar
            </a>
          </div>
        </li>
        {% endfor %}
      </ul>
      {% else %}
        <p class="empty">No hay tareas todavía. Agrega la primera.</p>
      {% endif %}
    </div>
  </body>
</html>
"""


PLANTILLA_EDITAR = """
<!doctype html>
<html lang="es">
  <head>
    <meta charset="utf-8">
    <title>Editar tarea</title>
    <style>
      body {
        font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        margin: 0;
        padding: 0;
        background: #f3f4f6;
      }
      .container {
        max-width: 600px;
        margin: 40px auto;
        background: #ffffff;
        border-radius: 12px;
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.05);
        padding: 24px 28px 32px;
      }
      h1 {
        margin-top: 0;
        font-size: 1.6rem;
      }
      form {
        display: flex;
        gap: 8px;
        margin-bottom: 16px;
      }
      input[type="text"] {
        flex: 1;
        padding: 8px 10px;
        border-radius: 6px;
        border: 1px solid #d1d5db;
        font-size: 0.95rem;
      }
      button {
        padding: 8px 14px;
        border-radius: 6px;
        border: none;
        background: #2563eb;
        color: #ffffff;
        cursor: pointer;
        font-size: 0.95rem;
      }
      button:hover {
        background: #1d4ed8;
      }
      a {
        font-size: 0.9rem;
        color: #6b7280;
        text-decoration: none;
      }
      a:hover {
        text-decoration: underline;
      }
    </style>
  </head>
  <body>
    <div class="container">
      <h1>Editar tarea</h1>
      <form method="post">
        <input
          type="text"
          name="texto"
          value="{{ tarea.texto }}"
          required
        >
        <button type="submit">Guardar</button>
      </form>
      <a href="{{ url_for('index') }}">Volver a la lista</a>
    </div>
  </body>
</html>
"""


@app.route("/")
def index():
  return render_template_string(PLANTILLA_INDEX, tareas=tareas)


@app.route("/agregar", methods=["POST"])
def agregar():
  global proximo_id
  texto = request.form.get("texto", "").strip()
  if texto:
    tareas.append({"id": proximo_id, "texto": texto, "hecho": False})
    proximo_id += 1
    guardar_tareas()
  return redirect(url_for("index"))


@app.route("/completar/<int:id>")
def completar(id):
  for tarea in tareas:
    if tarea["id"] == id:
      tarea["hecho"] = True
      break
  guardar_tareas()
  return redirect(url_for("index"))


@app.route("/eliminar/<int:id>")
def eliminar(id):
  global tareas
  tareas = [t for t in tareas if t["id"] != id]
  guardar_tareas()
  return redirect(url_for("index"))


@app.route("/editar/<int:id>", methods=["GET", "POST"])
def editar(id):
  tarea = next((t for t in tareas if t["id"] == id), None)
  if not tarea:
    return redirect(url_for("index"))

  if request.method == "POST":
    texto = request.form.get("texto", "").strip()
    if texto:
      tarea["texto"] = texto
      guardar_tareas()
    return redirect(url_for("index"))

  return render_template_string(PLANTILLA_EDITAR, tarea=tarea)


if __name__ == "__main__":
  app.run(debug=True)

from flask import Flask, request, redirect, url_for, render_template_string

app = Flask(__name__)

# Lista en memoria para las tareas
# Cada tarea es un diccionario: {"id": int, "texto": str, "hecho": bool}
tareas = []
proximo_id = 1


PLANTILLA_INDEX = """
<!doctype html>
<html lang="es">
  <head>
    <meta charset="utf-8">
    <title>Gestor de tareas</title>
    <style>
      body {
        font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        margin: 0;
        padding: 0;
        background: #f3f4f6;
      }
      .container {
        max-width: 800px;
        margin: 40px auto;
        background: #ffffff;
        border-radius: 12px;
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.05);
        padding: 24px 28px 32px;
      }
      h1 {
        margin-top: 0;
        font-size: 1.8rem;
      }
      form {
        display: flex;
        gap: 8px;
        margin-bottom: 20px;
      }
      input[type="text"] {
        flex: 1;
        padding: 8px 10px;
        border-radius: 6px;
        border: 1px solid #d1d5db;
        font-size: 0.95rem;
      }
      button {
        padding: 8px 14px;
        border-radius: 6px;
        border: none;
        background: #2563eb;
        color: #ffffff;
        cursor: pointer;
        font-size: 0.95rem;
      }
      button:hover {
        background: #1d4ed8;
      }
      ul {
        list-style: none;
        padding: 0;
        margin: 0;
      }
      li {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 8px 0;
        border-bottom: 1px solid #e5e7eb;
      }
      li:last-child {
        border-bottom: none;
      }
      .tarea-texto.hecha {
        text-decoration: line-through;
        color: #6b7280;
      }
      .badge {
        font-size: 0.75rem;
        padding: 2px 6px;
        border-radius: 999px;
        background: #e5e7eb;
        color: #374151;
        margin-left: 6px;
      }
      .acciones {
        display: flex;
        gap: 8px;
        align-items: center;
      }
      .link-accion {
        font-size: 0.85rem;
        text-decoration: none;
      }
      .link-accion:hover {
        text-decoration: underline;
      }
      .link-completar {
        color: #059669;
      }
      .link-editar {
        color: #2563eb;
      }
      .link-eliminar {
        color: #dc2626;
      }
      .empty {
        color: #9ca3af;
        font-size: 0.95rem;
        padding: 4px 0;
      }
    </style>
  </head>
  <body>
    <div class="container">
      <h1>Gestor de tareas</h1>

      <form action="{{ url_for('agregar') }}" method="post">
        <input
          type="text"
          name="texto"
          placeholder="Escribe una nueva tarea..."
          required
        >
        <button type="submit">Agregar</button>
      </form>

      {% if tareas %}
      <ul>
        {% for tarea in tareas %}
        <li>
          <span class="tarea-texto {% if tarea.hecho %}hecha{% endif %}">
            {{ tarea.texto }}
            {% if tarea.hecho %}
              <span class="badge">Completada</span>
            {% endif %}
          </span>
          <div class="acciones">
            {% if not tarea.hecho %}
            <a
              class="link-accion link-completar"
              href="{{ url_for('completar', id=tarea.id) }}"
            >
              Completar
            </a>
            {% else %}
            <span style="font-size: 0.8rem; color: #9ca3af;">✔</span>
            {% endif %}
            <a
              class="link-accion link-editar"
              href="{{ url_for('editar', id=tarea.id) }}"
            >
              Editar
            </a>
            <a
              class="link-accion link-eliminar"
              href="{{ url_for('eliminar', id=tarea.id) }}"
            >
              Eliminar
            </a>
          </div>
        </li>
        {% endfor %}
      </ul>
      {% else %}
        <p class="empty">No hay tareas todavía. Agrega la primera.</p>
      {% endif %}
    </div>
  </body>
</html>
"""


PLANTILLA_EDITAR = """
<!doctype html>
<html lang="es">
  <head>
    <meta charset="utf-8">
    <title>Editar tarea</title>
    <style>
      body {
        font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        margin: 0;
        padding: 0;
        background: #f3f4f6;
      }
      .container {
        max-width: 600px;
        margin: 40px auto;
        background: #ffffff;
        border-radius: 12px;
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.05);
        padding: 24px 28px 32px;
      }
      h1 {
        margin-top: 0;
        font-size: 1.6rem;
      }
      form {
        display: flex;
        gap: 8px;
        margin-bottom: 16px;
      }
      input[type="text"] {
        flex: 1;
        padding: 8px 10px;
        border-radius: 6px;
        border: 1px solid #d1d5db;
        font-size: 0.95rem;
      }
      button {
        padding: 8px 14px;
        border-radius: 6px;
        border: none;
        background: #2563eb;
        color: #ffffff;
        cursor: pointer;
        font-size: 0.95rem;
      }
      button:hover {
        background: #1d4ed8;
      }
      a {
        font-size: 0.9rem;
        color: #6b7280;
        text-decoration: none;
      }
      a:hover {
        text-decoration: underline;
      }
    </style>
  </head>
  <body>
    <div class="container">
      <h1>Editar tarea</h1>
      <form method="post">
        <input
          type="text"
          name="texto"
          value="{{ tarea.texto }}"
          required
        >
        <button type="submit">Guardar</button>
      </form>
      <a href="{{ url_for('index') }}">Volver a la lista</a>
    </div>
  </body>
</html>
"""


@app.route("/")
def index():
  return render_template_string(PLANTILLA_INDEX, tareas=tareas)


@app.route("/agregar", methods=["POST"])
def agregar():
  global proximo_id
  texto = request.form.get("texto", "").strip()
  if texto:
    tareas.append({"id": proximo_id, "texto": texto, "hecho": False})
    proximo_id += 1
  return redirect(url_for("index"))


@app.route("/completar/<int:id>")
def completar(id):
  for tarea in tareas:
    if tarea["id"] == id:
      tarea["hecho"] = True
      break
  return redirect(url_for("index"))


@app.route("/eliminar/<int:id>")
def eliminar(id):
  global tareas
  tareas = [t for t in tareas if t["id"] != id]
  return redirect(url_for("index"))


@app.route("/editar/<int:id>", methods=["GET", "POST"])
def editar(id):
  tarea = next((t for t in tareas if t["id"] == id), None)
  if not tarea:
    return redirect(url_for("index"))

  if request.method == "POST":
    texto = request.form.get("texto", "").strip()
    if texto:
      tarea["texto"] = texto
    return redirect(url_for("index"))

  return render_template_string(PLANTILLA_EDITAR, tarea=tarea)


if __name__ == "__main__":
  app.run(debug=True)

from flask import Flask, request, redirect, url_for, render_template_string

app = Flask(__name__)

# Lista en memoria para las tareas
# Cada tarea es un diccionario: {"id": int, "texto": str, "hecho": bool}
tareas = []
proximo_id = 1


PLANTILLA_INDEX = """
<!doctype html>
<html lang="es">
  <head>
    <meta charset="utf-8">
    <title>Gestor de tareas</title>
    <style>
      body {
        font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        margin: 0;
        padding: 0;
        background: #f3f4f6;
      }
      .container {
        max-width: 800px;
        margin: 40px auto;
        background: #ffffff;
        border-radius: 12px;
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.05);
        padding: 24px 28px 32px;
      }
      h1 {
        margin-top: 0;
        font-size: 1.8rem;
      }
      form {
        display: flex;
        gap: 8px;
        margin-bottom: 20px;
      }
      input[type="text"] {
        flex: 1;
        padding: 8px 10px;
        border-radius: 6px;
        border: 1px solid #d1d5db;
        font-size: 0.95rem;
      }
      button {
        padding: 8px 14px;
        border-radius: 6px;
        border: none;
        background: #2563eb;
        color: #ffffff;
        cursor: pointer;
        font-size: 0.95rem;
      }
      button:hover {
        background: #1d4ed8;
      }
      ul {
        list-style: none;
        padding: 0;
        margin: 0;
      }
      li {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 8px 0;
        border-bottom: 1px solid #e5e7eb;
      }
      li:last-child {
        border-bottom: none;
      }
      .tarea-texto.hecha {
        text-decoration: line-through;
        color: #6b7280;
      }
      .badge {
        font-size: 0.75rem;
        padding: 2px 6px;
        border-radius: 999px;
        background: #e5e7eb;
        color: #374151;
        margin-left: 6px;
      }
      .link-completar {
        font-size: 0.85rem;
        color: #059669;
        text-decoration: none;
      }
      .link-completar:hover {
        text-decoration: underline;
      }
      .empty {
        color: #9ca3af;
        font-size: 0.95rem;
        padding: 4px 0;
      }
    </style>
  </head>
  <body>
    <div class="container">
      <h1>Gestor de tareas</h1>

      <form action="{{ url_for('agregar') }}" method="post">
        <input
          type="text"
          name="texto"
          placeholder="Escribe una nueva tarea..."
          required
        >
        <button type="submit">Agregar</button>
      </form>

      {% if tareas %}
      <ul>
        {% for tarea in tareas %}
        <li>
          <span class="tarea-texto {% if tarea.hecho %}hecha{% endif %}">
            {{ tarea.texto }}
            {% if tarea.hecho %}
              <span class="badge">Completada</span>
            {% endif %}
          </span>
          {% if not tarea.hecho %}
          <a
            class="link-completar"
            href="{{ url_for('completar', id=tarea.id) }}"
          >
            Marcar como completada
          </a>
          {% else %}
          <span style="font-size: 0.8rem; color: #9ca3af;">✔</span>
          {% endif %}
        </li>
        {% endfor %}
      </ul>
      {% else %}
        <p class="empty">No hay tareas todavía. Agrega la primera.</p>
      {% endif %}
    </div>
  </body>
</html>
"""


@app.route("/")
def index():
  return render_template_string(PLANTILLA_INDEX, tareas=tareas)


@app.route("/agregar", methods=["POST"])
def agregar():
  global proximo_id
  texto = request.form.get("texto", "").strip()
  if texto:
    tareas.append({"id": proximo_id, "texto": texto, "hecho": False})
    proximo_id += 1
  return redirect(url_for("index"))


@app.route("/completar/<int:id>")
def completar(id):
  for tarea in tareas:
    if tarea["id"] == id:
      tarea["hecho"] = True
      break
  return redirect(url_for("index"))


if __name__ == "__main__":
  app.run(debug=True)