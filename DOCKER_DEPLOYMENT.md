# Docker Deployment Guide

This guide explains how to deploy the RAG Study Chat API using Docker and Docker Compose.

## 🐳 Docker Architecture

### Services Overview
- **External Neon PostgreSQL**: Cloud-hosted PostgreSQL database with pgvector extension
- **redis**: Redis for caching (optional but recommended)
- **api**: RAG Study Chat API application
- **nginx**: Reverse proxy with rate limiting and SSL termination

### Network Architecture
```
Internet → Nginx (Port 80/443) → API (Port 8000) → Neon PostgreSQL (Cloud)
                                                  → Redis (Port 6379)
```

## 🚀 Quick Start

### Prerequisites
- Docker 20.10+
- Docker Compose 2.0+
- At least 2GB RAM available
- 5GB disk space

### 1. Clone and Configure
```bash
git clone <repository>
cd rag_study_chat

# Copy environment template
cp .env.example .env

# Edit .env with your API keys
nano .env
```

### 2. Deploy Production
```bash
# Make deploy script executable
chmod +x deploy.sh

# Deploy production environment
./deploy.sh prod
```

### 3. Verify Deployment
```bash
# Check service status
./deploy.sh status

# Test API
curl http://localhost:8000/health

# View logs
./deploy.sh logs api
```

## 🛠️ Deployment Commands

### Production Deployment
```bash
./deploy.sh prod           # Deploy production environment
./deploy.sh production     # Same as above
```

### Development Deployment
```bash
./deploy.sh dev            # Deploy with hot reload
./deploy.sh development    # Same as above
```

### Management Commands
```bash
./deploy.sh stop           # Stop all services
./deploy.sh restart        # Restart all services
./deploy.sh status         # Show service status
./deploy.sh logs [service] # Show logs
./deploy.sh test           # Run tests
./deploy.sh cleanup        # Remove everything
```

## 📁 File Structure

```
rag_study_chat/
├── Dockerfile              # Production container
├── Dockerfile.dev          # Development container
├── docker-compose.yml      # Production services
├── docker-compose.dev.yml  # Development overrides
├── nginx.conf              # Nginx configuration
├── init-db.sql            # Database initialization
├── deploy.sh              # Deployment script
├── .dockerignore          # Docker ignore rules
└── .env                   # Environment variables
```

## 🔧 Configuration

### Environment Variables (.env)
```bash
# Database - External Neon PostgreSQL
DATABASE_URL=postgresql://neondb_owner:vCFIsy2nER8c@ep-wandering-feather-a4mv42v8.us-east-1.aws.neon.tech/neondb?sslmode=require

# AWS S3
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_BUCKET_NAME=your_bucket
AWS_REGION=us-east-1

# API Keys
OPENAI_API_KEY=your_openai_key
LLAMA_CLOUD_API_KEY=your_llama_key
LLAMA_PROJECT_ID=your_project_id

# Optional
REDIS_URL=redis://redis:6379/0
LOG_LEVEL=INFO
```

### Docker Compose Services

#### API Application
```yaml
api:
  build: .
  environment:
    # Using external Neon PostgreSQL database
    DATABASE_URL: ${DATABASE_URL}
    OPENAI_API_KEY: ${OPENAI_API_KEY}
    # ... other environment variables
  ports:
    - "8000:8000"
  depends_on:
    redis:
      condition: service_healthy
```

#### Redis Cache
```yaml
redis:
  image: redis:7-alpine
  ports:
    - "6379:6379"
  volumes:
    - redis_data:/data
  healthcheck:
    test: ["CMD", "redis-cli", "ping"]
```

## 🌐 Production Deployment

### With Nginx Proxy
```bash
# Deploy with Nginx
./deploy.sh prod

# Access via:
# - Direct API: http://localhost:8000
# - Via Nginx: http://localhost:80
```

### SSL/HTTPS Setup
1. Obtain SSL certificates
2. Place certificates in `./ssl/` directory
3. Uncomment HTTPS server block in `nginx.conf`
4. Update domain name in configuration

### Environment-Specific Configs

