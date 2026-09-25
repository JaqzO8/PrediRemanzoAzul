#!/usr/bin/env bash
# ==============================================================================
# Script de aprovisionamiento automatizado para AWS EC2 (Ubuntu 22.04 / 24.04 LTS)
# Proyecto: PrediRemanzoAzul
# ==============================================================================

set -euo pipefail

echo "=========================================================="
echo "🚀 Iniciando aprovisionamiento de EC2 para PrediRemanzoAzul"
echo "=========================================================="

# 1. Actualizar repositorios del sistema
sudo apt-get update -y
sudo apt-get upgrade -y

# 2. Instalar paquetes esenciales
sudo apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    git \
    nginx \
    ufw \
    htop

# 3. Instalar Docker Engine y Docker Compose Plugin
if ! command -v docker &> /dev/null; then
    echo "🐳 Instalando Docker..."
    sudo install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    sudo chmod a+r /etc/apt/keyrings/docker.gpg

    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

    sudo apt-get update -y
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    # Añadir usuario al grupo docker
    sudo usermod -aG docker "$USER"
    echo "Docker instalado correctamente."
fi

# 4. Configurar Firewall (UFW)
echo "🛡️ Configurando UFW Firewall..."
sudo ufw allow 22/tcp comment 'SSH'
sudo ufw allow 80/tcp comment 'HTTP'
sudo ufw allow 443/tcp comment 'HTTPS'
sudo ufw allow 8080/tcp comment 'App directa si aplica'
sudo ufw --force enable

# 5. Directorio del proyecto
APP_DIR="/opt/prediremanzoazul"
if [ ! -d "$APP_DIR" ]; then
    echo "📁 Creando directorio en $APP_DIR..."
    sudo mkdir -p "$APP_DIR"
    sudo chown -R "$USER:$USER" "$APP_DIR"
fi

# 6. Configurar Nginx Reverse Proxy
echo "🌐 Configurando Nginx Reverse Proxy..."
if [ -f "$APP_DIR/deploy/nginx_prediremanzoazul.conf" ]; then
    sudo cp "$APP_DIR/deploy/nginx_prediremanzoazul.conf" /etc/nginx/sites-available/prediremanzoazul.conf
    sudo ln -sf /etc/nginx/sites-available/prediremanzoazul.conf /etc/nginx/sites-enabled/
    sudo rm -f /etc/nginx/sites-enabled/default
    sudo nginx -t && sudo systemctl reload nginx
fi

echo "=========================================================="
echo "✅ Servidor EC2 aprovisionado exitosamente."
echo "Próximo paso: Clona el repositorio en $APP_DIR y ejecuta:"
echo "  docker compose up -d --build"
echo "=========================================================="
