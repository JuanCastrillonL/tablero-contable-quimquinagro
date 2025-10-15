# tablero-contable-quimquinagro
Aplicación en Streamlit para análisis contable de QuimQuinAgro. Incluye consultas de flujo, caja, egresos e ingresos por socio.


## 🔧 Requisitos
- Python 3.9+ (Anaconda recomendado)
- Paquetes de `requirements.txt`
- Base de datos SQLite: `contabilidad.db`  
  - **Ubicación esperada:** actualizar `DB_PATH` en `app.py` (`C:\Users\TUUSUARIO\Documents\contabilidad.db`) #poner la direccion en la que usted tiene el archivo descargado 
  - O colocarla en la raíz del proyecto y usar `DB_PATH = os.path.join(BASE_DIR, "contabilidad.db")`.

## ▶️ Ejecución
```bash
pip install -r requirements.txt
streamlit run app.py
