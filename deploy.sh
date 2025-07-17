#!/bin/bash

# RAG Study Chat API Deployment Script
# This script helps deploy the application using Docker Compose

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    if ! command_exists docker; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! command_exists docker-compose; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    print_success "Prerequisites check passed"
}

# Check environment file
check_env_file() {
    print_status "Checking environment configuration..."
    
    if [ ! -f .env ]; then
        print_warning ".env file not found"
        if [ -f .env.example ]; then
            print_status "Copying .env.example to .env"
            cp .env.example .env
            print_warning "Please edit .env file with your actual API keys before continuing"
            read -p "Press Enter after configuring .env file..."
        else
            print_error ".env.example file not found. Cannot create .env file."
            exit 1
        fi
    fi
    
    # Check for required environment variables
    source .env
    
    required_vars=("OPENAI_API_KEY" "AWS_ACCESS_KEY_ID" "AWS_SECRET_ACCESS_KEY" "LLAMA_CLOUD_API_KEY")
    missing_vars=()
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ] || [[ "${!var}" == "your_"* ]]; then
            missing_vars+=("$var")
        fi
    done
    
    if [ ${#missing_vars[@]} -ne 0 ]; then
        print_error "Missing or unconfigured environment variables:"
        for var in "${missing_vars[@]}"; do
            echo "  - $var"
        done
        print_warning "Please configure these variables in .env file"
        exit 1
    fi
    
    print_success "Environment configuration check passed"
}

# Build and start services
deploy_production() {
    print_status "Deploying production environment..."
    
    # Build images
    print_status "Building Docker images..."
    docker-compose build --no-cache
    
    # Start services
    print_status "Starting services..."
    docker-compose up -d
    
    # Wait for services to be healthy
    print_status "Waiting for services to be ready..."
    sleep 10
    
    # Check service health
    if docker-compose ps | grep -q "Up (healthy)"; then
        print_success "Services are running and healthy"
    else
        print_warning "Some services may not be fully ready yet"
        print_status "Check service status with: docker-compose ps"
    fi
    
    print_success "Production deployment completed"
    print_status "API is available at: http://localhost:8000"
    print_status "With Nginx proxy at: http://localhost:80"
}

# Deploy development environment
deploy_development() {
    print_status "Deploying development environment..."
    
    # Build and start development services
    docker-compose -f docker-compose.yml -f docker-compose.dev.yml build --no-cache
    docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
    
    print_success "Development deployment completed"
    print_status "API is available at: http://localhost:8001"
    print_status "Database is available at: localhost:5433"
}

# Stop services
stop_services() {
    print_status "Stopping services..."
    docker-compose down
    print_success "Services stopped"
}

# Clean up (remove containers, volumes, images)
cleanup() {
    print_warning "This will remove all containers, volumes, and images related to this project"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_status "Cleaning up..."
        docker-compose down -v --rmi all
        docker system prune -f
        print_success "Cleanup completed"
    else
        print_status "Cleanup cancelled"
    fi
}

# Show logs
show_logs() {
    service=${1:-}
    if [ -n "$service" ]; then
        docker-compose logs -f "$service"
    else
        docker-compose logs -f
    fi
}

# Show service status
show_status() {
    print_status "Service Status:"
    docker-compose ps
    
    print_status "\nService Health:"
    docker-compose exec api curl -s http://localhost:8000/health | python -m json.tool 2>/dev/null || echo "API not responding"
}

# Run tests
run_tests() {
    print_status "Running tests..."
    docker-compose exec api python test_client.py
}

# Show help
show_help() {
    echo "RAG Study Chat API Deployment Script"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  prod, production     Deploy production environment"
    echo "  dev, development     Deploy development environment"
    echo "  stop                 Stop all services"
    echo "  restart              Restart all services"
    echo "  status               Show service status"
    echo "  logs [service]       Show logs (optionally for specific service)"
    echo "  test                 Run tests"
    echo "  cleanup              Remove all containers, volumes, and images"
    echo "  help                 Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 prod              # Deploy production"
    echo "  $0 dev               # Deploy development"
    echo "  $0 logs api          # Show API logs"
    echo "  $0 status            # Show service status"
}

# Main script logic
main() {
    case "${1:-help}" in
        "prod"|"production")
            check_prerequisites
            check_env_file
            deploy_production
            ;;
        "dev"|"development")
            check_prerequisites
            check_env_file
            deploy_development
            ;;
        "stop")
            stop_services
            ;;
        "restart")
            stop_services
            sleep 2
            deploy_production
            ;;
        "status")
            show_status
            ;;
        "logs")
            show_logs "$2"
            ;;
        "test")
            run_tests
            ;;
        "cleanup")
            cleanup
            ;;
        "help"|*)
            show_help
            ;;
    esac
}

# Run main function with all arguments
main "$@"