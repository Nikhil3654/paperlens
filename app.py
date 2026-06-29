from pathlib import Path

streamlit_app = Path(__file__).parent / "app" / "streamlit_app.py"
exec(streamlit_app.read_text())
