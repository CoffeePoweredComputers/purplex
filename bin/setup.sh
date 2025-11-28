#!/bin/bash
# =====================================================================================
# PURPLEX INITIAL SETUP SCRIPT
# =====================================================================================
# Sets up a fresh development environment
# =====================================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}           Purplex Development Setup                    ${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"

# Check prerequisites
echo -e "\n${YELLOW}Checking prerequisites...${NC}"

check_command() {
    if command -v $1 &> /dev/null; then
        echo -e "${GREEN}✓ $1 is installed${NC}"
        return 0
    else
        echo -e "${RED}✗ $1 is not installed${NC}"
        return 1
    fi
}

MISSING_DEPS=false
check_command python3 || MISSING_DEPS=true
check_command pip || MISSING_DEPS=true
check_command node || MISSING_DEPS=true
check_command yarn || npm install -g yarn
check_command docker || MISSING_DEPS=true
check_command docker-compose || MISSING_DEPS=true
check_command psql || echo -e "${YELLOW}  PostgreSQL client optional${NC}"

if [ "$MISSING_DEPS" = true ]; then
    echo -e "\n${RED}Please install missing dependencies and run again${NC}"
    exit 1
fi

# Step 1: Create virtual environment
echo -e "\n${YELLOW}Step 1: Creating Python virtual environment...${NC}"
if [ ! -d "env" ]; then
    python3 -m venv env
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "${GREEN}✓ Virtual environment already exists${NC}"
fi

# Activate virtual environment
source env/bin/activate

# Step 2: Install Python dependencies
echo -e "\n${YELLOW}Step 2: Installing Python dependencies...${NC}"
pip install --upgrade pip
pip install -r requirements/development.txt
echo -e "${GREEN}✓ Python dependencies installed${NC}"

# Step 3: Set up environment file
echo -e "\n${YELLOW}Step 3: Setting up environment configuration...${NC}"
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo -e "${YELLOW}Please edit .env and add your OPENAI_API_KEY${NC}"
    echo -e "${GREEN}✓ Environment file created${NC}"
else
    echo -e "${GREEN}✓ Environment file already exists${NC}"
fi

# Step 4: Install frontend dependencies
echo -e "\n${YELLOW}Step 4: Installing frontend dependencies...${NC}"
cd purplex/client
yarn install
cd ../..
echo -e "${GREEN}✓ Frontend dependencies installed${NC}"

# Step 5: Start Docker services
echo -e "\n${YELLOW}Step 5: Starting Docker services...${NC}"
docker-compose -f config/docker/development.yml up -d postgres redis
sleep 5
echo -e "${GREEN}✓ Docker services started${NC}"

# Step 6: Run database migrations
echo -e "\n${YELLOW}Step 6: Setting up database...${NC}"
python manage.py migrate
echo -e "${GREEN}✓ Database migrations completed${NC}"

# Step 7: Create superuser
echo -e "\n${YELLOW}Step 7: Creating superuser account...${NC}"
echo -e "${YELLOW}Enter details for Django admin account:${NC}"
python manage.py createsuperuser

# Step 8: Load sample data
echo -e "\n${YELLOW}Step 8: Loading sample data...${NC}"
python manage.py populate_comprehensive
echo -e "${GREEN}✓ Sample data loaded${NC}"

# Step 9: Run tests
echo -e "\n${YELLOW}Step 9: Running test suite...${NC}"
pytest -q -m "not slow"
echo -e "${GREEN}✓ Tests passed${NC}"

# Setup complete
echo -e "\n${GREEN}════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}         Setup completed successfully! 🎉              ${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"

echo -e "\n${BLUE}Next steps:${NC}"
echo -e "1. Edit ${YELLOW}.env${NC} and add your OPENAI_API_KEY"
echo -e "2. Start the development server: ${YELLOW}./start.sh${NC}"
echo -e "3. Access the application:"
echo -e "   • Frontend: ${BLUE}http://localhost:5173${NC}"
echo -e "   • Django Admin: ${BLUE}http://localhost:8000/admin${NC}"
echo -e "   • API: ${BLUE}http://localhost:8000/api${NC}"
echo -e "\n${GREEN}Happy coding! 🚀${NC}"