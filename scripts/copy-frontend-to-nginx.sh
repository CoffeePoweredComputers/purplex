#!/bin/bash
# Copy frontend dist files from web container to nginx
# This runs once when nginx starts

echo "Waiting for web container to be ready..."
until docker exec purplex_web_1 test -f /app/purplex/client/dist/index.html 2>/dev/null; do
    sleep 2
done

echo "Copying frontend files to nginx..."
docker cp purplex_web_1:/app/purplex/client/dist/. /tmp/frontend/
docker cp /tmp/frontend/. purplex_nginx_1:/usr/share/nginx/html/
rm -rf /tmp/frontend

echo "Frontend files copied successfully!"
