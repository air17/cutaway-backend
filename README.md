# Cutaway Backend

REST API server for [Cutaway](https://github.com/cutaway-inc/cutaway).

## Install

Requirement: Python 3.6 or newer

Install dependencies: `pip install -r requirements.txt`<br>
Start the server: `uvicorn main:app`

Run the tests: `pytest`

## Usage

Build image: `docker build . -t cutaway`

Run it: `docker run -dp 8000:80 --mount source=cutaway-data,target=/app/static --name cutaway cutaway`
<br>This will run application on port 8000.
The pictures will be stored in `cutaway-data` folder.

## API documentation:
#### Automatic interactive API documentation (provided by <a href="https://github.com/swagger-api/swagger-ui" class="external-link" target="_blank">Swagger UI</a>):
When you run the server it will be available at
http://127.0.0.1:8000/docs/

Or you can use demo here:
https://cutaway.161e.tk/docs/

#### Alternative automatic documentation (provided by <a href="https://github.com/Rebilly/ReDoc" class="external-link" target="_blank">ReDoc</a>):
On your server: http://127.0.0.1:8000/redoc

Demo: https://cutaway.161e.tk/redoc/

## Author
[Biulent Ozdzhan](https://github.com/air17)

## License

Apache License 2.0 © 2021 Biulent Ozdzhan
