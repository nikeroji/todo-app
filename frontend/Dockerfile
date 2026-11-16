FROM alpine:3.23 AS build

WORKDIR /site

COPY index.html app.js ./
COPY static/ ./static/


FROM nginx:stable-alpine

COPY --from=build /site/ /usr/share/nginx/html/

EXPOSE 80