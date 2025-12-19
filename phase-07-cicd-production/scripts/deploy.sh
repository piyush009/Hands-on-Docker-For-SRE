#!/bin/bash
# Deployment script for Phase 7
# Usage: ./scripts/deploy.sh <version> <environment>

set -e

VERSION=${1:-latest}
ENVIRONMENT=${2:-dev}

echo "Deploying version $VERSION to $ENVIRONMENT environment"

# Set environment-specific variables
case $ENVIRONMENT in
  dev)
    APP_ENV=dev
    ;;
  staging)
    APP_ENV=staging
    ;;
  prod)
    APP_ENV=prod
    ;;
  *)
    echo "Unknown environment: $ENVIRONMENT"
    exit 1
    ;;
esac

# Export variables for docker-compose
export APP_VERSION=$VERSION
export BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
export GIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
export APP_ENV

# Pull latest image
echo "Pulling image: phase7-flask:$VERSION"
docker pull phase7-flask:$VERSION || echo "Image not found in registry, will build locally"

# Deploy with docker-compose
echo "Deploying..."
docker-compose up -d

# Wait for healthcheck
echo "Waiting for healthcheck..."
sleep 10

# Check health
HEALTH=$(docker inspect --format='{{.State.Health.Status}}' phase7-web 2>/dev/null || echo "none")
if [ "$HEALTH" = "healthy" ]; then
  echo "Deployment successful! Container is healthy."
else
  echo "Warning: Container health status: $HEALTH"
fi

# Show version
echo "Deployed version:"
curl -s http://localhost:8085/version | jq .

echo "Deployment complete!"