#### Production
- Uses optimized Docker image
- Includes Nginx reverse proxy
- Has health checks and restart policies
- Uses persistent volumes

#### Development
- Includes hot reload
- Mounts source code as volume
- Exposes additional ports
- Includes development tools

## 📊 Monitoring and Logs

### View Service Status
```bash
./deploy.sh status
```

### View Logs
```bash
# All services
./deploy.sh logs

# Specific service
./deploy.sh logs api
./deploy.sh logs postgres
./deploy.sh logs nginx

# Follow logs in real-time
docker-compose logs -f api
```

### Health Checks
```bash
# API health
curl http://localhost:8000/health

# Database health
docker-compose exec postgres pg_isready -U raguser

# Redis health
docker-compose exec redis redis-cli ping
```

## 🔒 Security Considerations

### Production Security
1. **Change default passwords** in docker-compose.yml
2. **Use environment variables** for sensitive data
3. **Enable SSL/HTTPS** in production
4. **Configure firewall** to restrict access
5. **Regular security updates** for base images

### Network Security
- Services communicate via internal Docker network
- Only necessary ports are exposed
- Nginx provides rate limiting
- Security headers are configured

### Data Security
- Database data is persisted in Docker volumes
- Sensitive environment variables are not logged
- API keys are passed via environment variables

## 🚨 Troubleshooting

### Common Issues

#### Services Won't Start
```bash
# Check logs
./deploy.sh logs

# Check Docker daemon
sudo systemctl status docker

# Check disk space
df -h
```

#### Database Connection Issues
```bash
# Check PostgreSQL logs
./deploy.sh logs postgres

# Test database connection
docker-compose exec postgres psql -U raguser -d ragchat -c "SELECT 1;"

# Check pgvector extension
docker-compose exec postgres psql -U raguser -d ragchat -c "SELECT * FROM pg_extension WHERE extname='vector';"
```

#### API Not Responding
```bash
# Check API logs
./deploy.sh logs api

# Check API health
curl -v http://localhost:8000/health

# Check environment variables
docker-compose exec api env | grep -E "(OPENAI|DATABASE)"
```

#### Out of Memory
```bash
# Check memory usage
docker stats

# Increase Docker memory limit
# (Docker Desktop: Settings → Resources → Memory)
```

### Performance Tuning

#### Database Optimization
```sql
-- Connect to database
docker-compose exec postgres psql -U raguser -d ragchat

-- Check database size
SELECT pg_size_pretty(pg_database_size('ragchat'));

-- Optimize queries
ANALYZE;
VACUUM;
```

#### API Optimization
- Adjust worker processes in uvicorn
- Configure connection pooling
- Enable Redis caching
- Monitor memory usage

## 📈 Scaling

### Horizontal Scaling
```yaml
# Scale API instances
api:
  deploy:
    replicas: 3
  
# Load balancer configuration
nginx:
  # Configure upstream with multiple backends
```

### Vertical Scaling
```yaml
# Increase resource limits
api:
  deploy:
    resources:
      limits:
        memory: 2G
        cpus: '1.0'
```

## 🔄 Updates and Maintenance

### Update Application
```bash
# Pull latest code
git pull

# Rebuild and restart
./deploy.sh restart
```

### Database Backup
```bash
# Create backup
docker-compose exec postgres pg_dump -U raguser ragchat > backup.sql

# Restore backup
docker-compose exec -T postgres psql -U raguser ragchat < backup.sql
```

### Clean Up
```bash
# Remove unused containers and images
docker system prune

# Complete cleanup (WARNING: removes all data)
./deploy.sh cleanup
```

## 📞 Support

### Getting Help
1. Check logs: `./deploy.sh logs`
2. Verify configuration: `./deploy.sh status`
3. Test connectivity: `curl http://localhost:8000/health`
4. Review this documentation
5. Check Docker and system resources

### Useful Commands
```bash
# Enter container shell
docker-compose exec api bash
docker-compose exec postgres psql -U raguser ragchat

# Copy files from container
docker cp rag_api:/app/logs ./logs

# View container resource usage
docker stats
```