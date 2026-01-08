#!/bin/bash
set -e

# Create databases for youtube-v2 and twitter-apify services
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE mcp_youtube;
    CREATE DATABASE mcp_twitter_apify;
EOSQL

echo "Databases mcp_youtube and mcp_twitter_apify created successfully"

