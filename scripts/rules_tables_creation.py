import re

import pandas as pd
from google.cloud import bigquery

# --- CONFIGURATION ---
PROJECT_ID = "your-project-id"  # TODO: Replace with your Project ID
DATASET_ID = "your_dataset_id"  # TODO: Replace with your Dataset ID

# File Names (Update these if your local filenames differ)
FILE_NC_RULES = "Copy of Inspection_Following_NC v1.9.xlsx - Feuil.csv"
FILE_AQL_GEN = "Copy of AQL Général - AQL Général.csv"
FILE_AQL_SPEC = "Copy of AQL Spécial - AQL Spécial.csv"

# --- HELPER FUNCTIONS ---


def parse_lot_size(val):
    """Parses '2 – 8' or '500,001 et plus' into min/max integers."""
    val = str(val).replace(",", "").strip()

    # Handle 'and up' / 'et plus'
    if "et plus" in val.lower() or "and up" in val.lower() or "+" in val:
        # Extract the first number found
        match = re.search(r"\d+", val)
        if match:
            return int(match.group()), 999999999  # Use a large number for infinity

    # Handle ranges '2 – 8' (normalize dash)
    val = val.replace("–", "-").replace("—", "-")  # handle different dash types
    if "-" in val:
        parts = val.split("-")
        try:
            return int(parts[0].strip()), int(parts[1].strip())
        except ValueError:
            pass  # Fallback to 0,0 if parsing fails

    return 0, 0


def parse_ac_re(val):
    """Parses 'Ac=0/Re=1' to return the Accept number (0)."""
    if pd.isna(val) or str(val).strip() == "":
        return None

    # Look for 'Ac=X'
    match = re.search(r"Ac=(\d+)", str(val))
    if match:
        return int(match.group(1))
    return None


def process_aql_table(filepath, is_special=False):
    """Reads and transforms an AQL CSV file."""
    # Read CSV (handling Latin1 or UTF-8 depending on file)
    try:
        df = pd.read_csv(filepath)
    except UnicodeDecodeError:
        df = pd.read_csv(filepath, encoding="latin1")

    new_rows = []

    for _, row in df.iterrows():
        # 1. Parse Lot Size
        l_min, l_max = parse_lot_size(row["Taille du Lot"])

        # 2. Parse Limits
        crit = parse_ac_re(row.get("Critical (AQL 0)"))
        maj15 = parse_ac_re(row.get("Major (AQL 1.5)"))
        maj25 = parse_ac_re(row.get("Major (AQL 2.5)"))
        min4 = parse_ac_re(row.get("Minor (AQL 4.0)"))

        common_data = {
            "taille_lot_min": l_min,
            "taille_lot_max": l_max,
            "lettre": row["Lettre"],
            "taille_echantillon": row["Échantillon à prélever"],
            "critique_0_max": crit,
            "majeur_1_5_max": maj15,
            "majeur_2_5_max": maj25,
            "mineur_4_max": min4,
        }

        # 3. Handle Levels (Denormalization)
        raw_level = str(row["Level"])
        levels = []

        if is_special and "-" in raw_level:
            # Logic for "S1-S4" -> ["S1", "S2", "S3", "S4"]
            prefix_match = re.match(r"([A-Za-z]+)", raw_level)
            prefix = prefix_match.group(1) if prefix_match else ""
            nums = re.findall(r"\d+", raw_level)

            if len(nums) == 2:
                start, end = int(nums[0]), int(nums[1])
                for i in range(start, end + 1):
                    levels.append(f"{prefix}{i}")
            else:
                levels.append(raw_level)  # Fallback
        else:
            levels.append(raw_level)

        # Create a row for each level
        for lvl in levels:
            r = common_data.copy()
            r["niveau"] = lvl
            new_rows.append(r)

    return pd.DataFrame(new_rows)


# --- MAIN EXECUTION ---


def main():
    client = bigquery.Client(project=PROJECT_ID)

    # 1. Process NC Rules
    print("Processing NC Rules...")
    try:
        df_nc = pd.read_csv(FILE_NC_RULES)
    except UnicodeDecodeError:
        df_nc = pd.read_csv(FILE_NC_RULES, encoding="latin1")

    # Rename columns to target schema
    df_nc = df_nc.rename(
        columns={
            "Family of non compliance": "famille_non_conformite",
            "Product category": "categorie_produit",
            "cause of non-compliance": "cause_non_conformite",
            "Labaroatory validation": "decision_laboratoire",  # Note: Matches typo in source if present
            "Siplec Decision": "decision_siplec",
            "Comments": "commentaires",
        }
    )

    # Select only required columns
    df_nc = df_nc[
        [
            "famille_non_conformite",
            "categorie_produit",
            "cause_non_conformite",
            "decision_laboratoire",
            "decision_siplec",
            "commentaires",
        ]
    ]

    # 2. Process AQL Tables
    print("Processing AQL General...")
    df_aql_gen = process_aql_table(FILE_AQL_GEN, is_special=False)

    print("Processing AQL Special...")
    df_aql_spec = process_aql_table(FILE_AQL_SPEC, is_special=True)

    # 3. Define Schemas
    schema_nc = [
        bigquery.SchemaField("famille_non_conformite", "STRING"),
        bigquery.SchemaField("categorie_produit", "STRING"),
        bigquery.SchemaField("cause_non_conformite", "STRING"),
        bigquery.SchemaField("decision_laboratoire", "STRING"),
        bigquery.SchemaField("decision_siplec", "STRING"),
        bigquery.SchemaField("commentaires", "STRING"),
    ]

    schema_aql = [
        bigquery.SchemaField("taille_lot_min", "INTEGER"),
        bigquery.SchemaField("taille_lot_max", "INTEGER"),
        bigquery.SchemaField("niveau", "STRING"),
        bigquery.SchemaField("lettre", "STRING"),
        bigquery.SchemaField("taille_echantillon", "INTEGER"),
        bigquery.SchemaField("critique_0_max", "INTEGER"),
        bigquery.SchemaField("majeur_1_5_max", "INTEGER"),
        bigquery.SchemaField("majeur_2_5_max", "INTEGER"),
        bigquery.SchemaField("mineur_4_max", "INTEGER"),
    ]

    # 4. Upload to BigQuery
    job_config_nc = bigquery.LoadJobConfig(
        schema=schema_nc, write_disposition="WRITE_TRUNCATE"
    )
    job_config_aql = bigquery.LoadJobConfig(
        schema=schema_aql, write_disposition="WRITE_TRUNCATE"
    )

    print(f"Uploading table: {DATASET_ID}.inspection_nc_rules")
    client.load_table_from_dataframe(
        df_nc, f"{DATASET_ID}.inspection_nc_rules", job_config=job_config_nc
    ).result()

    print(f"Uploading table: {DATASET_ID}.aql_general")
    client.load_table_from_dataframe(
        df_aql_gen, f"{DATASET_ID}.aql_general", job_config=job_config_aql
    ).result()

    print(f"Uploading table: {DATASET_ID}.aql_special")
    client.load_table_from_dataframe(
        df_aql_spec, f"{DATASET_ID}.aql_special", job_config=job_config_aql
    ).result()

    print("Success! All tables created and populated.")


if __name__ == "__main__":
    main()
