import uvicorn


if __name__ == '__main__':
    uvicorn.run('simulator.mcu.app:app', host='127.0.0.1', port=9102)