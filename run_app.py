import threading
import uvicorn
import time
import requests
import webbrowser

def start_api():
    # Arranca FastAPI
    uvicorn.run("api:app", host="127.0.0.1", port=8000)

def wait_for_server():
    # Espera hasta que el servidor esté listo
    url = "http://127.0.0.1:8000"
    while True:
        try:
            requests.get(url)
            break
        except:
            time.sleep(0.5)

if __name__ == "__main__":
    # Ejecuta FastAPI en un hilo en segundo plano
    api_thread = threading.Thread(target=start_api, daemon=True)
    api_thread.start()

    # Espera que el servidor esté listo
    wait_for_server()

    # Abre automáticamente la app en el navegador
    webbrowser.open("http://127.0.0.1:8000")

    # Mantiene el script corriendo mientras el hilo del servidor está activo
    api_thread.join()