#!/bin/bash

# Your Railway deployment URL
API_URL="https://trace-production-79d5.up.railway.app"

echo "🚀 Testing Trace API at: $API_URL"
echo "=================================================="

# Test health endpoint
echo ""
echo "1. Testing /health endpoint:"
echo "----------------------------"
curl -X GET "$API_URL/health" -H "Content-Type: application/json" | python -m json.tool

# Test API test endpoint
echo ""
echo ""
echo "2. Testing /api/test endpoint:"
echo "-------------------------------"
curl -X GET "$API_URL/api/test" -H "Content-Type: application/json" | python -m json.tool

# Test auth requirement
echo ""
echo ""
echo "3. Testing /api/summarize (should require auth):"
echo "-------------------------------------------------"
curl -X POST "$API_URL/api/summarize" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "text": "Test content"}' \
  -w "\nHTTP Status: %{http_code}\n"

echo ""
echo "=================================================="
echo "✅ Tests complete!"