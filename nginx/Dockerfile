FROM nginx:1.25-alpine

# Copy frontend dist files into nginx
COPY --from=purplex-web /app/purplex/client/dist /usr/share/nginx/html

# Copy nginx configs
COPY nginx.conf /etc/nginx/nginx.conf
COPY sites-available /etc/nginx/sites-available

EXPOSE 80 443
