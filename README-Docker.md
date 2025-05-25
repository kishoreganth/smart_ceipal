# Smart Ceipal FastAPI Docker Deployment

This guide explains how to deploy the Smart Ceipal FastAPI application with Selenium using Docker on AWS EC2 Ubuntu.

## Prerequisites

1. AWS EC2 Ubuntu instance
2. Docker and Docker Compose installed
3. Git (to clone the repository)

## Quick Setup on AWS EC2

### 1. Install Docker and Docker Compose

```bash
# Update system
sudo apt update

# Install Docker
sudo apt install -y docker.io
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.21.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Logout and login again for group changes to take effect
exit
```

### 2. Clone and Setup Project

```bash
# Clone your project
git clone <your-repository-url>
cd <your-project-directory>

# Create .env file with your credentials
cp .env.example .env
nano .env  # Edit with your actual credentials
```

### 3. Environment Variables

Create a `.env` file with the following variables:

```env
# API Configuration
API_KEY=your_secure_api_key_here

# RippleHire Credentials - USA
RIPPLE_USERNAME_USA=your_usa_username
RIPPLE_PASSWORD_USA=your_usa_password

# RippleHire Credentials - India
RIPPLE_USERNAME_INDIA=your_india_username
RIPPLE_PASSWORD_INDIA=your_india_password

# OpenAI API Key
OPENAI_API_KEY=your_openai_api_key

# Ceipal API Configuration
CEIPAL_API_KEY=your_ceipal_api_key
```

### 4. Build and Run

```bash
# Build and start the application
docker-compose up -d --build

# Check if it's running
docker-compose ps

# View logs
docker-compose logs -f

# Check health
curl http://localhost:8000/docs
```

### 5. Security Group Configuration

Make sure your EC2 instance's security group allows:
- Inbound traffic on port 8000
- Outbound traffic for internet access

## Usage

### API Endpoints

1. **Health Check**: `GET http://your-ec2-ip:8000/docs`
2. **Job Details**: `GET http://your-ec2-ip:8000/job/details?job_id=123&country=USA`

### API Authentication

Include the API key in the request header:
```
X-API-Key: your_secure_api_key_here
```

### Example Request

```bash
curl -X GET "http://your-ec2-ip:8000/job/details?job_id=123&country=USA" \
     -H "X-API-Key: your_secure_api_key_here"
```

## Docker Commands

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Rebuild and restart
docker-compose up -d --build

# View logs
docker-compose logs -f app

# Execute commands in container
docker-compose exec app bash

# Remove everything including volumes
docker-compose down -v
```

## Troubleshooting

### Common Issues

1. **Chrome/ChromeDriver Issues**:
   ```bash
   # Check if Chrome is installed in container
   docker-compose exec app google-chrome --version
   
   # Check ChromeDriver
   docker-compose exec app /smart_ceipal/drivers/chromedriver --version
   ```

2. **Port Issues**:
   ```bash
   # Check if port is in use
   sudo netstat -tulpn | grep :8000
   
   # Change port in docker-compose.yml if needed
   ```

3. **Permission Issues**:
   ```bash
   # Fix permissions for resources directory
   sudo chown -R $USER:$USER ./resources
   sudo chown -R $USER:$USER ./drivers
   ```

### Logs

```bash
# Application logs
docker-compose logs app

# Real-time logs
docker-compose logs -f

# Container status
docker-compose ps
```

## Production Considerations

1. **Reverse Proxy**: Use nginx for SSL termination and load balancing
2. **Monitoring**: Add health checks and monitoring
3. **Backup**: Backup your .env file securely
4. **Updates**: Regularly update dependencies and base images
5. **Scaling**: Consider using Docker Swarm or Kubernetes for scaling

## File Structure

```
smart_ceipal/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── api.py
├── scraper.py
├── ceipal_AI.py
├── .env
├── .gitignore
├── drivers/          # ChromeDriver (auto-created)
└── resources/        # Screenshots and logs (auto-created)
``` 