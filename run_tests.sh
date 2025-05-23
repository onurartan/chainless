#!/bin/bash

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color
BOLD='\033[1m'

divider() {
  echo -e "${BOLD}--------------------------------------------------${NC}"
}

header() {
  echo -e "\n${BOLD}🔹 $1${NC}"
  divider
}

run_examples() {
  header "Running Examples (examples/*.py)"
  for file in examples/*.py; do
    echo -e "▶️ Running: ${file}"
    uv run  "$file"
    status=$?
    if [ $status -ne 0 ]; then
      echo -e "${RED}❌ Failed: $file${NC}"
      exit 1
    else
      echo -e "${GREEN}✅ Passed: $file${NC}\n"
    fi
  done
}

run_tests() {
  header "Running Tests (pytest)"
  uv run pytest --color=yes
  status=$?
  if [ $status -ne 0 ]; then
    echo -e "${RED}❌ Tests failed.${NC}"
    exit 1
  else
    echo -e "${GREEN}✅ All tests passed.${NC}"
  fi
}

main() {
  echo -e "${BOLD}🚀 Starting Full Run with uv...${NC}"
  divider
#   run_examples 
  run_tests
  divider
  echo -e "${GREEN}🏁 All steps completed successfully.${NC}"
}

main
