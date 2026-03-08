FROM node:20-alpine
WORKDIR /app
RUN echo '<!DOCTYPE html><html><head><title>AutoQuery</title></head><body><h1>AutoQuery</h1><p>Frontend coming soon.</p></body></html>' > index.html
EXPOSE 3000
CMD ["npx", "--yes", "serve", "-s", ".", "-l", "3000"]
