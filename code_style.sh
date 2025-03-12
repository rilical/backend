#!/bin/bash

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Define target directories
TARGETS="apps remit_scout quotes"

# Function to run a command and report its status
run_command() {
    local cmd="$1"
    local name="$2"
    
    echo -e "\n${YELLOW}Running ${name}...${NC}"
    eval "$cmd"
    local status=$?
    
    if [ $status -eq 0 ]; then
        echo -e "${GREEN}${name} completed successfully.${NC}"
    else
        echo -e "${RED}${name} encountered issues (exit code: $status).${NC}"
    fi
    
    return $status
}

echo -e "${YELLOW}Running code style tools on: ${TARGETS}${NC}"

# Run Black formatter
run_command "black $TARGETS" "Black formatter"

# Run isort
run_command "isort $TARGETS" "isort"

# Run flake8
run_command "flake8 $TARGETS" "flake8"

# Run mypy
echo -e "\n${YELLOW}Running mypy...${NC}"
mypy $TARGETS --ignore-missing-imports
if [ $? -eq 0 ]; then
    echo -e "${GREEN}mypy check completed successfully.${NC}"
else
    echo -e "${RED}mypy found issues. See above for details.${NC}"
fi

# Option to run pre-commit on all files
echo -e "\n${YELLOW}Would you like to run pre-commit on all files? (y/n)${NC}"
read -r response
if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    echo -e "\n${YELLOW}Running pre-commit on all files...${NC}"
    pre-commit run --all-files
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}pre-commit completed successfully.${NC}"
    else
        echo -e "${RED}pre-commit found issues. See above for details.${NC}"
    fi
fi

echo -e "\n${YELLOW}Code style checks completed.${NC}"
echo -e "${YELLOW}Remember: pre-commit hooks will run automatically on each commit.${NC}"
echo -e "${YELLOW}To run pre-commit manually on all files:${NC}"
echo -e "pre-commit run --all-files" 