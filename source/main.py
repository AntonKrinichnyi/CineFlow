from fastapi import FastAPI


app = FastAPI()

@app.get("/")
async def start_root():
    return {"message": "Hello everyone!"}