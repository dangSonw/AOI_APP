import uvicorn


if __name__ == '__main__':
    uvicorn.run('hardware.mcu.app:app', host='127.0.0.1', port=9102)