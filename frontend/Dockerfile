# Stage 1: Build React App
FROM node:18-alpine as build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

# Stage 2: Serve with Nginx
FROM nginx:alpine

# Copy built assets from builder stage
COPY --from=build /app/dist /usr/share/nginx/html/login_app

# Expose port 80
EXPOSE 80

# CMD is technically not needed as nginx:alpine has it, but good for clarity
CMD ["nginx", "-g", "daemon off;"]
