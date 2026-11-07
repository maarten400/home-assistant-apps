FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && python -m playwright install --with-deps chromium && apt-get update && apt-get install -y --no-install-recommends xvfb x11vnc novnc websockify nginx && rm -rf /var/lib/apt/lists/* && useradd --uid 10001 --create-home api && mkdir /data && chmod -R a+rX /opt/pw-browsers
COPY app.py parser.py browser.py settings.py run.py nginx.conf ./
COPY setup.html /usr/share/novnc/setup.html
EXPOSE 8000
CMD ["python", "run.py"]
