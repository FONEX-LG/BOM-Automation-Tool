# BOM Automation Tool

## Overview
This tool automates the purchasing process for electronic components. It takes a BOM (Excel/CSV), checks real-time stock and pricing via the **Mouser API**, optimizes quantities for price breaks/MOQs, and exports a formatted Purchase Order (PO) for Oracle.

## Setup

1.  **Install Requirements**
    Run this command to install all necessary libraries:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Configure API Key**
    * Locate `config_example.py` in the source folder.
    * Rename it to `config.py`.
    * Open it and paste your Mouser API key:
        ```python
        MOUSER_API_KEY = "YOUR_KEY_HERE"
        ```

3.  **Template File**
    * Ensure `template_digikey_mouser_orderer.xlsx` is in the main project folder.

## Usage

1.  **Run the App**
    ```bash
    python src/bom_po_tool/ui_preview.py
    ```

2.  **Workflow**
    * **Browse:** Load your BOM file.
    * **Check Stock:** Fetches live data and optimizes quantities.
    * **Export PO:** Generates the Excel file for purchasing.

## Features
* **Auto-Stock Check:** Live inventory from Mouser.
* **Smart Quantity:** Auto-adjusts for Minimum Order Quantities (MOQ) and Pack Sizes.
* **Oracle Export:** Maps data to the required company Excel template.
