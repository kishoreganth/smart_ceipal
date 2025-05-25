# Smart Ceipal FastAPI Docker Deployment

This guide shows two approaches to deploy the Smart Ceipal FastAPI application with Selenium using Docker on AWS EC2 Ubuntu.

## Prerequisites

1. AWS EC2 Ubuntu instance
2. Docker installed
3. Git (to clone the repository)

## Approach 1: Simple .env File Method (Recommended)

This is the simplest approach where your `.env` file is copied into the Docker container and loaded directly by the Python application.

### 1. Install Docker

```bash
# Update system
sudo apt update

# Install Docker
sudo apt install -y docker.io
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER

# Logout and login again for group changes to take effect
exit
```

### 2. Clone and Setup Project

```bash
# Clone your project
git clone <your-repository-url>
cd <your-project-directory>

# Create .env file with your credentials
nano .env  # Create and edit with your actual credentials
```

### 3. Create .env File

Create a `.env` file in your project root:

```env
# API Configuration
API_KEY=your_secure_api_key_here

# RippleHire Credentials - USA
ripple_username=your_usa_username
ripple_password=your_usa_password

# RippleHire Credentials - India
ripple_username_india=your_india_username
ripple_password_india=your_india_password

# OpenAI API Key
OPENAI_API_KEY=your_openai_api_key

# Ceipal API Configuration
CEIPAL_API_KEY=your_ceipal_api_key
```

### 4. Build and Run with Docker

```bash
# Build the Docker image
docker build -t smart-ceipal .

# Run the container
docker run -d \
  --name smart-ceipal-app \
  -p 8000:8000 \
  --restart unless-stopped \
  -v $(pwd)/resources:/smart_ceipal/resources \
  -v $(pwd)/drivers:/smart_ceipal/drivers \
  smart-ceipal

# Check if it's running
docker ps

# View logs
docker logs -f smart-ceipal-app

# Check health
curl http://localhost:8000/docs
```

### 5. Simple Docker Management Commands

```bash
# Stop the container
docker stop smart-ceipal-app

# Start the container
docker start smart-ceipal-app

# Restart the container
docker restart smart-ceipal-app

# Remove the container
docker rm smart-ceipal-app

# Remove the image
docker rmi smart-ceipal

# Rebuild and run
docker stop smart-ceipal-app
docker rm smart-ceipal-app
docker build -t smart-ceipal .
docker run -d --name smart-ceipal-app -p 8000:8000 --restart unless-stopped -v $(pwd)/resources:/smart_ceipal/resources -v $(pwd)/drivers:/smart_ceipal/drivers smart-ceipal
```

---

## Approach 2: Docker Compose Method

If you prefer using docker-compose for more complex setups:

### 1. Install Docker Compose

```bash
# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.21.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### 2. Use docker-compose.yml

Your existing docker-compose.yml file works with environment variables.

### 3. Docker Compose Commands

```bash
# Build and start
docker-compose up -d --build

# Stop
docker-compose down

# View logs
docker-compose logs -f app
```

---

## Which Approach is Better?

### Simple .env File Method (Recommended for you):
✅ **Pros:**
- Simpler deployment with just `docker build` and `docker run`
- No need for docker-compose.yml
- Direct environment variable loading
- Easier to understand and debug
- Perfect for single-service applications
- Faster startup

❌ **Cons:**
- Less flexible for multi-service setups
- Harder to override environment variables per deployment

### Docker Compose Method:
✅ **Pros:**
- Better for multi-service applications
- Easier environment variable management
- Better for production orchestration
- Health checks and restart policies
- Volume management

❌ **Cons:**
- Additional complexity
- Requires docker-compose installation
- Overkill for single-service apps

## Security Group Configuration

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

## Troubleshooting

### Common Issues

1. **Chrome/ChromeDriver Issues**:
   ```bash
   # Check if Chrome is installed in container
   docker exec smart-ceipal-app google-chrome --version
   
   # Check ChromeDriver
   docker exec smart-ceipal-app /smart_ceipal/drivers/chromedriver --version
   ```

2. **Port Issues**:
   ```bash
   # Check if port is in use
   sudo netstat -tulpn | grep :8000
   ```

3. **Permission Issues**:
   ```bash
   # Fix permissions for resources directory
   sudo chown -R $USER:$USER ./resources
   sudo chown -R $USER:$USER ./drivers
   ```

### Logs

```bash
# Application logs (simple method)
docker logs smart-ceipal-app

# Real-time logs
docker logs -f smart-ceipal-app

# Container status
docker ps
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