import uvicorn
from app.config import HOST, PORT

if __name__ == "__main__":
    print(f"Starting YouTube MP3/MP4 Converter on http://{HOST}:{PORT}")
    print(f"API Documentation available on http://{HOST}:{PORT}/api/docs")
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=True)
