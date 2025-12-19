#!/bin/bash
# Rollback script for Phase 7
# Usage: ./scripts/rollback.sh <previous-version> <environment>

set -e

PREVIOUS_VERSION=${1}
ENVIRONMENT=${2:-prod}

if [ -z "$PREVIOUS_VERSION" ]; then
  echo "Error: Previous version required"
  echo "Usage: ./scripts/rollback.sh <previous-version> [environment]"
  exit 1
fi

echo "Rolling back to version $PREVIOUS_VERSION in $ENVIRONMENT environment"

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
export APP_VERSION=$PREVIOUS_VERSION
export BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
export GIT_SHA="rollback-$PREVIOUS_VERSION"
export APP_ENV

# Pull previous version image
echo "Pulling previous version: phase7-flask:$PREVIOUS_VERSION"
docker pull phase7-flask:$PREVIOUS_VERSION || {
  echo "Error: Could not pull image phase7-flask:$PREVIOUS_VERSION"
  echo "Make sure the image exists in registry"
  exit 1
}

# Update docker-compose to use previous version
echo "Rolling back..."
docker-compose up -d

# Wait for healthcheck
echo "Waiting for healthcheck..."
sleep 10

# Check health
HEALTH=$(docker inspect --format='{{.State.Health.Status}}' phase7-web 2>/dev/null || echo "none")
if [ "$HEALTH" = "healthy" ]; then
  echo "Rollback successful! Container is healthy."
else
  echo "Warning: Container health status: $HEALTH"
fi

# Show version
echo "Rolled back to version:"
curl -s http://localhost:8085/version | jq .

echo "Rollback complete!"

