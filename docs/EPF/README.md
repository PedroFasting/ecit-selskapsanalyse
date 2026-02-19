# Emergent Product Framework (EPF) - Instance Data

This directory contains the **instance-specific EPF data** for ecit-selskapsanalyse.

## Structure

```
docs/EPF/
├── _instances/ecit-selskapsanalyse/   # All EPF artifacts for this product
├── AGENTS.md        # AI agent instructions
└── README.md        # This file
```

## Working with EPF

All EPF operations are performed via **epf-cli**:

```bash
# Health check
epf-cli health

# Validate a file
epf-cli validate docs/EPF/_instances/ecit-selskapsanalyse/READY/00_north_star.yaml

# List schemas
epf-cli schemas list
```
