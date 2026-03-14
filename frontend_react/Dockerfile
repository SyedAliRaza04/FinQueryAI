# Use official Node runtime
FROM node:20-alpine

WORKDIR /app

# Install dependencies
COPY package.json package-lock.json ./
RUN npm install

# Copy source code
COPY . .

# Expose Vite's default port
EXPOSE 5173

# Start Vite dev server exposing all interfaces
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
