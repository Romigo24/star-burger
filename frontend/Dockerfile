FROM node:17.6.0
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm install
COPY . .
RUN npm run build
CMD npx serve -s bundles -p 3000
