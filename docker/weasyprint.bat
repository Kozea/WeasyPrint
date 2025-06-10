@ECHO OFF
REM weasyprint for Windows, via Docker

docker run -v ".:/data" --rm -it weasyprint %*
