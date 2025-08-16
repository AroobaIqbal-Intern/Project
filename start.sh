#!/bin/bash

# Academic Reference Graph Startup Script

echo "🚀 Starting Academic Reference Graph..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install/upgrade dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found. Please copy env.example to .env and configure it."
    echo "   cp env.example .env"
    echo "   Then edit .env with your OpenAI API key and other settings."
    exit 1
fi

# Check if Redis is running
echo "🔍 Checking Redis connection..."
if ! redis-cli ping > /dev/null 2>&1; then
    echo "⚠️  Redis is not running. Please start Redis first:"
    echo "   macOS: brew services start redis"
    echo "   Ubuntu: sudo systemctl start redis"
    echo "   Windows: Start Redis service"
    exit 1
fi

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p media papers
mkdir -p logs
mkdir -p chroma_db

# Run database migrations
echo "🗄️  Running database migrations..."
python manage.py makemigrations
python manage.py migrate

# Create superuser if none exists
echo "👤 Checking for superuser..."
python manage.py shell -c "
from django.contrib.auth.models import User
if not User.objects.filter(is_superuser=True).exists():
    print('No superuser found. Please create one manually:')
    print('python manage.py createsuperuser')
"

# Collect static files
echo "📦 Collecting static files..."
python manage.py collectstatic --noinput

echo ""
echo "✅ Setup complete! Starting services..."
echo ""

# Function to cleanup background processes
cleanup() {
    echo ""
    echo "🛑 Shutting down services..."
    kill $DJANGO_PID $CELERY_PID $CELERY_BEAT_PID 2>/dev/null
    exit 0
}

# Set trap for cleanup
trap cleanup SIGINT SIGTERM

# Start Django server
echo "🌐 Starting Django server..."
python manage.py runserver &
DJANGO_PID=$!

# Wait a moment for Django to start
sleep 3

# Start Celery worker
echo "🔧 Starting Celery worker..."
celery -A reference_graph worker --loglevel=info &
CELERY_PID=$!

# Start Celery beat (optional)
echo "⏰ Starting Celery beat..."
celery -A reference_graph beat --loglevel=info &
CELERY_BEAT_PID=$!

echo ""
echo "🎉 All services are running!"
echo ""
echo "📱 Django server: http://localhost:8000"
echo "🔧 Admin interface: http://localhost:8000/admin"
echo "📊 API endpoints: http://localhost:8000/api/"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Wait for all background processes
wait
