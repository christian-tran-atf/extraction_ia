# Goals

These scripts are only used for creating mock resources 'manually', because the following processes are not yet existent:
- Cloud Run job that make incremental insertions from the source tables to the control table AND uploads PDF files to the Cloud Storage bucket.
- Secondary pipeline that handles the business rules & AQL

It will be necessary to have a proper and dedicated method to create the GCP resources with IaC.

# Usage

In order to be able to run the program, the GCP resources must already be created.

If they're not yet existent, execute these scripts:
1. `control_table_and_bucket_creation.py`
2. `fri_extraction_prompt_images.py`
3. `rules_tables_creation`

Please note that for each script, you either need to have the required files downloaded on your local storage already OR retrieve the folder ID corresponding to the drive folder containing the files.
1. FRI PDF files (in 'Qualité' Drive -> '03_RESSOURCES_ET_PROCEDURES' -> 'Vérification de Rapports Qualité' -> 'Exemples rapport qualité' -> 'Rapport FRI (inspection)')
2. Images in prompt for FRI (in 'Qualité' Drive -> '01_SUJETS_EN_COURS' -> '04_Contrôle des rapports par IA' -> '01_Cadrage' -> 'POC FRI' -> 'Images utilisées dans le prompt')
3. Inspection rules and AQLs (in 'Qualité' Drive -> '01_SUJETS_EN_COURS' -> '04_Contrôle des rapports par IA' -> '01_Cadrage' -> 'Règles métiers')