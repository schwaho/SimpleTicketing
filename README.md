# SimpleTicketing

<p>
  <img src="SimpleTicketing_Logo.svg" width="180" alt="SimpleTicketing Logo">
</p>

SimpleTicketing is a lightweight digital ticketing system for non-profit organizations.

## Status

Early development stage.
The software is experimental; interfaces and behavior may change at any time.
Not recommended for production use.

## Motivation

Non-profit organizations often face a choice between complex open-source solutions
and commercial providers with recurring costs when digitizing events.

SimpleTicketing takes a deliberately minimal approach.
Its goal is to provide a low-barrier entry into digital ticket management without financial risk
and without high technical requirements.

## Requirements

- Python >= 3.9
- pip

## Installation

SimpleTicketing can be installed either from a prebuilt source distribution (sdist)
(recommended) or directly from the repository using an editable install.
Using a virtual Python environment (`venv`) is recommended.

### Install from sdist archive (recommended)

#### 1. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

#### 2. Install the sdist archive

```bash
pip install simpleticketing-<version>.tar.gz
```

### Install from repository (alternative)

#### 1. Clone the repository

```bash
git clone git@github.com:schwaho/SimpleTicketing.git
cd SimpleTicketing
```

#### 2. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

#### 3. Install in editable mode

```bash
pip install -e .
```

#### 4. Install development tools (optional)

```bash
pip install .[dev,utils]
```

## Usage

### Command Line Interface (CLI)

#### sdist installation

After sdist installation, the `simpleticketing` command is available.

Initialize a new instance:
```bash
simpleticketing init
```

Delete ticket data:
```bash
simpleticketing clean
```

Reset the entire instance:
```bash
simpleticketing reset
```

#### Alternative (editable installation)

When working directly from the repository, the CLI can be executed via the module:

Initialize a new instance:
```bash
python -m simple_ticketing.cli init
```

Delete ticket data:
```bash
python -m simple_ticketing.cli clean
```

Reset the entire instance:
```bash
python -m simple_ticketing.cli reset
```

### Application Mode (Web API & Frontend)

To start the web application (Flask API and frontend), run:

```bash
python -m simple_ticketing
```

> Note:
> The instance must be initialized once using the CLI before starting the application.

Open your browser and navigate to https://127.0.0.1:5000 to open the SimpleTicketing dashboard.
Alternatively, the API endpoints are available at https://127.0.0.1:5000/api.

## License

MIT (see LICENSE.txt)

This project includes third-party components licensed under
the Apache License 2.0 and the SIL Open Font License 1.1.
See 3RD_PARTY_LICENSES.txt for details.
